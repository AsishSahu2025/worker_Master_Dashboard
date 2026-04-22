from django.utils import timezone
from myapp.models import Task
import time
from datetime import datetime

# def check_interval(task_id):
#     try:
#         task = Task.objects.get(id=task_id)
#     except Task.DoesNotExist:
#         print("Task not found")
#         return False

#     from_time = task.from_time.strftime("%H:%M") if task.from_time else None
#     end_time = task.to_time.strftime("%H:%M") if task.to_time else None
#     current_time = timezone.localtime(timezone.now()).time().strftime("%H:%M")
#     fmt = "%H:%M"

#     sleeptime = (
#         datetime.strptime(end_time, fmt)
#         - datetime.strptime(current_time, fmt)
#     ).total_seconds()-19
#     print(sleeptime)
#     count=1

#     while True:
#         print("Task:", task)
#         print("End Time:", end_time)
#         print("Current Time:", current_time)
#         if count == 1:
#             time.sleep(int(sleeptime))
#             count+= 1
#         current_time = timezone.localtime(timezone.now()).time().strftime("%H:%M")
#         task = Task.objects.get(id=task_id)
#         status=task.status
#         print("status:",status)
#         print("TaskID:",task.id)
       
#         if current_time == end_time and status == "processing":
#             setattr(task,"status","completed")
#             break
#         elif status == "abort":
#             break
#     task.save()
#     return task

        

        

# from datetime import datetime, timedelta
# import time

# def check_interval(task_id):
#     try:
#         task = Task.objects.get(id=task_id)
#     except Task.DoesNotExist:
#         return

#     if not task.to_time:
#         return

#     # use local naive time
#     now = datetime.now()

#     # combine with today's date (same logic as your system)
#     end_dt = datetime.combine(now.date(), task.to_time)

#     sleep_seconds = (end_dt - now).total_seconds()

#     if sleep_seconds > 0:
#         time.sleep(sleep_seconds)

#     # buffer
#     time.sleep(5)

#     try:
#         task.refresh_from_db()
#     except Task.DoesNotExist:
#         print("Task deleted before completion check")
#         return

#     if task.status == "processing":
#         task.status = "Unknown State"
#         task.is_published = False
#         task.save()
#     else:
#         print("Already handled by MQTT")

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
        task.status = "Unknown State"
        task.is_published = False
        task.save()
    else:
        print("Already handled by MQTT")