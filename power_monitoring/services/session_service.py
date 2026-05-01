import json
import threading
import time
import paho.mqtt.publish as publish
from django.utils import timezone
from power_monitoring.models import MonitoringSession, SensorData

MQTT_BROKER = "mqttbroker.bc-pl.com"
MQTT_PORT = 1883
MQTT_USER = "mqttuser"
MQTT_PASSWORD = "Bfl@2025"

SESSION_STATUS_CACHE = {}

# ================= DELAYED TRIGGER ================= #
def delayed_trigger(device_id, delay=5):
    time.sleep(delay)
    trigger_next_cycle(device_id)

# ================= UPDATE STATUS ================= #
def update_session_status(session):
    try:
        now = timezone.now()
        old_status = session.status

        if old_status in ["COMPLETED", "FAILED", "ABORTED"]:
            return

        if not session.start_time or not session.end_time:
            new_status = "PENDING"
            duration = None

        else:
            has_data = SensorData.objects.filter(session=session).exists()

            if now < session.start_time:
                new_status = "PENDING"

            elif session.start_time <= now <= session.end_time + timezone.timedelta(seconds=10):
                new_status = "PROCESSING"

            else:
                new_status = "COMPLETED" if has_data else "FAILED"

            duration = session.end_time - session.start_time

        # ================= LOG ONLY ON CHANGE ================= #
        if SESSION_STATUS_CACHE.get(session.id) != new_status:
            print(f"🔄 Session {session.id}: {old_status} ➝ {new_status}")
            SESSION_STATUS_CACHE[session.id] = new_status

        # ================= SAVE ================= #
        session.status = new_status
        session.duration = duration
        session.save(update_fields=["status", "duration"])

        # ================= TRIGGER NEXT ================= #
        if new_status == "COMPLETED" and old_status != new_status:
            threading.Thread(
                target=delayed_trigger,
                args=(session.device.device_id,),
                daemon=True
            ).start()

    except Exception as e:
        print(f"⚠️ update_session_status error {session.id}: {e}")

# ================= TRIGGER NEXT ================= #
def trigger_next_cycle(device_id):
    try:
        print("🔥 trigger_next_cycle CALLED")

        next_session = MonitoringSession.objects.filter(
            device__device_id=device_id,
            status="PENDING"
        ).order_by("cycle_number").first()

        if not next_session:
            print("✅ No more cycles")
            return

        # ❌ DO NOT SEND MQTT HERE
        print(f"⏳ Next session {next_session.id} will be triggered by watcher at correct time")

    except Exception as e:
        print(f"❌ trigger_next_cycle error: {e}")