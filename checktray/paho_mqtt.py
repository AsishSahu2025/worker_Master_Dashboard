import threading
import time
import json
import paho.mqtt.client as mqtt
from django.utils import timezone
from django.core.cache import cache
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
        # client.subscribe("feeder/+/schedule_status")
        # print('message subscribe schedule status topic.') 
        # client.subscribe(TOPIC_TELEMETRY)
        # print("message subscribed to telemetry topic.")
        # client.subscribe(BMS_TOPICS)
        # print("message subscribed battery topics.")
    else:
        print(f"Failed to connect, return code {rc}")

# def mark_schedule_completed(schedule):
#     """Mark a schedule as completed in DB."""
#     schedule.status = "Completed"
#     schedule.completed_at = timezone.now()   #  CHANGED: set completed_at
#     schedule.is_running = False
#     schedule.save(update_fields=['status', 'completed_at', 'is_running'])

#     #  CHANGED: delay clearing current_running_id
#     def clear_id():
#         # global current_running_id
#         # current_running_id = None
#         pick_next_schedule_for_device()  # continue with next job

#     threading.Timer(3, clear_id).start()  # 3s delay to allow MQTT messages

def get_running_schedule_for_device(device_id):
    return Scheduling.objects.filter(
        device_id__Device_id=device_id,
        is_running=True
    ).first()

def device_offline_watchdog(device, poll_seconds=WATCHDOG_SLEEP):
    # device_id = device.Device_id
    # time.sleep(30)

    # while True:
    #     try:
    #         last_seen = cache.get(f"last_seen_{device_id}")
    #         now = timezone.now()

    #         if not last_seen or (now - last_seen).total_seconds() > 45:
    #             update_state_and_log(device_id, "DEVICE", "OFFLINE", True, human_msg="Device went offline (no telemetry received)")
    #             for iface, svc in [
    #                 ("WIFI","INTERFACE"),("WIFI","INTERNET"),
    #                 ("GSM","INTERFACE"),("GSM","INTERNET")
    #             ]:
    #                 update_state_and_log(device_id, iface, svc, None)
    #         else:
    #             update_state_and_log(device_id, "DEVICE", "OFFLINE", False, human_msg="Device is online")

    #     except Exception as e:
    #         print(f"[WATCHDOG ERROR] {device_id}", e)

    #     time.sleep(poll_seconds)

    device_id = device.Device_id

    while True:
        try:
            last_seen = cache.get(f"last_seen_{device_id}")
            now = timezone.now()

            offline = (
                last_seen is None or
                (now - last_seen).total_seconds() > DEVICE_OFFLINE_TIMEOUT
            )

            # if offline:
            #     update_state_and_log(
            #         device_id,
            #         "DEVICE",
            #         "OFFLINE",
            #         True,
            #         human_msg="Heartbeat timeout — device offline"
            #     )

            #     for iface, svc in [
            #         ("WIFI","INTERFACE"),
            #         ("WIFI","INTERNET"),
            #         ("GSM","INTERFACE"),
            #         ("GSM","INTERNET")
            #     ]:
            #         update_state_and_log(device_id, iface, svc, None)

            # else:
            #     update_state_and_log(
            #         device_id,
            #         "DEVICE",
            #         "OFFLINE",
            #         False
            #     )

        except Exception as e:
            print(f"[WATCHDOG ERROR] {device_id}", e)

        time.sleep(poll_seconds)

def cleanup_stale_running_schedules():
    """
    Called on server startup.
    Purpose:
    - Handle schedules affected by server downtime
    """

    # now = timezone.now()

    # Handle RUNNING schedules (state unknown)
    running_schedules = Scheduling.objects.filter(
        status="Running",
        is_running=True
    )

    for sched in running_schedules:
        sched.status = "Server Restarted – State Unknown"
        sched.is_running = False
        sched.save(update_fields=["status", "is_running"])

        print(f"[RECOVERY] Running schedule {sched.id} marked unknown")

    # Handle MISSED pending schedules (start_time passed during downtime)
    missed_pending = Scheduling.objects.filter(
        status="Pending",
        is_running=False,
        start_time__lt=SERVER_START_TIME
    )

    for sched in missed_pending:
        sched.status = "Server started after schedule time – Missed Schedule"
        sched.save(update_fields=["status"])

        print(f"[RECOVERY] Pending schedule {sched.id} missed due to server start")




