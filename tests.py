import paho.mqtt.client as mqtt
import json
import time

BROKER = "mqttbroker.bc-pl.com"   # same as subscriber
PORT = 1883
DEVICE_ID = "BFL_FdtryA001"
TOPIC = f"auto_feeder/{DEVICE_ID}/system/alert"
USERNAME = "mqttuser"
PASSWORD = "Bfl@2025"


payload = ""


def on_connect(client, userdata, flags, rc):
    print("Connected with rc:", rc)

client = mqtt.Client(client_id="test_publisher")
client.username_pw_set(USERNAME, PASSWORD)
client.on_connect = on_connect

client.connect(BROKER, PORT, 60)

# 🔑 THIS IS THE MISSING PART
client.loop_start()

client.publish(TOPIC, json.dumps(payload), qos=1)

time.sleep(1)   # give time to send packet

client.loop_stop()
client.disconnect()

print("Published correctly")
