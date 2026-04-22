import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from myapp.models import *  
from django.utils import timezone
from myapp.utils import apply_extra_feed_if_last_cycle, trigger_device
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
                # print(payload)
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
            
                # auto_feed=getattr(task,'auto_feed_rate')
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

                    # 🔥 UPDATE END TIME (your same logic, just using existing duration)
                    if task.from_time:
                        start_dt = datetime.combine(date.today(), task.from_time)
                        end_dt = start_dt + timedelta(minutes=int(duration))
                        task.to_time = end_dt.time()

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
                    # task = Task.objects.get(id=state.task_id)
                    # # 🔥 APPLY FINAL FEED LOGIC

                    # # 🔥 RECALCULATE TIME BASED ON FEED
                    # # feed_kg = float(task.feedin or 0)
                    # # get total feed from cycle 1
                    # first_task = Task.objects.filter(
                    #     device=task.device,
                    #     cycles=1
                    # ).first()

                    # total_feed = float(first_task.feedin or 0)

                    # # calculate current cycle feed
                    # feed_kg = (total_feed * task.feed_weight) / 100

                    # # seconds = int((feed_kg * 1000) / 13)   # your formula
                    # # minutes = seconds // 60

                    # # task.time_interval = str(minutes)
                    # use_feed = feed_kg * 1000   # convert to grams
                    # duration = math.ceil(use_feed / 800)  # minutes
                    # task.time_interval = str(duration)

                    # # update time
                    # # if task.from_time:
                    # #     start_dt = datetime.combine(date.today(), task.from_time)
                    # #     end_dt = start_dt + timedelta(seconds=seconds)
                    # #     task.to_time = end_dt.time()
                    # if task.from_time:
                    #     start_dt = datetime.combine(date.today(), task.from_time)
                    #     end_dt = start_dt + timedelta(minutes=duration)
                    #     task.to_time = end_dt.time()

                    # # 🔥 NOW PREPARE PAYLOAD
                    # formatted_time = task.from_time.strftime("%H:%M")
                    # duration = task.time_interval

                    # auto_feed = int(task.auto_feed_rate or 0)
                    # auto_sprinkle = getattr(task, 'auto_sprinkle_rate')

                    # load = f"{formatted_time},{duration},{auto_feed},{auto_sprinkle}"
                    # print(load)

                    # # 🔥 SAVE BEFORE SENDING
                    # task.status = "processing"
                    # task.is_published = True
                    # task.save()

                    # client.publish(TOPIC_SCHEDULE, load, qos=1)

                    # print("step 2 success")

                    # # 🔥 APPLY EXTRA FEED HERE
                    # task = apply_extra_feed_if_last_cycle(task)

                    # # reload updated values
                    # start_time = task.from_time
                    # formatted_time = start_time.strftime("%H:%M")
                    # duration = task.time_interval

                    # # 🔥 USE UPDATED FEED
                    # auto_feed = int(task.feedin or 0)
                    # auto_sprinkle = getattr(task, 'auto_sprinkle_rate')

                    # load = f"{formatted_time},{duration},{auto_feed},{auto_sprinkle}"
                    # print(load)

                    # client.publish(TOPIC_SCHEDULE, load, qos=1)

                    # task.status = "processing"
                    # task.is_published = True
                    # task.save()
                    # load=f"{formatted_time},{duration},{auto_feed},{auto_sprinkle}"
                    # print(load)
                    # client.publish(TOPIC_SCHEDULE,load, qos=1)
                    # task = Task.objects.get(id=state.task_id)
                    # task.status = "processing"
                    # task.is_published = True
                    # task.save()
                    # print("step 2 success")
                    # state.step = 0
                    # state.save()

                elif "Auto event completed at" in payload:
                    print("✅ Cycle completed, moving to next")

                    # Get current task
                    task = Task.objects.get(id=state.task_id)

                    # Mark completed + release device
                    task.status = "completed"  # VERY IMPORTANT
                    task.save()

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
                    print("⚠️ Abort received from device")

                    task = Task.objects.get(id=state.task_id)

                    # mark abort + release device
                    task.status = "abort"
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
        