def watchdog_for_schedule(sched_id):
    try:
        sched = Scheduling.objects.get(id=sched_id)
    except Scheduling.DoesNotExist:
        return

    sched.refresh_from_db()


    if sched.status in ["Completed", "Aborted"]:
        return

    device_id = sched.device_id.Device_id

    while True:
        time.sleep(WATCHDOG_SLEEP)

        # Always refresh state
        sched.refresh_from_db()

        # Stop watchdog if schedule finished properly
        if sched.status in ["Completed", "Aborted"]:
            return

        last_seen = cache.get(f"last_seen_{device_id}")
        now = timezone.now()


        # Device OFFLINE → close schedule
        if last_seen is None or (now - last_seen).total_seconds() > DEVICE_OFFLINE_TIMEOUT:
            sched.status = "Device Disconnected , Cycle Skipped"
            sched.is_running = False
            sched.save(update_fields=["status", "is_running"])

            print(f"[WATCHDOG] Schedule {sched.id} closed → Device offline")

            pick_next_schedule_for_device(sched.device_id)
            return


def pick_next_schedule_for_device(device):
    now_time = timezone.now()

    if Scheduling.objects.filter(device_id=device, is_running=True).exists():
        return
    
    last_seen = cache.get(f"last_seen_{device.Device_id}")
    if not last_seen or ( timezone.now() - last_seen).total_seconds() > DEVICE_OFFLINE_TIMEOUT:
        return

    next_schedule = Scheduling.objects.filter(
        device_id=device,
        start_time__lte=now_time,
        is_running=False,
        status="Pending"
    ).order_by("start_time").first()


    if next_schedule:
        next_schedule.is_running = True
        next_schedule.status = "Running"
        next_schedule.save(update_fields=["is_running", "status"])

        threading.Thread(
            target=watchdog_for_schedule,
            args=(next_schedule.id,),
            daemon=True
        ).start()

        print(f"[STARTED] Device={device.Device_id}, Schedule={next_schedule.id}")


def scheduler_loop():
    while True:
        try:
            for device in Device.objects.all():
                pick_next_schedule_for_device(device)

        except Exception as e:
            print("[SCHEDULER ERROR]", e)

        time.sleep(CHECK_INTERVAL)


# def update_state_and_log(device_id, interface, service, new_value, base_ts=None, human_msg=None):
#     """
#     FINAL LOGIC:
#     - UNKNOWN updates recent_value = "unknown" but DO NOT rotate or log history
#     - REAL true/false behave normally
#     - If new real value equals the last known real value => no duplicate
#     """

#     ts = base_ts or timezone.now()

#     # Convert to string formats
#     if isinstance(new_value, bool):
#         incoming = "true" if new_value else "false"
#     elif new_value is None:
#         incoming = "unknown"
#     else:
#         incoming = str(new_value)

#     # Get DB object
#     obj, created = LastServiceState.objects.get_or_create(
#         device_id=device_id,
#         interface=interface,
#         service=service,
#         defaults={
#             "recent_value": incoming,
#             "last_value": None,
#             "message": human_msg or "initial",
#             "updated_at": ts,
#         }
#     )

#     prev_recent = obj.recent_value
#     prev_last   = obj.last_value

#     # ---------------------------------------------
#     # CASE 1 — UNKNOWN → rotate recent_value → last_value
#     # ---------------------------------------------
#     if incoming == "unknown":

#         # Rotate: recent_value → last_value (because unknown must not replace real value)
#         if prev_recent != "unknown":
#             obj.last_value = prev_recent   # <── THIS is the missing logic
#             obj.recent_value = "unknown"
#             obj.message = human_msg or f"{interface} {service} unknown (device offline)"

#         obj.updated_at = ts
#         obj.save(update_fields=["recent_value", "last_value", "message", "updated_at"])

#         print(f"[UNKNOWN] {device_id} {interface} {service}: {prev_recent} → UNKNOWN (no history logged)")
#         return

#     # -------------------------------------------------------
#     # CASE 2 — previous was UNKNOWN, now a real value arrived
#     # -------------------------------------------------------
#     if prev_recent == "unknown":

#     # CASE A: first real value after unknown
#         # if prev_last is None:
#         #     obj.recent_value = incoming
#         #     obj.message = human_msg or f"{interface} {service} connection restored"
#         #     obj.updated_at = ts
#         #     obj.save(update_fields=["recent_value", "message", "updated_at"])
#         #     print(f"[RECOVERED] {device_id} {interface} {service}: UNKNOWN → {incoming}")
#         #     return

#         if prev_last is None:
#             obj.last_value = "unknown"
#             obj.recent_value = incoming
#             obj.message = human_msg or f"{interface} {service} initialized"
#             obj.updated_at = ts
#             obj.save(update_fields=["recent_value", "last_value", "message", "updated_at"])

#             last_issue = (
#                 ConnectivityIssue.objects
#                 .filter(device_id=device_id, interface=interface, service=service)
#                 .order_by("-timestamp")
#                 .first()
#             )

#             if not last_issue or last_issue.value != incoming:
#                 ConnectivityIssue.objects.create(
#                     device_id=device_id,
#                     interface=interface,
#                     service=service,
#                     value=incoming,
#                     message=obj.message,
#                     timestamp=ts,
#                 )

#             return


#         # CASE B: previous real exists
#         last_real = prev_last

