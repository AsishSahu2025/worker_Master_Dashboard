import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from myapp.models import *
from myapp.utils import trigger_device
import math
# MQTT Broker Configuration
BROKER = "mqttbroker.bc-pl.com"  # Remote broker
PORT = 1883
USERNAME = "mqttuser"
PASSWORD = "Bfl@2025"

# Subscribe to all devices using wildcard
#-------------------------------------------------------------
#                             TOPICS
#-------------------------------------------------------------
ALL_DEVICES_TOPIC = "auto_feeder/+/system/alert"
TOPIC_AUTO="auto_feeder/+/mode/switch"
TOPIC_STATUS="auto_feeder/+/auto/status"
from datetime import datetime, timedelta, date
#--------------------------------------+-----------------------
class Command(BaseCommand):
    help = 'Subscribe to system alert topic and save messages to Alert_message table'

    def handle(self, *args, **options):
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.stdout.write(self.style.SUCCESS("✅ Connected to MQTT broker"))
                client.subscribe(ALL_DEVICES_TOPIC)
                client.subscribe(TOPIC_AUTO)
                client.subscribe(TOPIC_STATUS)
                self.stdout.write(self.style.SUCCESS(f"🔔 Subscribed to topic: {ALL_DEVICES_TOPIC}"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Connection failed with code {rc}"))

        def on_message(client, userdata, msg):
            try:
                payload = msg.payload.decode()
                topic_parts = msg.topic.split('/')
                device_id = None
                
                if len(topic_parts) >= 4 and topic_parts[0] == 'auto_feeder':
                    device_id = topic_parts[1]
                    
                self.stdout.write(f"📩 Message from device {device_id}: {payload}")
                cleaned_payload = payload.strip()
                if not cleaned_payload:
                    print("⚠️ Empty or whitespace message received. Skipping save.")
                    return
                else:
                    Alert_message.objects.create(alert=payload, device_id=device_id)
                self.stdout.write(self.style.SUCCESS(f"✅ Message from device {device_id} saved to Alert_message table"))
                
                state, _ = DeviceCommandState.objects.get_or_create(device_id=device_id)
                print(device_id)
                TOPIC_DOOR = f"auto_feeder/{device_id}/door/set_position"
                TOPIC_SCHEDULE=f"auto_feeder/{device_id}/schedule"
        
                task=Task.objects.filter(device__device_id=device_id,id=state.task_id).first()
                duration=getattr(task,'time_interval')
                print(duration)
                start_time=getattr(task,'from_time')
                formatted_time = start_time.strftime("%H:%M")
            
                auto_feed = int(task.feedin or 0)
                auto_sprinkle=getattr(task,'auto_sprinkle_rate')
                door=getattr(task,'auto_door')

                payload = payload.strip()
            
                # 🔁 STEP LOGIC
                if state.step == 1 and payload == "AUTO":
                    result = client.publish(TOPIC_DOOR,f"{door}", qos=1)
                    if result.rc != 0:
                        print("❌ MQTT publish failed")
                    else:
                        print("✅ Door command sent to device")
                    print("step 1 success")
                    state.step = 2
                    state.save()

                elif state.step == 2 and payload == f"Door set to {door} steps":
                    task = Task.objects.get(id=state.task_id)
                    task.refresh_from_db()

                    # 🔥 USE ALREADY CALCULATED VALUES (DO NOT RECALCULATE)
                    duration = task.time_interval

                    # 🔥 SAFETY CHECK
                    if not duration:
                        print("❌ Duration missing, skipping trigger")
                        return

                    # 🔥 PREPARE PAYLOAD (NO CHANGE IN FORMAT)
                    formatted_time = task.from_time.strftime("%H:%M")
                    auto_feed = int(task.auto_feed_rate or 0)
                    auto_sprinkle = getattr(task, 'auto_sprinkle_rate')

                    load = f"{formatted_time},{duration},{auto_feed},{auto_sprinkle}"
                    print(load)

                    # 🔥 SAVE BEFORE SENDING (same as your logic)
                    task.status = "processing"
                    task.is_published = True
                    task.save()

                    # 🔥 SEND TO DEVICE
                    client.publish(TOPIC_SCHEDULE, load, qos=1)

                    print("step 2 success")

                elif "Auto event completed at" in payload:
                    print("✅ Cycle completed, moving to next")

                    # Get current task
                    task = Task.objects.get(id=state.task_id)

                    # Mark completed + release device
                    task.status = "completed"  # VERY IMPORTANT
                    task.save()

                    # Send Telegram notification for completion
                    try:
                        from myapp.telegram_notifications import notify_task_completion
                        
                        device_id_str = device_id
                        cycle_no = getattr(task, 'cycles', '—')
                        worker_name_obj = getattr(task, 'worker_name', None)
                        worker_name = str(worker_name_obj) if worker_name_obj else 'Unknown'
                        
                        completion_data = {
                            "device_id": device_id_str,
                            "cycle": cycle_no,
                            "worker_name": worker_name
                        }
                        
                        notify_task_completion(completion_data)
                        print(f"[TELEGRAM COMPLETE] Notification sent for Device {device_id_str}, Cycle {cycle_no}")
                    except Exception as e:
                        print(f"[TELEGRAM COMPLETE ERROR] {e}")

                    # Find NEXT cycle strictly (NO reuse, NO same task)
                    next_task = Task.objects.filter(
                        device__device_id=device_id,
                        status='scheduled',
                        cycles__gt=task.cycles   # ONLY NEXT cycles
                    ).order_by("cycles").first()

                    if not next_task:
                        print("✅ No more cycles left")
                        return

                    print(f"➡️ Next cycle found: C{next_task.cycles}")

                    # SAFETY: prevent duplicate trigger
                    running = Task.objects.filter(
                        device__device_id=device_id,
                        status="processing"
                    ).exists()

                    if running:
                        print("⛔ Device still running, skip trigger")
                        return

                    print("🚀 Triggering next cycle")

                    trigger_device(device_id, next_task.id)

                elif "Auto event aborted" in payload:
                    print("⚠️ Aborted received from device")

                    task = Task.objects.get(id=state.task_id)

                    # mark abort + release device
                    task.status = "aborted"
                    task.to_time = datetime.now().time()
                    task.is_published = True   # IMPORTANT
                    task.save()

                    # get next cycle STRICTLY
                    next_task = Task.objects.filter(
                        device__device_id=device_id,
                        batch_id=task.batch_id,          # 🔥 add
                        schedule_date=task.schedule_date,
                        status='scheduled',
                        cycles__gt=task.cycles   # KEY FIX
                    ).order_by("cycles").first()

                    if not next_task:
                        print("✅ No more cycles left")
                        return

                    print(f"➡️ Next cycle found: C{next_task.cycles}")

                    # SAFETY: ensure no running task
                    running = Task.objects.filter(
                        device__device_id=device_id,
                        batch_id=task.batch_id,          # 🔥 add
                        schedule_date=task.schedule_date,
                        status="processing"
                    ).exists()

                    if running:
                        print("⛔ Device still processing, skip trigger")
                        return

                    print("🚀 Triggering next cycle")

                    # JUST CALL THIS (no manual logic)
                    trigger_device(device_id, next_task.id)

                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error saving message: {e}"))

        def on_disconnect(client, userdata, rc):
            self.stdout.write(f"⚠️ Disconnected with code {rc}")
            if rc != 0:
                self.stdout.write("🔄 Attempting to reconnect...")
                try:
                    client.reconnect()
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Reconnection failed: {e}"))

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        
        # Only set credentials if provided
        if USERNAME and PASSWORD:
            client.username_pw_set(USERNAME, PASSWORD)
            
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect

        try:
            self.stdout.write(f"🔌 Connecting to {BROKER}:{PORT}...")
            client.connect(BROKER, PORT, 60)
            client.loop_forever()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ MQTT connection error: {e}"))
        
