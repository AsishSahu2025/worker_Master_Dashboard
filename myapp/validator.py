from datetime import datetime

from celery import shared_task
from datetime import datetime

@shared_task(bind=True)
def check_interval(self, task_id):
    from .models import Task

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return

    if not task.to_time:
        return

    now = datetime.now()

    end_dt = datetime.combine(now.date(), task.to_time)

    sleep_seconds = (end_dt - now).total_seconds()

    # 🔥 KEY CHANGE (no sleep)
    if sleep_seconds > 0:
        # re-schedule itself
        self.apply_async(
            args=[task_id],
            countdown=int(sleep_seconds) + 5  # buffer included
        )
        return

    # ---------- FINAL EXECUTION ----------
    try:
        task.refresh_from_db()
    except Task.DoesNotExist:
        print("Task deleted before completion check")
        return

    if task.status == "processing":
        task.status = "unknown State"
        task.is_published = True
        task.save()
    else:
        print("Already handled by MQTT")