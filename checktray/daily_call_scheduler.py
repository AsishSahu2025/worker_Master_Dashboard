"""
Background thread that runs forever and places
a daily call to the manager at the configured time.
"""
from __future__ import annotations

import time
import threading
from datetime import datetime
from django.conf import settings


def daily_call_loop():
    """
    Runs every 60 seconds.
    When current time matches DAILY_SCHEDULE_CALL_HOUR:DAILY_SCHEDULE_CALL_MINUTE,
    places a call — but only ONCE per day using a date flag.
    """
    from checktray.daily_call import call_manager_daily_reminder

    call_hour   = getattr(settings, "DAILY_SCHEDULE_CALL_HOUR",   6)
    call_minute = getattr(settings, "DAILY_SCHEDULE_CALL_MINUTE", 30)

    last_called_date = None

    print(f"[Daily Call] Scheduler started — will call at {call_hour:02d}:{call_minute:02d} every day.")

    while True:
        try:
            now   = datetime.now()   # ← simple local time, no timezone issues
            today = now.date()

            is_call_time = (
                now.hour   == call_hour and
                now.minute == call_minute
            )

            if is_call_time and last_called_date != today:
                last_called_date = today
                print(f"[Daily Call] Triggering morning reminder call at {now.strftime('%H:%M')}...")
                call_manager_daily_reminder()

        except Exception as e:
            print(f"[Daily Call ERROR] {e}")

        time.sleep(60)


def start_daily_call_thread():
    thread = threading.Thread(target=daily_call_loop, daemon=True)
    thread.start()
    print("[Daily Call] Background thread started.")