import redis
import json

redis_client = redis.Redis(host="localhost", port=6379, db=0)

QUEUE_NAME = "mqtt_command_queue"


def enqueue_mqtt_command(topic, payload):

    command = {
        "topic": topic,
        "payload": payload
    }

    redis_client.rpush(QUEUE_NAME, json.dumps(command))