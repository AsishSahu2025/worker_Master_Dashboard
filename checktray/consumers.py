
# import json
# import asyncio
# from django.utils import timezone
# from channels.db import database_sync_to_async
# from .models import Image
# from .storage.azure import generate_read_sas
# from channels.generic.websocket import AsyncWebsocketConsumer

# @database_sync_to_async
# def fetch_latest_images():
#     return list(
#         Image.objects
#         .order_by("-created_at")[:4]
#         .values(
#             "device_id",
#             "image_type",
#             "logical_path",
#             "created_at"
#         )
#     )


# class ThermalImageConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.room_group_name = "thermal_images_group"
#         #self.is_connected = True
#         await self.channel_layer.group_add(self.room_group_name, self.channel_name)
#         await self.accept()

#         print("[✓] WebSocket connection established.")

#         await self.send(text_data=json.dumps({
#             "type": "connection_established",
#             "message": "WebSocket connection established"
#         }))

#         self.send_task = asyncio.create_task(self.send_thermal_images_periodically())
#         self.ping_task = asyncio.create_task(self.send_ping_periodically())

#     async def disconnect(self, close_code):
#         #self.is_connected = False
#         try:
#             if hasattr(self, 'send_task') and self.send_task:
#                 self.send_task.cancel()
#                 try:
#                     await self.send_task
#                 except asyncio.CancelledError:
#                     pass

#             if hasattr(self, 'ping_task') and self.ping_task:
#                 self.ping_task.cancel()
#                 try:
#                     await self.ping_task
#                 except asyncio.CancelledError:
#                     pass

#             await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
#             print("[!] WebSocket disconnected.")
#         except Exception as e:
#             print(f"[ERROR] Error during WebSocket disconnection: {e}")
#         finally:
#             await self.close()

#     async def receive(self, text_data):
#         # if not self.is_connected:
#         #     return
#         data = json.loads(text_data)
#         if data.get('type') == 'ping':
#             await self.send(text_data=json.dumps({
#                 'type': 'pong'
#             }))
#             print("[↔] Ping received, Pong sent.")

#     async def send_ping_periodically(self):
#         while True:
#             try:
#                 await self.send(text_data=json.dumps({
#                     'type': 'ping'
#                 }))
#                 await asyncio.sleep(10)
#         # try:
#         #     while self.is_connected:
#         #         await self.safe_send({'type': 'ping'})
#         #         await asyncio.sleep(20)
#             except asyncio.CancelledError:
#                 break
#             except Exception as e:
#                 print(f"[PING ERROR] {e}")
#                 break


#     async def send_thermal_images_periodically(self):
#         try:
#             while True:
#                 await self.send_thermal_images()
#                 await asyncio.sleep(5)
#         except asyncio.CancelledError:
#             print("[INFO] Background image task cancelled due to disconnect.")
#         except Exception as e:
#             print(f"[ERROR] Periodic image sending failed: {e}")
#             await self.send(text_data=json.dumps({
#                 'type': 'error',
#                 'message': 'An error occurred while sending images.'
#             }))

#     async def send_thermal_images(self):
#         start_time = timezone.localtime(timezone.now())
#         print(f"[TIME] Image send cycle started at: {start_time.isoformat()}")

#         try:
#             db_start = timezone.now()

#             records = await fetch_latest_images()

#             db_end = timezone.localtime(timezone.now())
#             print(
#                 f"[TIME] DB fetch completed at: {db_end.isoformat()} | "
#                 f"Took: {(db_end - db_start).total_seconds()}s"
#             )

#             process_start = timezone.now()

#             thermal_data = []
#             colour_data = []

#             for idx, row in enumerate(records, start=1):
#                 print(f"\n[INFO] Processing Record #{idx}")

#                 device_id = row["device_id"]
#                 image_type = row["image_type"]
#                 logical_path = row["logical_path"]
#                 created_at = row["created_at"]

#                 image_url = generate_read_sas(logical_path)

#                 payload = {
#                     "node_id": device_id,
#                     "created_at": created_at.isoformat(),
#                     "image_url": image_url
#                 }

#                 if image_type == "thermal":
#                     thermal_data.append(payload)
#                     print(f"[✓] Thermal image URL prepared for node_id: {device_id}")

#                 elif image_type == "color":
#                     colour_data.append(payload)
#                     print(f"[✓] Colour image URL prepared for node_id: {device_id}")

#             process_end = timezone.localtime(timezone.now())
#             print(
#                 f"[TIME] Image processing completed at: {process_end.isoformat()} | "
#                 f"Took: {(process_end - process_start).total_seconds()}s"
#             )

#             send_start = timezone.localtime(timezone.now())

#             if thermal_data:
#                 await self.send(text_data=json.dumps({
#                     "type": "thermal_images",
#                     "data": thermal_data
#                 }))

#             if colour_data:
#                 await self.send(text_data=json.dumps({
#                     "type": "colour_images",
#                     "data": colour_data
#                 }))

#             print(
#                 f"[✓] Sent {len(thermal_data)} thermal and "
#                 f"{len(colour_data)} colour image URLs to WebSocket"
#             )

#             send_end = timezone.localtime(timezone.now())
#             print(
#                 f"[TIME] WebSocket send completed at: {send_end.isoformat()} | "
#                 f"Took: {(send_end - send_start).total_seconds()}s"
#             )

#             print(
#                 f"[TIME] TOTAL cycle time: "
#                 f"{(send_end - start_time).total_seconds()}s"
#             )

#         except Exception as e:
#             print(f"[CRITICAL] Error sending images: {e}")
#             await self.send(text_data=json.dumps({
#                 "type": "error",
#                 "message": "Failed to fetch images."
#             }))

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