#         if incoming == last_real:
#             # UNKNOWN → TRUE (same real value) is still a RECOVERY
#             obj.recent_value = incoming
#             obj.message = human_msg or f"{interface} {service} connection restored"
#             obj.updated_at = ts
#             obj.save(update_fields=["recent_value", "message", "updated_at"])
#             print(f"[RECOVERED] {device_id} {interface} {service}: UNKNOWN → {incoming}")
#             return

#         # CASE C: real change
#         obj.last_value = last_real
#         obj.recent_value = incoming
#         obj.message = human_msg or f"{interface} {service} changed to {incoming}"
#         obj.updated_at = ts
#         obj.save(update_fields=["last_value","recent_value","message","updated_at"])

#         ConnectivityIssue.objects.create(
#             device_id=device_id,
#             interface=interface,
#             service=service,
#             value=incoming,
#             message=f"{interface} {service}: {'connected' if incoming == 'true' else 'disconnected'}",
#             timestamp=ts,
#         )
#         print(f"[STATE CHANGED] {device_id} {interface} {service}: {last_real} → {incoming}")
#         return


#     # -------------------------------------------------------
#     # CASE 3 — No UNKNOWN involved, NORMAL LOGIC
#     # -------------------------------------------------------

#     # SAME VALUE => no update
#     if prev_recent == incoming:
#         obj.updated_at = ts
#         if human_msg:
#             obj.message = human_msg
#         obj.save(update_fields=["updated_at", "message"])
#         return

#     # REAL VALUE CHANGE
#     obj.last_value = prev_recent
#     obj.recent_value = incoming
#     obj.updated_at = ts
#     # obj.message = human_msg or f"{interface} {service} changed to {incoming}"
#     state_msg = "connected" if incoming == "true" else "disconnected"
#     obj.message = human_msg or f"{interface} {service}: {state_msg}"
#     obj.save(update_fields=["last_value","recent_value","message","updated_at"])

#     ConnectivityIssue.objects.create(
#         device_id=device_id,
#         interface=interface,
#         service=service,
#         value=incoming,
#         message=obj.message,
#         timestamp=ts,
#     )

#     print(f"[STATE CHANGED] {device_id} {interface} {service}: {prev_recent} → {incoming}")

# def log_network_identity_if_changed(device_id, interface, new_value):
#     """
#     Stores GSM operator / WiFi SSID history
#     ONLY when value changes.
#     """

#     if not new_value:
#         return

#     last_entry = (
#         NetworkIdentityHistory.objects
#         .filter(device_id=device_id, interface=interface)
#         .order_by("-timestamp")
#         .first()
#     )

#     # Skip duplicate identity
#     if last_entry and last_entry.value == new_value:
#         return

#     NetworkIdentityHistory.objects.create(
#         device_id=device_id,
#         interface=interface,
#         value=new_value
#     )

#     print(f"[IDENTITY] {device_id} {interface} changed → {new_value}")


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

    if is_heartbeat:
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
        return



    # if is_bms:
    #     print('bms received')
    #     parameter = topic.split("/")[2]
    #     update_data = build_update_dict(parameter, message)

    #     if update_data:
    #         # buffer_bms_snapshot(device_id, update_data)
    #         print('gone for storing')
    #         mqtt_work_queue.put(( buffer_bms_snapshot,(device_id, update_data)
    # ))
    #     return


    # TELEMETRY
    # if is_signal:
    #     data = json.loads(message)

    #     update_state_and_log(device_id, "GSM", "INTERFACE", data.get("gsm_connected"))
    #     update_state_and_log(device_id, "GSM", "INTERNET", data.get("gsm_internet"))
    #     update_state_and_log(device_id, "WIFI", "INTERFACE", data.get("wifi_connected"))
    #     update_state_and_log(device_id, "WIFI", "INTERNET", data.get("wifi_internet"))
    #     log_network_identity_if_changed(device_id, "GSM", data.get("gsm_operator"))
    #     log_network_identity_if_changed(device_id, "WIFI", data.get("wifi_ssid"))
    #     return

    schedule = get_running_schedule_for_device(device_id)

    # FIX 2: fallback for restart / timing race
    if not schedule:
        schedule = (
            Scheduling.objects
            .filter(device_id__Device_id=device_id, status="Running")
            .order_by("-start_time")
            .first()
        )

    if not schedule:
        print(f"[WARN] No matching schedule for device {device_id}")
        return
    
    msg_lower=message.lower()

    # COMPLETED
    if is_cycle_status and "all cycles completed" in msg_lower:
        schedule.status = "Completed"
        schedule.completed_at = timezone.now()
        schedule.is_running = False
        schedule.save(update_fields=["status", "completed_at", "is_running"])

        pick_next_schedule_for_device(schedule.device_id)
        return
    

    # ABORTED
    if is_abort:
        schedule.status = "Aborted"
        schedule.is_running = False
        schedule.save(update_fields=["status", "is_running"])

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

