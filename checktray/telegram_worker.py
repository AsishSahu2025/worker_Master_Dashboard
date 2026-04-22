import redis
import json
from checktray.telegram_notifications import notify_checktray_task

redis_client = redis.Redis(host="localhost", port=6379, db=0)

QUEUE_NAME = "telegram_queue"


def telegram_worker():
    print("📩 Telegram worker started")

    while True:
        data = redis_client.blpop(QUEUE_NAME)

        if not data:
            continue

        _, json_data = data
        payload = json.loads(json_data)

        task_id = payload["task_id"]

        try:
            notify_checktray_task(task_id)
            print(f"[TELEGRAM SENT] Task {task_id}")
        except Exception as e:
            print("[TELEGRAM ERROR]", e)