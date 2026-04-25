import time
import paho.mqtt.client as mqtt
from .models import DeviceCommandState, Task
from .validator import check_interval
BROKER = "mqttbroker.bc-pl.com"   # same as subscriber
PORT = 1883
USERNAME = "mqttuser"
PASSWORD = "Bfl@2025"

def trigger_device(device_id, task_id):

    task = Task.objects.get(id=task_id)

    # Apply last cycle logic ONLY here
    task = apply_extra_feed_if_last_cycle(task)
    task.save()


    # Check if device already running
    running_task = Task.objects.filter(
        device__device_id=device_id,
        batch_id=task.batch_id,
        schedule_date=task.schedule_date,
        status="processing"
    ).exists()

    if running_task:
        print("⛔ Device busy, skipping trigger")
        return False

    # Mark this task active
    task.is_published = True
    task.status = "processing"
    task.save()

    #---------------------- Threading------------------------------
    check_interval.delay(task.id)

    # Update device state
    DeviceCommandState.objects.update_or_create(
        device_id=device_id,
        defaults={"step": 1, "task_id": task.id}
    )

    TOPIC = f"auto_feeder/{device_id}/mode/switch"

    client = mqtt.Client(
        client_id=f"tasksubmit_{device_id}_{int(time.time())}",
        protocol=mqtt.MQTTv311
    )

    def on_connect(client, userdata, flags, rc):
        print("Connected with rc:", rc)

    client.on_connect = on_connect

    if USERNAME and PASSWORD:
        client.username_pw_set(USERNAME, PASSWORD)

    client.loop_start()
    client.connect(BROKER, 1883, 60)

    client.publish(TOPIC, "AUTO", qos=1)

    time.sleep(1)

    client.loop_stop()
    client.disconnect()

    print(f"AUTO triggered for Task {task.id}")

    return True

from django.db.models import Sum
from datetime import datetime, date, timedelta

def apply_extra_feed_if_last_cycle(task):

    last_task = Task.objects.filter(
        device=task.device,
        batch_id=task.batch_id,
        schedule_date=task.schedule_date
    ).order_by('-cycles').first()

    # Only apply if LAST cycle
    if not last_task or task.id != last_task.id:
        return task

    extra_feed = float(last_task.extra_feed or 0)

    # ============================================================
    # NEW: SKIP IF NO EXTRA FEED
    # ============================================================
    if extra_feed == 0:
        print("⏭️ No extra feed → skipping")
        return task
    # ============================================================

    print("🔥 LAST CYCLE → ADD EXTRA FEED")

    # ============================================================
    # UPDATED: DO NOT RECALCULATE REMAINING
    # ============================================================
    base_feed = float(task.feedin or 0)
    final_feed = base_feed + extra_feed
    # ============================================================

    # update task
    task.feedin = final_feed

    # percentage (for consistency only)
    first_task = Task.objects.filter(
        device=task.device,
        batch_id=task.batch_id,
        schedule_date=task.schedule_date,
        cycles=1
    ).first()

    total_feed = float(first_task.feedin or 0)

    percentage = (final_feed / total_feed) * 100 if total_feed > 0 else 0

    task.feedin_percentage = percentage
    task.feed_weight = percentage

    # ============================================================
    # KEEP TIME LOGIC (JUST IMPROVE)
    # ============================================================
    import math
    seconds = int((final_feed * 1000) / 13)
    minutes = math.ceil(seconds / 60)
    # ============================================================

    if task.from_time:
        start_dt = datetime.combine(date.today(), task.from_time)
        end_dt = start_dt + timedelta(seconds=seconds)

        task.to_time = end_dt.time()
        task.time_interval = str(minutes)

    # reset extra feed
    task.extra_feed = 0
    task.save(update_fields=["extra_feed"])

    print(f"✅ Final Feed: {final_feed}, Duration: {minutes} mins")

    return task
