import redis
import json
import logging
from myapp.telegram_notifications import notify_task_schedule

logger = logging.getLogger(__name__)

redis_client = redis.Redis(host="localhost", port=6379, db=0)

QUEUE_NAME = "myapp_telegram_queue"


def telegram_worker():
    """
    Background worker that processes Telegram notifications from Redis queue
    """
    print("📩 MyApp Telegram worker started")

    while True:
        try:
            data = redis_client.blpop(QUEUE_NAME)

            if not data:
                continue

            _, json_data = data
            payload = json.loads(json_data)

            try:
                result = notify_task_schedule(payload)
                if result:
                    print(f"[TELEGRAM SENT] Task ID: {payload.get('task_id')}, Device: {payload.get('device_id')}")
                else:
                    print(f"[TELEGRAM FAILED] Task ID: {payload.get('task_id')}")
            except Exception as e:
                logger.error(f"[TELEGRAM ERROR] {e}")
                print(f"[TELEGRAM ERROR] {e}")
        except Exception as e:
            logger.error(f"[WORKER ERROR] {e}")
            print(f"[WORKER ERROR] {e}")
            continue
