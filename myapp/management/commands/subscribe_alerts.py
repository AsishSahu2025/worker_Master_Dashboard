import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from myapp.models import *  

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
        
                task=Task.objects.filter(device=device_id,id=state.task_id).first()
                duration=getattr(task,'time_interval')
                print(duration)
                start_time=getattr(task,'from_time')
                formatted_time = start_time.strftime("%H:%M")
            
                auto_feed=getattr(task,'auto_feed_rate')
                auto_sprinkle=getattr(task,'auto_sprinkle_rate')
                door=getattr(task,'auto_door')
            
                # 🔁 STEP LOGIC
                if state.step == 1 and payload == "AUTO":
                    client.publish(TOPIC_DOOR,f"{door}", qos=1)
                    print("step 1 success")
                    state.step = 2
                    state.save()

                elif state.step == 2 and payload == f"Door set to {door} steps":
                    load=f"{formatted_time},{duration},{auto_feed},{auto_sprinkle}"
                    print(load)
                    client.publish(TOPIC_SCHEDULE,load, qos=1)
                    print("step 2 success")
                    state.step = 0
                    state.save()

                elif state.step == 0 and payload.startswith("Auto event completed at"):
                    print("✅ Process completed")
                    
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
        
