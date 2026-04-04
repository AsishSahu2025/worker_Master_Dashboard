import json
import paho.mqtt.publish as publish

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


# ================= STATUS HELPER ================= #
def update_session_status(session):
    now = timezone.now()
    if session.status in ["COMPLETED", "FAILED", "ABORTED"]:
        return
    if not session.start_time or not session.end_time:
        session.status = "PENDING"
    else:
        has_data = session.readings.exists() if hasattr(session, 'readings') else False
        if now < session.start_time:
            session.status = "PENDING"
        elif session.start_time <= now <= session.end_time:
            session.status = "PROCESSING"
        else:
            session.status = "COMPLETED" if has_data else "FAILED"
        session.duration = session.end_time - session.start_time
    session.save(update_fields=["status", "duration"])


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

            session = MonitoringSession.objects.create(
                device=device,
                cycle_number=next_cycle_number,
                start_time=None,
                end_time=None,
                status="PENDING"
            )
            created_cycles.append({
                "cycle_number": session.cycle_number,
                "start_time": session.start_time,
                "end_time": session.end_time
            })

        return Response({
            "success": True,
            "device_id": device.device_id,
            "cycles": created_cycles
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
        worker_id = request.data.get("worker_id")

        # ----------- VALIDATION ----------- #
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

        worker = None
        if worker_id:
            try:
                worker = Worker_details.objects.get(mobno=worker_id)
            except Worker_details.DoesNotExist:
                raise ValidationError({"worker_id": "Invalid worker"})

        main_default = 1 if device.device_id == "BFL_PomonA001" else 2
        now = timezone.now()
        created_sessions = []

        with transaction.atomic():
            for i, cycle_data in enumerate(cycles):
                # ----------- PARSE DATETIME ----------- #
                try:
                    start_time = parser.parse(cycle_data['start_time'])
                    if timezone.is_naive(start_time):
                        start_time = timezone.make_aware(start_time)

                    end_time = parser.parse(cycle_data['end_time'])
                    if timezone.is_naive(end_time):
                        end_time = timezone.make_aware(end_time)
                except Exception:
                    raise ValidationError({"error": f"Cycle {i+1}: Invalid datetime format"})

                main = cycle_data.get("main", main_default)

                # ----------- TIME VALIDATION ----------- #
                if start_time < now + timedelta(seconds=60):
                    raise ValidationError({"error": f"Cycle {i+1}: start_time must be at least 60s from now"})
                if end_time <= start_time:
                    raise ValidationError({"error": f"Cycle {i+1}: end_time must be after start_time"})
                if (end_time - start_time).total_seconds() < 60:
                    raise ValidationError({"error": f"Cycle {i+1}: duration must be >= 60s"})

                # ----------- OVERLAP CHECK ----------- #
                overlap = MonitoringSession.objects.filter(
                    device=device,
                    start_time__lt=end_time,
                    end_time__gt=start_time
                )
                if overlap.exists():
                    raise ValidationError({"error": f"Cycle {i+1}: overlaps with existing session"})

                # ----------- CREATE SESSION ----------- #
                session = MonitoringSession.objects.create(
                    device=device,
                    worker=worker,
                    start_time=start_time,
                    end_time=end_time,
                    main=main,
                    status="PENDING",
                    cycle_number=(MonitoringSession.objects.filter(device=device).count() + 1)
                )

                update_session_status(session)
                created_sessions.append(session)

                # ----------- MQTT PUBLISH ----------- #
                payload = {
                    "cycle": session.cycle_number,
                    "start_time": start_time.strftime("%H:%M"),
                    "duration": int((end_time - start_time).total_seconds()),
                    "main": main
                }
                topic = f"pomon/{device.device_id}/rnd/schedule"
                try:
                    publish.single(
                        topic,
                        json.dumps(payload, separators=(',', ':')),
                        hostname=MQTT_BROKER,
                        port=MQTT_PORT,
                        auth={"username": MQTT_USER, "password": MQTT_PASSWORD}
                    )
                except Exception as e:
                    print("MQTT Error:", e)

        return Response({
            "success": True,
            "message": f"{len(created_sessions)} cycles scheduled successfully",
            "device": device.device_id,
            "cycles": [
                {
                    "cycle_number": s.cycle_number,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "main": s.main
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

        session.abort()

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

        return Response({"success": True})


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