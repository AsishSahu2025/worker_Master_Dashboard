from django.utils import timezone
from myapp.models import Task
import time
from datetime import datetime

def check_interval(task_id):
    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        print("Task not found")
        return False

    from_time = task.from_time.strftime("%H:%M") if task.from_time else None
    end_time = task.to_time.strftime("%H:%M") if task.to_time else None
    current_time = timezone.localtime(timezone.now()).time().strftime("%H:%M")
    fmt = "%H:%M"

    sleeptime = (
        datetime.strptime(end_time, fmt)
        - datetime.strptime(current_time, fmt)
    ).total_seconds()-19
    print(sleeptime)
    count=1

    while True:
        
        current_time = timezone.localtime(timezone.now()).time().strftime("%H:%M")
        task = Task.objects.get(id=task_id)
        print("Task:", task)
        print("End Time:", end_time)
        print("Current Time:", current_time)
        status=task.status
        print("status:",status)
        print("TaskID:",task.id)
        if count == 1:
            time.sleep(int(sleeptime))
            count+= 1
        if current_time == end_time and status == "processing":
            setattr(task,"status","completed")
            break
        else:
            break
    task.save()
    return task

        

        
