import time
import paho.mqtt.client as mqtt
from django.utils import timezone
from django.core.cache import cache
from django.db import close_old_connections
from .models import *
from myapp.models import *
from checktray.telegram_queue import enqueue_telegram
from checktray.telegram_notifications import notify_checktray_abort, notify_checktray_cancel

SERVER_START_TIME = timezone.now()

# MQTT Configuration
MQTT_BROKER = 'mqttbroker.bc-pl.com'
MQTT_PORT = 1883
MQTT_USER = 'mqttuser'
MQTT_PASSWORD = 'Bfl@2025'
SCHEDULE_STATUS= "feeder/+/schedule_status"
SCHEDULE_CANCLE= "feeder/+/schedule_cancle"
STATUS_TOPIC = "feeder/+/cycle_status"
ABORT_TOPIC = "feeder/+/cycle_abort"
ALIVE_TOPIC="feeder/+/heartbeat"
mqtt_client = None
mqtt_connected= False
CHECK_INTERVAL = 3  # scheduler loop sleep
WATCHDOG_SLEEP = 3  # offline watchdog poll interval (seconds)
MQTT_GRACE_SECONDS = 10
DEVICE_OFFLINE_TIMEOUT= 20
HEARTBEAT_INTERVAL=5

def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected= True
        print("Connected to MQTT broker.")
        client.subscribe(ALIVE_TOPIC)
        print('message subscribed heartbeat topic.')
        client.subscribe(STATUS_TOPIC)
        print('message subscribed status topic.')
        client.subscribe(ABORT_TOPIC)
        print('message subscribed aborted topic.')
        client.subscribe(SCHEDULE_STATUS)
        print('message subscribed schedule status topic.')
        client.subscribe(SCHEDULE_CANCLE)
        print('message subscribed schedule cancle topic.')
    else:
        print(f"Failed to connect, return code {rc}")



def cleanup_stale_running_schedules():
    """
    Called on server startup.
    Purpose:
    - Handle schedules affected by server downtime
    """

    # Handle RUNNING schedules (state unknown)
    running_schedules = ChecktrayTask.objects.filter(
        status="Running"
    )

    for sched in running_schedules:
        sched.status = "Server Restarted – State Unknown"
        sched.save(update_fields=["status"])

        print(f"[RECOVERY] Running schedule {sched.id} marked unknown")

    # Handle MISSED pending schedules (start_time passed during downtime)
    missed_pending = ChecktrayTask.objects.filter(
        status__in=["Pending","ScheduleRequested"],
        start_time__lt=timezone.now()
    )

    for sched in missed_pending:
        sched.status = "Server started after schedule time – Missed Schedule"
        sched.submit = "True"
        sched.save(update_fields=["status","submit"])

        print(f"[RECOVERY] {sched.status} schedule {sched.id} missed due to server start")




def watchdog_for_schedule(sched):
    device_id = sched.device_id.device_id
    last_seen = cache.get(f"last_seen_{device_id}")
    now = timezone.now()

    print("\n[WATCHDOG DEBUG]")
    print("Device:", device_id)
    print("Now:", now)
    print("Last Seen:", last_seen)

    if last_seen:
        diff = (now - last_seen).total_seconds()
        print("Time Diff (seconds):", diff)
    else:
        print("Last Seen is None ❌")


    if sched.status in ["Completed", "Aborted"]:
        return

    if not last_seen or (
        timezone.now() - last_seen
    ).total_seconds() > DEVICE_OFFLINE_TIMEOUT:
        print("inside watchdog ---------------------------------------------------------------")

        sched.status = "Device Disconnected"
        sched.save(update_fields=["status"])

        print(f"[WATCHDOG] Closed schedule {sched.id}")

        pick_next_schedule_for_device(sched.device_id)


def pick_next_schedule_for_device(device):

    running = (
        ChecktrayTask.objects
        .filter(device_id=device, status="Running")
        .only("id")
        .first()
    )

    # already running?
    if running:
        return

    # device offline?
    last_seen = cache.get(f"last_seen_{device.device_id}")
    if not last_seen or (
        timezone.now() - last_seen
    ).total_seconds() > DEVICE_OFFLINE_TIMEOUT:
        return

    next_schedule = (
        ChecktrayTask.objects.filter(
            device_id=device,
            status="Pending",
            start_time__lte=SERVER_START_TIME
        )
        .order_by("start_time")
        .first()
    )

    if not next_schedule:
        return

    # ATOMIC START (prevents double execution)
    updated = ChecktrayTask.objects.filter(
        id=next_schedule.id,
        status="Pending"
    ).update(
        status="Running"
    )

    if updated:
        print(f"[STARTED] Device={device.device_id}, Schedule={next_schedule.id}")

