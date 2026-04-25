import json
import asyncio
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from checktray.models import Image
import time
from .storage.azure import generate_read_sas


@database_sync_to_async
def fetch_initial_images(device_id):
    return list(
        Image.objects
        .filter(device_id=device_id)
        .order_by("-created_at")[:4]
        .values(
            "device_id",
            "image_type",
            "logical_path",
            "created_at"
        )
    )


class ThermalImageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get device_id from query params
        query_string = self.scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        self.device_id = params.get("device_id", [None])[0]
        self.last_pong = time.time()

        if not self.device_id:
            await self.close(code=4002)
            return

        # Accept connection
        await self.accept()
        print(f"[✓] WS connected | device={self.device_id}")

        # Send initial images
        await self.send_initial_images()

        # Join device group
        self.group_name = f"device_{self.device_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Keepalive ping
        self.ping_task = asyncio.create_task(self.send_ping())

        await self.send(json.dumps({
            "type": "connection_established",
            # "message": "Subscribed to live updates"
        }))

    async def disconnect(self, close_code):
        print(f"[!] WS disconnected | device={getattr(self, 'device_id', None)}")

        if hasattr(self, "ping_task"):
            self.ping_task.cancel()

        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)

            if data.get("type") == "pong":
                self.last_pong = time.time()
                print('pong received')
                # await self.send(json.dumps({"type": "pong"}))

        except Exception as e:
            print(f"[RECEIVE ERROR] {e}")

    async def send_ping(self):
        try:
            while True:
                if time.time() - self.last_pong > 15:
                    print("No pong received. Closing connection.")
                    await self.close()
                    break
                print('ping sent')
                await self.send(json.dumps({"type": "ping"}))
                await asyncio.sleep(15)
        except asyncio.CancelledError:
            pass

    async def send_initial_images(self):
        records = await fetch_initial_images(self.device_id)
        print('intital image captured')

        thermal, colour = [], []

        for row in records:
            payload = {
                "node_id": row["device_id"],
                "created_at": row["created_at"].isoformat(),
                "image_url": generate_read_sas(row["logical_path"]),
            }

            if row["image_type"] == "thermal":
                thermal.append(payload)
            elif row["image_type"] == "color":
                colour.append(payload)

        if thermal:
            await self.send(json.dumps({
                "type": "thermal_images",
                "data": thermal
            }))

        if colour:
            await self.send(json.dumps({
                "type": "colour_images",
                "data": colour
            }))

    async def new_image(self, event):
        data = event["data"]

        await self.send(json.dumps({
            "type": "new_image",
            "data": {
                "node_id": data["node_id"],
                "image_type": data["image_type"],
                "image_url": generate_read_sas(data["logical_path"]),
                "created_at": data["created_at"]
            }
        }))