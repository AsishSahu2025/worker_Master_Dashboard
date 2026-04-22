from celery import shared_task
from django.utils import timezone
from .models import Task
from .utils import trigger_device
from datetime import timedelta

@shared_task
def start_scheduled_cycles():
    now = timezone.now()
    today = now.date()
    trigger_time = (now + timedelta(minutes=1)).time()

    # 🔥 SAME QUERY + DISTINCT batch_id
    devices = Task.objects.filter(
        schedule_date=today,
        status="scheduled",
        cycles=1,
        from_time__lte=trigger_time
    ).distinct("batch_id")   # ✅ ONLY CHANGE

    for device in devices:
        # Prevent duplicate triggering (UNCHANGED)
        if Task.objects.filter(device=device.device, status="processing").exists():
            continue

        # Prevent re-trigger (UNCHANGED)
        if device.status != "scheduled":
            continue

        trigger_device(device.device.device_id, device.id)
