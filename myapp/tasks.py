from celery import shared_task
from django.utils import timezone
from .models import Task
from power_monitoring.models import *
from checktray.models import *
from .utils import trigger_device
from datetime import timedelta
from datetime import datetime

@shared_task
def start_scheduled_cycles():
    now = timezone.now()
    today = now.date()
    trigger_time = (now + timedelta(minutes=1)).time()

    # SAME QUERY + DISTINCT batch_id
    devices = Task.objects.filter(
        schedule_date=today,
        status="scheduled",
        cycles=1,
        from_time__lte=trigger_time
    ).distinct("batch_id")   # ONLY CHANGE

    for device in devices:
        # Prevent duplicate triggering (UNCHANGED)
        if Task.objects.filter(device=device.device, status="processing").exists():
            continue

        # Prevent re-trigger (UNCHANGED)
        if device.status != "scheduled":
            continue

        trigger_device(device.device.device_id, device.id)


@shared_task
def daily_task_cleanup():
    today = datetime.now().date()

    # Delete ALL past tasks (no status condition)
    Task.objects.filter(
        schedule_date__lt=today
    ).delete()

    MonitoringSession.objects.exclude(
        status="PENDING"
        ).delete()
    
    ChecktrayTask.objects.exclude(
        status="Pending"
    ).delete()

    print("✅ All old tasks deleted")