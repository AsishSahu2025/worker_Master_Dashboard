import os
import sys
import json
import time
import threading

from datetime import timedelta
from django.db import close_old_connections

# ================= DJANGO SETUP ================= #
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "water.settings")

import django
django.setup()

# ================= MQTT ================= #
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import requests

# ================= DJANGO ================= #
from django.utils import timezone

# ================= PROJECT ================= #
from power_monitoring.models import SensorData, MonitoringSession
from power_monitoring.utils.telegram_cards import generate_live_data_card
from power_monitoring.services.session_service import update_session_status


# ================= MQTT CONFIG ================= #
MQTT_BROKER = "mqttbroker.bc-pl.com"
MQTT_PORT = 1883
MQTT_USER = "mqttuser"
MQTT_PASSWORD = "Bfl@2025"

TOPIC_ALL = "pomon/+/rnd/#"

TOPIC_ALERT = "pomon/+/rnd/alert"
TOPIC_ABORT = "pomon/+/rnd/abort"


# ================= TELEGRAM ================= #
TELEGRAM_BOT_TOKEN = "8650685796:AAEWB2H-Jsr-34Oycq2EDi-EgbzGTKS0hkw"
TELEGRAM_GROUPCHAT_IDS = [-5186117690, 1836771564]

LAST_SENT = {}
LAST_VALUES = {}
INTERVAL = 2

# ================= TELEGRAM ================= #
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in TELEGRAM_GROUPCHAT_IDS:
        try:
            requests.post(url, data={
                "chat_id": chat_id,
                "text": message
            })
        except Exception as e:
            print("❌ Telegram Error:", e)


def send_telegram_image(image_buffer):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    for chat_id in TELEGRAM_GROUPCHAT_IDS:
        try:
            image_buffer.seek(0)
            requests.post(url, files={"photo": image_buffer}, data={"chat_id": chat_id})
        except Exception as e:
            print("❌ Telegram Error:", e)


# ================= MQTT CONNECT ================= #
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ MQTT Connected")
        client.subscribe(TOPIC_ALL)
    else:
        print(f"❌ MQTT Connection failed: {rc}")


# ================= MQTT MESSAGE ================= #
def on_message(client, userdata, msg):
    topic = msg.topic
    raw_payload = msg.payload.decode()

    print("\n========== MQTT ==========")
    print("📌", topic)
    print("📦", raw_payload)

    device_id = topic.split("/")[1]
    now = timezone.now()

    # ===== ALERT ===== #
    if topic.endswith("/alert"):
        send_telegram_alert(f"⚠ Alert {device_id}: {raw_payload}")
        return

    # ===== SENSOR DATA ===== #
    if topic.endswith("/status"):

        try:
            payload = json.loads(raw_payload)
        except Exception as e:
            print("❌ JSON Error:", e)
            return

        session = MonitoringSession.objects.filter(
            device__device_id=device_id,
            status__in=["PENDING", "PROCESSING"]
        ).order_by("start_time").first()

        if not session:
            return

        update_session_status(session)
        session.refresh_from_db()

        if session.status != "PROCESSING":
            return

        dev = payload.get(f"Dev{session.main}")
        if not dev:
            return

        # ================= SAFE SENSOR VALUES ================= #
        r = float(dev.get("R") or 0)
        y = float(dev.get("Y") or 0)
        b = float(dev.get("B") or 0)

        # ================= FIXED VOLTAGE (IMPORTANT) ================= #
        # 👉 prevents NULL DB crash
        vr = 230.0
        vy = 230.0
        vb = 230.0

        # ================= ENERGY CALC ================= #
        power = 230 * (r + y + b)
        wh = power * (5 / 3600)

        # ================= SAFE DB INSERT ================= #
        try:
            SensorData.objects.create(
                session=session,
                timestamp=now,

                # ⚠ REQUIRED FIELDS (FIXED)
                voltage_r=vr,
                voltage_y=vy,
                voltage_b=vb,

                current_r=r,
                current_y=y,
                current_b=b,
                wh=wh
            )
        except Exception as e:
            print("❌ DB Insert Error:", e)
            return

        print(f"⚡ Session {session.id}: {wh:.4f} Wh")

        # ================= TELEGRAM ================= #
        try:
            img = generate_live_data_card(
                device_id=device_id,
                session_id=session.id,
                r=r, y=y, b=b,
                wh=wh,
                timestamp=now.strftime("%H:%M:%S")
            )

            key = f"{device_id}_{session.id}"
            values = (round(r, 2), round(y, 2), round(b, 2), round(wh, 2))

            if LAST_VALUES.get(key) != values:
                send_telegram_image(img)
                LAST_VALUES[key] = values

        except Exception as e:
            print("❌ Telegram Error:", e)


# ================= WATCHER ================= #
def schedule_watcher():
    while True:
        close_old_connections()
        now = timezone.now()

        sessions = MonitoringSession.objects.filter(
            start_time__isnull=False,
            end_time__isnull=False
        )

        for session in sessions:
            try:
                session.refresh_from_db()

                update_session_status(session)
                session.refresh_from_db()

                # ===============================
                # PRE-START WINDOW
                # ===============================
                if (
                    session.status == "PENDING"
                    and not getattr(session, "mqtt_sent", False)
                    and session.start_time - timedelta(seconds=20) <= now < session.start_time
                ):
                    print(f"⏰ PRE-START → Session {session.id}")

                    # ===============================
                    # STRICT DURATION CALCULATION
                    # ===============================
                    duration = int(
                        (session.end_time - session.start_time).total_seconds()
                    )

                    # ❌ HARD STOP RULE (IMPORTANT)
                    if duration <= 60:
                        print(f"❌ SKIP Session {session.id} (duration={duration})")
                        continue

                    # ===============================
                    # DEVICE EXPECTED FORMAT FIX
                    # ===============================
                    payload = {
                        "start_time": session.start_time.strftime("%H:%M"),
                        "duration": duration,
                        "main": int(session.main)
                    }

                    topic = f"pomon/{session.device.device_id}/rnd/schedule"

                    print(f"📤 MQTT → {payload}")

                    publish.single(
                        topic,
                        json.dumps(payload, separators=(",", ":")),
                        hostname=MQTT_BROKER,
                        port=MQTT_PORT,
                        auth={
                            "username": MQTT_USER,
                            "password": MQTT_PASSWORD
                        }
                    )

                    session.mqtt_sent = True
                    session.save(update_fields=["mqtt_sent"])

                    print(f"🚀 SENT → Session {session.id}")

            except Exception as e:
                print(f"⚠️ watcher error session {session.id}: {e}")

        time.sleep(1)


# ================= START ================= #
def start():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    threading.Thread(target=schedule_watcher, daemon=True).start()

    print("🚀 System Started")
    client.loop_forever()


if __name__ == "__main__":
    start()