import os
import sys
import json
import time
import threading
from datetime import timedelta

# ---------------- DJANGO SETUP ---------------- #
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "water.settings")
import django
django.setup()

# ---------------- THIRD PARTY ---------------- #
import paho.mqtt.client as mqtt
import requests

# ---------------- DJANGO ---------------- #
from django.utils import timezone

# ---------------- PROJECT ---------------- #
from power_monitoring.models import SensorData, MonitoringSession
from power_monitoring.views import update_session_status
from django.db import close_old_connections

# ---------------- CONFIG ---------------- #
MQTT_BROKER = "mqttbroker.bc-pl.com"
MQTT_PORT = 1883
MQTT_USER = "mqttuser"
MQTT_PASSWORD = "Bfl@2025" 

TOPIC_SENSOR = "pomon/+/rnd/status"
TOPIC_ALERT = "pomon/+/rnd/alert"
TOPIC_ABORT = "pomon/+/rnd/abort"  

# ---------------- TELEGRAM ---------------- #
TELEGRAM_BOT_TOKEN = "7119219406:AAHsLe6kqLiQmJMeTPCnYR3rg15__lvr92k"
TELEGRAM_GROUPCHAT_IDS = [-1002559440335]

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in TELEGRAM_GROUPCHAT_IDS:
        try:
            requests.post(url, data={"chat_id": chat_id, "text": message})
        except Exception as e:
            print("❌ Telegram Error:", e)

# ---------------- MQTT CALLBACKS ---------------- #
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ MQTT Connected")
        client.subscribe(TOPIC_SENSOR)
        client.subscribe(TOPIC_ALERT)
        client.subscribe(TOPIC_ABORT)
        print(f"📡 Subscribed to topics: {TOPIC_SENSOR}, {TOPIC_ALERT}, {TOPIC_ABORT}")
    else:
        print(f"❌ MQTT Connection failed with code {rc}")

def on_message(client, userdata, msg):
    topic = msg.topic
    raw_payload = msg.payload.decode()

    print("\n========== MQTT MESSAGE ==========")
    print(f"📌 Topic: {topic}")
    print(f"📦 Raw Payload: {raw_payload}")

    device_id = topic.split("/")[1]
    now = timezone.localtime()

    # ---------------- ALERT ---------------- #
    if topic.endswith("/rnd/alert"):
        print(f"⚠ ALERT from {device_id}: {raw_payload}")
        send_telegram_alert(f"⚠ Alert from {device_id}: {raw_payload}")
        return

    # ---------------- ABORT ---------------- #
    if topic.endswith("/rnd/abort"):
        print(f"🛑 Abort received from device {device_id}")

        session = MonitoringSession.objects.filter(
            device__device_id=device_id,  
            status="PROCESSING"
        ).first()

        if session:
            session.status = "ABORTED"
            session.end_time = now
            session.duration = now - session.start_time
            session.save(update_fields=["status", "end_time", "duration"])

            print(f"🛑 Session {session.id} marked as ABORTED")

        return

    # ---------------- SENSOR DATA ---------------- #
    if topic.endswith("/rnd/status"):

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            print("❌ Invalid JSON payload")
            return

        session = MonitoringSession.objects.filter(
            device__device_id=device_id,   # ✅ FIXED
            status__in=["PENDING", "PROCESSING"]
        ).order_by("start_time").first()

        if not session:
            print(f"⚠ No active session for {device_id}")
            return

        if session.status == "ABORTED":
            print(f"⛔ Session {session.id} is ABORTED")
            return

        update_session_status(session)

        if session.status != "PROCESSING":
            print(f"ℹ Session {session.id} not started yet")
            return

        device_key = f"Dev{session.main}"
        dev = payload.get(device_key)

        if not dev:
            print(f"⚠ {device_key} not found in payload")
            return

        try:
            r = float(dev.get("R", 0))
            y = float(dev.get("Y", 0))
            b = float(dev.get("B", 0))
        except Exception:
            print("❌ Invalid current values")
            return

        power = 230 * (r + y + b)
        wh = power * (5 / 3600)

        SensorData.objects.create(
            session=session,
            timestamp=now,
            voltage_r=230,
            voltage_y=230,
            voltage_b=230,
            current_r=r,
            current_y=y,
            current_b=b,
            wh=wh
        )

        print(f"⚡ Energy added → Session {session.id}: {wh:.4f} Wh")


# ---------------- SESSION WATCHER ---------------- #

def schedule_watcher():
    while True:
        close_old_connections()  

        sessions = MonitoringSession.objects.filter(
            status__in=["PENDING", "PROCESSING"]
        )

        for session in sessions:
            old_status = session.status
            update_session_status(session)

            if old_status != session.status:
                print(f"✅ Status Updated → {old_status} → {session.status} (Session {session.id})")

        time.sleep(5)


# ---------------- START ---------------- #
def start():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    threading.Thread(target=schedule_watcher, daemon=True).start()

    print("🚀 MQTT Listener Started")
    client.loop_forever()


if __name__ == "__main__":
    start()