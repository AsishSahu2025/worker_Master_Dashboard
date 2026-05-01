import json
import paho.mqtt.publish as publish

from power_monitoring.services.session_service import update_session_status
from .utils.telegram_cards import generate_cycle_card, generate_schedule_card, generate_abort_card
import requests
import io
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

from requests import request
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from dateutil import parser

from .models import SensorData, MonitoringSession
from .serializers import SensorDataSerializer, MonitoringSessionSerializer
from myapp.models import Device, Worker_details
# ---------------- MQTT CONFIG ---------------- #
MQTT_BROKER = "mqttbroker.bc-pl.com"
MQTT_PORT = 1883
MQTT_USER = "mqttuser"
MQTT_PASSWORD = "Bfl@2025"

TELEGRAM_BOT_TOKEN = "8650685796:AAEWB2H-Jsr-34Oycq2EDi-EgbzGTKS0hkw"
TELEGRAM_GROUPCHAT_IDS = [-5186117690, 1836771564]

def send_telegram_image(image_buffer, caption=""):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

    for chat_id in TELEGRAM_GROUPCHAT_IDS:
        try:
            image_buffer.seek(0)

            files = {"photo": image_buffer}
            data = {
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "HTML"
            }

            res = requests.post(url, files=files, data=data)
            print("📸 Telegram:", res.text)

        except Exception as e:
            print("❌ Telegram Error:", e)

# ================= SENSOR DATA ================= #
class SensorDataViewSet(ModelViewSet):
    queryset = SensorData.objects.all().order_by("-timestamp")
    serializer_class = SensorDataSerializer


# ================= GENERATE CYCLES ================= #
class GenerateCyclesView(APIView):
    def post(self, request):
        device_id = request.data.get("device_id")
        cycle_count = request.data.get("cycle_count")

        if not device_id:
            return Response({"error": "device_id required"}, status=400)
        if not cycle_count:
            return Response({"error": "cycle_count required"}, status=400)

        try:
            cycle_count = int(cycle_count)
        except:
            return Response({"error": "cycle_count must be integer"}, status=400)

        if cycle_count <= 0:
            return Response({"error": "cycle_count must be > 0"}, status=400)
        if cycle_count > 5:
            return Response({"error": "Max 5 cycles allowed"}, status=400)

        try:
            device = Device.objects.get(device_id=device_id)
        except Device.DoesNotExist:
            return Response({"error": "Invalid device"}, status=400)

        existing_empty = MonitoringSession.objects.filter(
            device=device,
            start_time__isnull=True,
            end_time__isnull=True
        ).count()

        if existing_empty > 0:
            return Response({
                "error": f"Cannot create new cycles. {existing_empty} unscheduled cycle(s) exist."
            }, status=400)

        active_count = MonitoringSession.objects.filter(
            device=device,
            status__in=["PENDING", "PROCESSING"]
        ).count()

        available_slots = max(0, 5 - active_count)
        cycles_to_create = min(cycle_count, available_slots)

        if cycles_to_create == 0:
            return Response({
                "error": "Device already has maximum cycles scheduled"
            }, status=400)

        created_cycles = []

        for i in range(cycles_to_create):
            last_cycle = MonitoringSession.objects.filter(device=device).order_by("-cycle_number").first()
            next_cycle_number = last_cycle.cycle_number + 1 if last_cycle else 1

            main_value = 1 if device.device_id == "BFL_PomonA001" else 2

            session = MonitoringSession.objects.create(
                device=device,
                cycle_number=next_cycle_number,
                start_time=None,
                end_time=None,
                status="PENDING",
                main=main_value
            )

            created_cycles.append({
                "cycle_number": session.cycle_number
            })

        # ================= TELEGRAM IMAGE ALERT ================= #
        try:
            now = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

            image = generate_cycle_card(
                device_id=device.device_id,
                cycles=created_cycles,
                timestamp=now
            )

            send_telegram_image(image)

        except Exception as e:
            print("⚠️ Telegram Image Failed:", e)

        # -------- RESPONSE -------- #
        return Response({
            "success": True,
            "device_id": device.device_id,
            "cycles": created_cycles
        })
    
