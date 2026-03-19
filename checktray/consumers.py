
import json
import asyncio
from django.utils import timezone
from channels.db import database_sync_to_async
from .models import Image
from .storage.azure import generate_read_sas
from channels.generic.websocket import AsyncWebsocketConsumer

@database_sync_to_async
def fetch_latest_images():
    return list(
        Image.objects
        .order_by("-created_at")[:20]
        .values(
            "device_id",
            "image_type",
            "logical_path",
            "created_at"
        )
    )


class ThermalImageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = "thermal_images_group"
        #self.is_connected = True
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        print("[✓] WebSocket connection established.")

        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "message": "WebSocket connection established"
        }))

        self.send_task = asyncio.create_task(self.send_thermal_images_periodically())
        self.ping_task = asyncio.create_task(self.send_ping_periodically())

    async def disconnect(self, close_code):
        #self.is_connected = False
        try:
            if hasattr(self, 'send_task') and self.send_task:
                self.send_task.cancel()
                try:
                    await self.send_task
                except asyncio.CancelledError:
                    pass

            if hasattr(self, 'ping_task') and self.ping_task:
                self.ping_task.cancel()
                try:
                    await self.ping_task
                except asyncio.CancelledError:
                    pass

            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            print("[!] WebSocket disconnected.")
        except Exception as e:
            print(f"[ERROR] Error during WebSocket disconnection: {e}")
        finally:
            await self.close()

    async def receive(self, text_data):
        # if not self.is_connected:
        #     return
        data = json.loads(text_data)
        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({
                'type': 'pong'
            }))
            print("[↔] Ping received, Pong sent.")

    async def send_ping_periodically(self):
        while True:
            try:
                await self.send(text_data=json.dumps({
                    'type': 'ping'
                }))
                await asyncio.sleep(10)
        # try:
        #     while self.is_connected:
        #         await self.safe_send({'type': 'ping'})
        #         await asyncio.sleep(20)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[PING ERROR] {e}")
                break

    # async def safe_send(self, payload):
    #     if not self.is_connected:
    #         return
    #     try:
    #         await self.send(text_data=json.dumps(payload))
    #     except Exception:
    #         self.is_connected = False

    # async def send_thermal_images(self):
    #     # if not self.is_connected:
    #     #     return
    #     start_time = timezone.localtime(timezone.now())
    #     print(f"[TIME] Image send cycle started at: {start_time.isoformat()}")
    #     try:
    #         db_start = timezone.now()
    #         # conn = psycopg2.connect(
    #         #     dbname="checktray",
    #         #     user="Vertoxlabs",
    #         #     password="Vtx@mru@#5951#new",
    #         #     host="bcpostgressqlserver12.postgres.database.azure.com",
    #         #     port="5432"
    #         # )

    #         conn = psycopg2.connect(
    #             dbname="postgres",
    #             user="postgres",
    #             password="Vtx202518",
    #             host="database-1.ce9w48qo0irl.us-east-1.rds.amazonaws.com",
    #             port="5432"
    #         )
    #         cur = conn.cursor()
    #         cur.execute("SELECT node_id, thermal_image, colour_image, created_at FROM check_tray_app_projectdata ORDER BY created_at DESC LIMIT 20")

    #         records = cur.fetchall()

    #         db_end = timezone.localtime(timezone.now())
    #         print(f"[TIME] DB fetch completed at: {db_end.isoformat()} | Took: {(db_end - db_start).total_seconds()}s")
    #         process_start = timezone.now()

    #         thermal_data = []
    #         colour_data = []

    #         for idx, row in enumerate(records, start=1):
    #             print(f"\n[INFO] Processing Record #{idx}")
    #             node_id, thermal_image_data, colour_image_data, created_at = row

    #             # Thermal image block
    #             if thermal_image_data:
    #                 try:
    #                     if isinstance(thermal_image_data, str):
    #                         thermal_image_data = thermal_image_data.encode('utf-8')
    #                     encoded = base64.b64encode(thermal_image_data).decode('utf-8')
    #                     thermal_data.append({
    #                         'node_id': node_id,
    #                         'created_at': created_at.isoformat(),
    #                         'thermal_image': encoded
    #                     })
    #                     print(f"[✓] Thermal image sent for node_id: {node_id}")
    #                 except Exception as e:
    #                     print(f"[ERROR] Thermal image encode failed for node_id {node_id}: {e}")
    #             else:
    #                 print(f"[INFO] No thermal image for node_id: {node_id}")

    #             # Colour image block
    #             if colour_image_data:
    #                 try:
    #                     if isinstance(colour_image_data, str):
    #                         colour_image_data = colour_image_data.encode('utf-8')
    #                     encoded = base64.b64encode(colour_image_data).decode('utf-8')
    #                     colour_data.append({
    #                         'node_id': node_id,
    #                         'created_at': created_at.isoformat(),
    #                         'colour_image': encoded
    #                     })
    #                     print(f"[✓] Colour image sent for node_id: {node_id}")
    #                 except Exception as e:
    #                     print(f"[ERROR] Colour image encode failed for node_id {node_id}: {e}")
    #             else:
    #                 print(f"[INFO] No colour image for node_id: {node_id}")

    #         cur.close()
    #         conn.close()

    #         process_end = timezone.localtime(timezone.now())
    #         print(f"[TIME] Image processing completed at: {process_end.isoformat()} | Took: {(process_end - process_start).total_seconds()}s")

    #         send_start = timezone.localtime(timezone.now())

    #         # Send thermal images
    #         if thermal_data:
    #             await self.send(text_data=json.dumps({
    #                 'type': 'thermal_images',
    #                 'data': thermal_data
    #             }))

    #         # Send colour images
    #         if colour_data:
    #             await self.send(text_data=json.dumps({
    #                 'type': 'colour_images',
    #                 'data': colour_data
    #             }))

    #         print(f"[✓] Sent {len(thermal_data)} thermal and {len(colour_data)} colour images to WebSocket")
            
    #         send_end = timezone.localtime(timezone.now())
    #         print(f"[TIME] WebSocket send completed at: {send_end.isoformat()} | Took: {(send_end - send_start).total_seconds()}s")

    #         print(f"[TIME] TOTAL cycle time: {(send_end - start_time).total_seconds()}s")

    #     except Exception as e:
    #         print(f"[CRITICAL] Error fetching images: {e}")
    #         await self.send(text_data=json.dumps({
    #             'type': 'error',
    #             'message': 'Failed to fetch images.'
    #         }))


    async def send_thermal_images_periodically(self):
        try:
            while True:
                await self.send_thermal_images()
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            print("[INFO] Background image task cancelled due to disconnect.")
        except Exception as e:
            print(f"[ERROR] Periodic image sending failed: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'An error occurred while sending images.'
            }))

    async def send_thermal_images(self):
        start_time = timezone.localtime(timezone.now())
        print(f"[TIME] Image send cycle started at: {start_time.isoformat()}")

        try:
            db_start = timezone.now()

            records = await fetch_latest_images()

            db_end = timezone.localtime(timezone.now())
            print(
                f"[TIME] DB fetch completed at: {db_end.isoformat()} | "
                f"Took: {(db_end - db_start).total_seconds()}s"
            )

            process_start = timezone.now()

            thermal_data = []
            colour_data = []

            for idx, row in enumerate(records, start=1):
                print(f"\n[INFO] Processing Record #{idx}")

                device_id = row["device_id"]
                image_type = row["image_type"]
                logical_path = row["logical_path"]
                created_at = row["created_at"]

                image_url = generate_read_sas(logical_path)

                payload = {
                    "node_id": device_id,
                    "created_at": created_at.isoformat(),
                    "image_url": image_url
                }

                if image_type == "thermal":
                    thermal_data.append(payload)
                    print(f"[✓] Thermal image URL prepared for node_id: {device_id}")

                elif image_type == "color":
                    colour_data.append(payload)
                    print(f"[✓] Colour image URL prepared for node_id: {device_id}")

            process_end = timezone.localtime(timezone.now())
            print(
                f"[TIME] Image processing completed at: {process_end.isoformat()} | "
                f"Took: {(process_end - process_start).total_seconds()}s"
            )

            send_start = timezone.localtime(timezone.now())

            if thermal_data:
                await self.send(text_data=json.dumps({
                    "type": "thermal_images",
                    "data": thermal_data
                }))

            if colour_data:
                await self.send(text_data=json.dumps({
                    "type": "colour_images",
                    "data": colour_data
                }))

            print(
                f"[✓] Sent {len(thermal_data)} thermal and "
                f"{len(colour_data)} colour image URLs to WebSocket"
            )

            send_end = timezone.localtime(timezone.now())
            print(
                f"[TIME] WebSocket send completed at: {send_end.isoformat()} | "
                f"Took: {(send_end - send_start).total_seconds()}s"
            )

            print(
                f"[TIME] TOTAL cycle time: "
                f"{(send_end - start_time).total_seconds()}s"
            )

        except Exception as e:
            print(f"[CRITICAL] Error sending images: {e}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Failed to fetch images."
            }))