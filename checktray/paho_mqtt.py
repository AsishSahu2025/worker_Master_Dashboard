import threading
import time
import json
import paho.mqtt.client as mqtt
from django.utils import timezone
from django.core.cache import cache
from django.db import close_old_connections
# from app1.bms.utils import build_update_dict, buffer_bms_snapshot
# from .mqtt_worker import *
from .models import *
from myapp.models import *

SERVER_START_TIME = timezone.now()

# MQTT Configuration
MQTT_BROKER = 'mqttbroker.bc-pl.com'
MQTT_PORT = 1883
MQTT_USER = 'mqttuser'
MQTT_PASSWORD = 'Bfl@2025'
STATUS_TOPIC = "feeder/+/cycle_status"
ABORT_TOPIC = "feeder/+/cycle_abort"
TOPIC_TELEMETRY = f"feeder/+/telemetry/signal"
BMS_TOPICS="bms/+/+"
ALIVE_TOPIC="feeder/+/heartbeat"
mqtt_client = None
CHECK_INTERVAL = 3  # scheduler loop sleep
WATCHDOG_SLEEP = 3  # offline watchdog poll interval (seconds)
MQTT_GRACE_SECONDS = 10
DEVICE_OFFLINE_TIMEOUT= 6
HEARTBEAT_INTERVAL=5

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker.")
        client.subscribe(ALIVE_TOPIC)
        print('message subscribed heartbeat topic.')
        client.subscribe(STATUS_TOPIC)
        print('message subscribed status topic.')
        client.subscribe(ABORT_TOPIC)
        print('message subscribed aborted topic.')
    else:
        print(f"Failed to connect, return code {rc}")


# def get_running_schedule_for_device(device_id):
#     return ChecktrayTask.objects.filter(
#         device_id__Device_id=device_id,
#         is_running=True
#     ).first()

# def device_offline_watchdog(device, poll_seconds=WATCHDOG_SLEEP):
#     device_id = device.Device_id

#     while True:
#         try:
#             last_seen = cache.get(f"last_seen_{device_id}")
#             now = timezone.now()

#             offline = (
#                 last_seen is None or
#                 (now - last_seen).total_seconds() > DEVICE_OFFLINE_TIMEOUT
#             )

#         except Exception as e:
#             print(f"[WATCHDOG ERROR] {device_id}", e)

#         time.sleep(poll_seconds)

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
        status="Pending",
        start_time__lt=timezone.now()
    )

    for sched in missed_pending:
        sched.status = "Server started after schedule time – Missed Schedule"
        sched.save(update_fields=["status"])

        print(f"[RECOVERY] Pending schedule {sched.id} missed due to server start")




def watchdog_for_schedule(sched):
    device_id = sched.device_id.device_id
    last_seen = cache.get(f"last_seen_{device_id}")

    if sched.status in ["Completed", "Aborted"]:
        return

    if not last_seen or (
        timezone.now() - last_seen
    ).total_seconds() > DEVICE_OFFLINE_TIMEOUT:

        sched.status = "Device Disconnected, Cycle Skipped"
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


# def scheduler_loop():
#     while True:
#         close_old_connections()
#         try:
#             now_time = timezone.localtime().time()
#             ready_schedules = (
#             #     Device.objects
#             #     .filter(checktraytask__status="Scheduled")
#             #     .distinct()
#             # )
#                 ChecktrayTask.objects
#                 .filter(
#                     status="Scheduled",
#                     start_time__lte=now_time
#                 )
#                 .select_related("device_id")
#                 .order_by("start_time")
#             )
#             # for device in devices:
#             #     pick_next_schedule_for_device(device)

#             for sched in ready_schedules:

#                 updated = ChecktrayTask.objects.filter(
#                     id=sched.id,
#                     status="Scheduled"
#                 ).update(
#                     status="Running"
#                 )

#                 if updated:
#                     print(
#                         f"[STARTED] Device={sched.device_id.Device_id}, "
#                         f"Schedule={sched.id}"
#                     )


#         except Exception as e:
#             print("[SCHEDULER ERROR]", e)

#         time.sleep(CHECK_INTERVAL)

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
    # normalized = " ".join(message.split()).lower()

    # 🔹 Extract device_id ONCE
    device_id = topic.split("/")[1]

    # CRITICAL FIX: Ignore unknown devices
    # if not Device.objects.filter(Device_id=device_id).exists():
    #     print(f"[MQTT] Ignored unknown device: {device_id}")
    #     return
    
    is_heartbeat = topic.endswith("heartbeat")
    # is_signal = topic.endswith("telemetry/signal")
    is_cycle_status = topic.endswith("cycle_status")
    is_abort = topic.endswith("cycle_abort")
    # is_bms= topic.startswith("bms/")

    # if is_signal:
    #     now = timezone.now()
    #     # FIX 1: ANY valid MQTT message means device is alive
    #     cache.set(f"last_seen_{device_id}", now, None)
    print(f"[MQTT] {topic} -> {message}")

    cache.set(f"last_seen_{device_id}", timezone.now(), None)
    print(f"[HEARTBEAT] {device_id} alive", timezone.now())
        # state = LastServiceState.objects.filter(
        # device_id=device_id,
        # interface="DEVICE",
        # service="OFFLINE"
        # ).first()

        # if not state or state.recent_value != "false":
        #     update_state_and_log(
        #         device_id,
        #         "DEVICE",
        #         "OFFLINE",
        #         False,
        #         human_msg="Heartbeat received — device online"
        #     )
        # return


    # schedule = get_running_schedule_for_device(device_id)
    schedule = (
    ChecktrayTask.objects
    .filter(device_id__device_id=device_id, status="Running")
    .order_by("-start_time")
    .first()
)

    if not schedule:
        print(f"[WARN] No matching schedule for device {device_id}")
        return
    
    msg_lower=message.lower()

    if schedule.status != "Running":
        return

    # COMPLETED
    if is_cycle_status and "all cycles completed" in msg_lower:
        schedule.status = "Completed"
        schedule.stop_time = timezone.now()
        schedule.save(update_fields=["status", "stop_time"])

        pick_next_schedule_for_device(schedule.device_id)
        return
    

    # ABORTED
    if is_abort:
        schedule.status = "Aborted"
        schedule.stop_time= timezone.now()
        schedule.save(update_fields=["status", "stop_time"])

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

