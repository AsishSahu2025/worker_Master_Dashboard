import redis
import json

redis_client = redis.Redis(host="localhost", port=6379, db=0)

QUEUE_NAME = "telegram_queue"


def enqueue_telegram(task_id):
    data = {
        "task_id": task_id
    }
    redis_client.rpush(QUEUE_NAME, json.dumps(data))