# ================= CLEAR ALL CYCLES ================= #

class ClearCyclesView(APIView):
    def delete(self, request):
        device_id = request.data.get("device_id")

        if device_id:
            deleted, _ = MonitoringSession.objects.filter(
                device__device_id=device_id
            ).delete()
            return Response({
                "success": True,
                "message": f"{deleted} cycles deleted for {device_id}"
            })

        deleted, _ = MonitoringSession.objects.all().delete()

        return Response({
            "success": True,
            "message": f"{deleted} cycles deleted (ALL)"
        })
    
# ================= EMPTY ROWS WITH DETAILS ================= #
class EmptySessionsDetailView(APIView):
    def get(self, request):
        device_id = request.query_params.get("device_id")
        if not device_id:
            return Response({"error": "device_id required"}, status=400)

        try:
            device = Device.objects.get(device_id=device_id)
        except Device.DoesNotExist:
            return Response({"error": "Invalid device"}, status=400)

        empty_sessions = MonitoringSession.objects.filter(
            device=device,
            start_time__isnull=True,
            end_time__isnull=True
        ).order_by("cycle_number")

        data = []
        for s in empty_sessions:
            data.append({
                "session_id": s.id,
                "cycle_number": s.cycle_number,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "duration": s.duration.total_seconds() if s.duration else None,
                "energy": s.energy if hasattr(s, "energy") else None,
                "status": s.status,
                "worker": {
                    "id": s.worker.id,
                    "name": getattr(s.worker, "name", None),
                    "mobno": getattr(s.worker, "mobno", None)
                } if s.worker else None,
                "main": s.main
            })

        return Response({
            "device_id": device.device_id,
            "empty_slots_count": len(data),
            "empty_sessions": data
        })

# ================= MONITORING SESSION CREATE/UPDATE ================= #
class MonitoringSessionViewSet(ModelViewSet):
    queryset = MonitoringSession.objects.all().order_by("-start_time")
    serializer_class = MonitoringSessionSerializer

    def create(self, request, *args, **kwargs):
        device_id = request.data.get("device_id")
        cycles = request.data.get("cycles")

        # ===== BASIC VALIDATION ===== #
        if not device_id:
            raise ValidationError({"device_id": "Device ID required"})

        if not cycles or not isinstance(cycles, list):
            raise ValidationError({"cycles": "Cycles must be a list"})

        if len(cycles) > 5:
            raise ValidationError({"cycles": "Max 5 cycles allowed"})

        try:
            device = Device.objects.get(device_id=device_id)
        except Device.DoesNotExist:
            raise ValidationError({"device_id": "Invalid device"})

        main_default = 1 if device.device_id == "BFL_PomonA001" else 2
        created_sessions = []

        now = timezone.now()
        next_start_time = now + timedelta(seconds=60)

        MIN_GAP_SECONDS = 120  

        last_start_time = None  

        with transaction.atomic():
            for i, cycle_data in enumerate(cycles):

                # ===== WORKER ===== #
                worker_id = cycle_data.get("worker_id")
                if not worker_id:
                    raise ValidationError({"error": f"Cycle {i+1}: worker_id required"})

                try:
                    worker = Worker_details.objects.get(mobno=worker_id)
                except Worker_details.DoesNotExist:
                    raise ValidationError({"error": f"Cycle {i+1}: invalid worker_id"})

                main = cycle_data.get("main", main_default)

                # ===== AUTO MODE ===== #
                if "duration" in cycle_data:
                    try:
                        duration = int(cycle_data["duration"])
                    except:
                        raise ValidationError({"error": f"Cycle {i+1}: invalid duration"})

                    if duration <= 60:
                        raise ValidationError({
                            "error": f"Cycle {i+1}: duration must be > 60 seconds"
                        })

                    start_time = next_start_time
                    end_time = start_time + timedelta(seconds=duration)

                    next_start_time = end_time + timedelta(seconds=MIN_GAP_SECONDS)

                # ===== MANUAL MODE ===== #
                else:
                    try:
                        start_time = parser.parse(cycle_data["start_time"])
                        end_time = parser.parse(cycle_data["end_time"])
                    except:
                        raise ValidationError({"error": f"Cycle {i+1}: invalid datetime"})

                # ===== BASIC VALIDATIONS ===== #
                if end_time <= start_time:
                    raise ValidationError({"error": f"Cycle {i+1}: end must be after start"})

                duration_check = (end_time - start_time).total_seconds()

                if duration_check <= 60:
                    raise ValidationError({
                        "error": f"Cycle {i+1}: duration must be > 60 seconds"
                    })

                # =========================================================
                # RULE 1: FIRST CYCLE MUST BE >= NOW + 120 SEC
                # =========================================================
                if i == 0:
                    min_first_start = now + timedelta(seconds=100)
                    if start_time < min_first_start:
                        raise ValidationError({
                            "error": "First cycle start_time must be at least 100 seconds greater than current time"
                        })

                # =========================================================
                # RULE 2: GAP BETWEEN CYCLES >= 120 SEC
                # =========================================================
                if last_start_time:
                    gap = (start_time - last_start_time).total_seconds()
                    if gap < MIN_GAP_SECONDS:
                        raise ValidationError({
                            "error": f"Cycle {i+1}: minimum gap between cycles must be 120 seconds"
                        })

                last_start_time = start_time

                # ===== GET EMPTY SLOT ===== #
                session = MonitoringSession.objects.filter(
                    device=device,
                    start_time__isnull=True,
                    end_time__isnull=True
                ).order_by("cycle_number").first()

                if not session:
                    raise ValidationError({"error": "No empty cycle available"})

                # ===== SAVE ===== #
                session.worker = worker
                session.start_time = start_time
                session.end_time = end_time
                session.main = main
                session.status = "PENDING"
                session.mqtt_sent = False
                session.save()

                created_sessions.append(session)

        return Response({
            "success": True,
            "message": f"{len(created_sessions)} cycles scheduled",
            "device": device.device_id,
            "cycles": [
                {
                    "cycle": s.cycle_number,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "status": s.status
                } for s in created_sessions
            ]
        })

