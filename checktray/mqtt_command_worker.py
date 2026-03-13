# from .mqtt_command_queue import mqtt_publish_queue
# from .paho_mqtt import mqtt_client

# def mqtt_command_worker():

#     print("MQTT command worker started")

#     while True:

#         command = mqtt_publish_queue.get()

#         topic = command["topic"]
#         payload = command["payload"]

#         result = mqtt_client.publish(topic, payload, qos=1)

#         if result.rc == 0:
#             print(f"[MQTT PUBLISHED] {topic}")
#         else:
#             print(f"[MQTT FAILED] {topic}")

import redis
import json
from checktray import paho_mqtt

redis_client = redis.Redis(host="localhost", port=6379, db=0)

QUEUE_NAME = "mqtt_command_queue"


def mqtt_command_worker():

    print("MQTT command worker started")

    while True:

        data = redis_client.blpop(QUEUE_NAME)

        if not data:
            continue

        _, command_json = data

        command = json.loads(command_json)

        topic = command["topic"]
        payload = command["payload"]

        if paho_mqtt.mqtt_client is None:
            print("MQTT client not ready yet")
            continue

        paho_mqtt.mqtt_client.publish(topic, payload, qos=1)

        print(f"[MQTT PUBLISHED] {topic}")