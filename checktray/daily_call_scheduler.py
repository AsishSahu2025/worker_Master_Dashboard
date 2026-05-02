"""
Background threads:
1. Daily Checktray manager call   — 6:30 AM
2. Checktray worker call          — 10 mins before task
3. Daily Autofeeder manager call  — 6:30 AM
4. Autofeeder worker call         — 10 mins before each cycle
"""
from __future__ import annotations

import time
import threading
from datetime import datetime
from django.utils import timezone
from django.db import close_old_connections
from django.conf import settings

WORKER_CALL_BEFORE_MINUTES = 10


def daily_call_loop():
    """Daily 6:30 AM call to manager for Checktray."""
    from checktray.daily_call import call_manager_daily_reminder

    call_hour   = getattr(settings, "DAILY_SCHEDULE_CALL_HOUR",   6)
    call_minute = getattr(settings, "DAILY_SCHEDULE_CALL_MINUTE", 30)
    last_called_date = None

    print(f"[Daily Call] Checktray manager call scheduled at {call_hour:02d}:{call_minute:02d} daily.")

    while True:
        try:
            now   = datetime.now()
            today = now.date()

            if now.hour == call_hour and now.minute == call_minute and last_called_date != today:
                last_called_date = today
                print(f"[Daily Call] Triggering Checktray manager call at {now.strftime('%H:%M')}...")
                call_manager_daily_reminder()

        except Exception as e:
            print(f"[Daily Call ERROR] {e}")

        time.sleep(60)


def autofeeder_daily_call_loop():
    """Daily 6:30 AM call to manager for Autofeeder."""
    from checktray.daily_call import call_manager_autofeeder_reminder

    call_hour   = getattr(settings, "DAILY_SCHEDULE_CALL_HOUR",   6)
    call_minute = getattr(settings, "DAILY_SCHEDULE_CALL_MINUTE", 30)
    last_called_date = None

    print(f"[Autofeeder Daily Call] Manager call scheduled at {call_hour:02d}:{call_minute:02d} daily.")

    while True:
        try:
            now   = datetime.now()
            today = now.date()

            if now.hour == call_hour and now.minute == call_minute and last_called_date != today:
                last_called_date = today
                print(f"[Autofeeder Daily Call] Triggering manager call at {now.strftime('%H:%M')}...")
                call_manager_autofeeder_reminder()

        except Exception as e:
            print(f"[Autofeeder Daily Call ERROR] {e}")

        time.sleep(60)


def worker_call_loop():
    """Checktray worker call — 10 mins before task start."""
    from checktray.daily_call import call_worker_for_task
    from checktray.models import ChecktrayTask

    print(f"[Worker Call] Checktray worker call {WORKER_CALL_BEFORE_MINUTES} mins before task.")

    while True:
        close_old_connections()
        try:
            now               = timezone.now()
            call_window_start = now
            call_window_end   = now + timezone.timedelta(minutes=WORKER_CALL_BEFORE_MINUTES)

            upcoming = (
                ChecktrayTask.objects
                .filter(
                    status="Pending",
                    start_time__gte=call_window_start,
                    start_time__lte=call_window_end,
                    worker_call_notified=False,
                )
                .select_related("device_id", "worker_name")
            )

            for task in upcoming:
                updated = ChecktrayTask.objects.filter(
                    id=task.id,
                    worker_call_notified=False
                ).update(worker_call_notified=True)

                if updated:
                    print(f"[Worker Call] Calling worker for Checktray task {task.id}")
                    call_worker_for_task(task)

        except Exception as e:
            print(f"[Worker Call ERROR] {e}")

        time.sleep(60)


def autofeeder_worker_call_loop():
    """
    Autofeeder worker call — 10 mins before each cycle's from_time.
    Each cycle = separate Task record with own from_time + worker_name.
    """
    from checktray.daily_call import call_worker_for_autofeeder_task
    from myapp.models import Task

    print(f"[Autofeeder Worker Call] Worker call {WORKER_CALL_BEFORE_MINUTES} mins before autofeeder task.")

    while True:
        close_old_connections()
        try:
            now   = datetime.now()
            today = now.date()

            todays_tasks = (
                Task.objects
                .filter(
                    schedule_date=today,
                    status__in=["scheduled", "processing"],
                    worker_name__isnull=False,
                    from_time__isnull=False,
                    worker_call_notified=False,
                )
                .select_related("device", "worker_name")
            )

            for task in todays_tasks:
                # Combine schedule_date + from_time → full datetime
                task_start_dt = datetime.combine(today, task.from_time)
                diff_mins     = (task_start_dt - now).total_seconds() / 60

                print(f"[Autofeeder Worker Call] Task {task.id} "
                      f"cycle={task.cycles} "
                      f"worker={task.worker_name.name} "
                      f"from_time={task.from_time} "
                      f"diff_mins={round(diff_mins, 1)}")

                # ── Fire only within 0 to 10 min window ──
                if 0 <= diff_mins <= WORKER_CALL_BEFORE_MINUTES:
                    updated = Task.objects.filter(
                        id=task.id,
                        worker_call_notified=False
                    ).update(worker_call_notified=True)

                    if updated:
                        print(f"[Autofeeder Worker Call] ✅ Calling {task.worker_name.name} "
                              f"for cycle {task.cycles} task {task.id}")
                        call_worker_for_autofeeder_task(task)

        except Exception as e:
            print(f"[Autofeeder Worker Call ERROR] {e}")

        time.sleep(30)


def start_daily_call_thread():
    """Start all 4 background call threads."""

    threading.Thread(target=daily_call_loop,          daemon=True).start()
    print("[Daily Call] Checktray manager thread started.")

    threading.Thread(target=autofeeder_daily_call_loop, daemon=True).start()
    print("[Autofeeder Daily Call] Manager thread started.")

    threading.Thread(target=worker_call_loop,          daemon=True).start()
    print("[Worker Call] Checktray worker thread started.")

    threading.Thread(target=autofeeder_worker_call_loop, daemon=True).start()
    print("[Autofeeder Worker Call] Worker thread started.")