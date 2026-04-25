import redis
import json

redis_client = redis.Redis(host="localhost", port=6379, db=0)

QUEUE_NAME = "myapp_telegram_queue"


def enqueue_telegram(task_data):
    """
    Enqueue task scheduling data for Telegram notification
    """
    data = {
        "task_id": task_data.get("task_id"),
        "device_id": task_data.get("device_id"),
        "feed_amount": task_data.get("feed_amount"),
        "total_cycles": task_data.get("total_cycles"),
        "schedule_date": task_data.get("schedule_date"),
        "generate_time": task_data.get("generate_time"),
        "assignments": task_data.get("assignments", [])  # List of {cycle, worker_name, time}
    }
    redis_client.rpush(QUEUE_NAME, json.dumps(data))