# ================= ABORT ================= #
class AbortSessionView(APIView):
    def post(self, request):
        session_id = request.data.get("session_id")

        if not session_id:
            return Response({"error": "session_id required"}, status=400)

        try:
            session = MonitoringSession.objects.get(id=session_id)
        except MonitoringSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)

        if session.status in ["COMPLETED", "FAILED", "ABORTED"]:
            return Response({"error": "Cannot abort"}, status=400)

        session.status = "ABORTED"
        session.end_time = timezone.now()
        session.duration = session.end_time - session.start_time if session.start_time else None
        session.save()

        topic = f"pomon/{session.device.device_id}/rnd/abort"
        try:
            publish.single(
                topic,
                json.dumps({"command": "ABORT"}),
                hostname=MQTT_BROKER,
                port=MQTT_PORT,
                auth={"username": MQTT_USER, "password": MQTT_PASSWORD}
            )
        except Exception as e:
            print("MQTT Abort Error:", e)

        # ================= TELEGRAM IMAGE ================= #
        try:
            current_time = timezone.now().strftime("%H:%M:%S")

            img = generate_abort_card(
                device_id=session.device.device_id,
                cycle_no=session.cycle_number,
                timestamp=current_time
            )

            send_telegram_image(img)

        except Exception as e:
            print("❌ Telegram Abort Image Error:", e)

        return Response({
            "success": True,
            "message": f"Session {session.id} aborted successfully"
        })


# ================= ENERGY SUMMARY ================= #
class EnergySummaryView(APIView):
    def get(self, request):
        today = timezone.localtime().date()
        total = SensorData.objects.filter(timestamp__date=today).aggregate(total=Sum("wh"))["total"] or 0
        return Response({"daily_energy_kwh": round(total / 1000, 4)})


# ================= ACTIVE SESSIONS ================= #
class ActiveSessionView(APIView):
    def get(self, request):
        sessions = MonitoringSession.objects.filter(status__in=["PENDING", "PROCESSING"])
        data = []
        for s in sessions:
            update_session_status(s)
            data.append({
                "session_id": s.id,
                "device": s.device.device_id,
                "cycle": s.cycle_number,
                "status": s.status
            })
        return Response(data)