def watchdog_loop():

    while True:
        close_old_connections()

        try:
            # running = ChecktrayTask.objects.filter(is_running=True)

            running = (
                ChecktrayTask.objects
                .filter(status="Running")
                .select_related("device_id")
                .only("id", "status", "device_id__device_id")
            )
            for sched in running:
                watchdog_for_schedule(sched)

        except Exception as e:
            print("[WATCHDOG ERROR]", e)

        time.sleep(WATCHDOG_SLEEP)


def scheduler_loop():
    while True:
        close_old_connections()

        try:
            ready_schedules = (
                ChecktrayTask.objects
                .filter(
                    status="Pending",
                    start_time__lte=timezone.now()
                )
                .select_related("device_id")
                .order_by("start_time")
            )

            running_devices = set(
                ChecktrayTask.objects
                .filter(status="Running")
                .values_list("device_id", flat=True)
            )

            for sched in ready_schedules:

                if sched.device_id_id in running_devices:
                    continue

                updated = ChecktrayTask.objects.filter(
                    id=sched.id,
                    status="Pending"
                ).update(status="Running")

                if updated:
                    running_devices.add(sched.device_id_id)
                    print(
                        f"[STARTED] Device={sched.device_id.device_id}, "
                        f"Schedule={sched.id}"
                    )

        except Exception as e:
            print("[SCHEDULER ERROR]", e)

        time.sleep(CHECK_INTERVAL)




def on_message(client, userdata, msg):
    print("MQTT MESSAGE RECEIVED!!!!!")
    #global current_running_id
    
    topic = msg.topic
    message = msg.payload.decode().strip()

    # 🔹 Extract device_id ONCE
    device_id = topic.split("/")[1]

    # CRITICAL FIX: Ignore unknown devices
    if not Device.objects.filter(device_id=device_id).exists():
        print(f"[MQTT] Ignored unknown device: {device_id}")
        return
    
    is_heartbeat = topic.endswith("heartbeat")
    is_cycle_status = topic.endswith("cycle_status")
    is_abort = topic.endswith("cycle_abort")
    sche_status= topic.endswith("schedule_status")

    print(f"[MQTT] {topic} -> {message}")

    if is_heartbeat:
        now = timezone.now()
        cache.set(f"last_seen_{device_id}", timezone.now(), None)
        print("last seen time",cache.get(f"last_seen_{device_id}"))
        print(f"[HEARTBEAT] {device_id} alive at {now}")
        return

    msg_lower=message.lower()
    print('msg lower',msg_lower)

    if sche_status and "scheduled:" in msg_lower:
        print(sche_status)
        sched = (
        ChecktrayTask.objects
        .filter(device_id__device_id=device_id, status="ScheduleRequested")
        .order_by("-start_time")
        .first())

        if not sched:
            print(f"[WARN] schedule_status received but no ScheduleRequested for {device_id}")
            return

        sched.status = "Pending"
        sched.submit = "True"
        print(sched.status)
        sched.save(update_fields=["status","submit"])

        print(f"[DEVICE CONFIRMED SCHEDULE] {sched.device_id}")

        enqueue_telegram(sched.id)

        return
    
    if sche_status and "rejected:" in msg_lower:
        print('inside reject schedule')

        sched = (
            ChecktrayTask.objects
            .filter(device_id__device_id=device_id, status__in=["Pending","ScheduleRequested"])
            .order_by("-start_time")
            .first()
        )

        if not sched:
            print(f"[WARN] reject received but no pending status for {device_id}")
            return

        # no telegram here
        sched.delete()

        print(f"[DEVICE REJECTED] {sched.device_id}")
        return
    
    if sche_status and "canceled:" in msg_lower:
        print('inside cancle schedule')
        sched = (
        ChecktrayTask.objects
        .filter(device_id__device_id=device_id, status__in=["Pending","ScheduleRequested"])
        .order_by("-start_time")
        .first())

        if not sched:
            print(f"[WARN] schedule_status received but no pending status for {device_id}")
            return
        
        notify_checktray_cancel(sched)
        sched.delete()
        
        print(f"[DEVICE CONFIRMED SCHEDULE CANCLE] {sched.device_id}")

    schedule = (
    ChecktrayTask.objects
    .filter(device_id__device_id=device_id, status="Running")
    .order_by("-start_time")
    .first()
)

    if not schedule:
        print(f"[WARN] No matching schedule for device {device_id}")
        return
    

    if schedule.status != "Running":
        return

    # COMPLETED
    if is_cycle_status and "all cycles completed" in msg_lower:
        print('------------------------completed-------------------------------------')
        schedule.status = "Completed"
        schedule.stop_time = timezone.now()
        schedule.save(update_fields=["status", "stop_time"])
        enqueue_telegram(schedule.id)  # ← ADD THIS LINE

        pick_next_schedule_for_device(schedule.device_id)
        return
    

    # ABORTED
    if is_abort and "aborted" in msg_lower:
        schedule.delete()
        notify_checktray_abort(schedule)

        pick_next_schedule_for_device(schedule.device_id)
        return
    



def start_mqtt_client():
    global mqtt_client
    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
    print('mqtt_client process completed')

