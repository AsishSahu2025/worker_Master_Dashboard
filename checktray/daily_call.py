"""
Twilio calls:
1. Daily manager reminder — 6:30 AM (Checktray)
2. Worker call — 10 mins before Checktray task
3. Daily manager reminder — 6:30 AM (Autofeeder)
4. Worker call — 10 mins before Autofeeder task
"""
from __future__ import annotations

import logging
from django.conf import settings

logging.basicConfig(
    filename="daily_call_log.txt",
    level=logging.INFO,
    format="%(asctime)s — %(message)s"
)


def call_manager_daily_reminder() -> str | None:
    """
    Places a voice call to the manager at 6:30 AM daily.
    """
    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
    auth_token  = getattr(settings, "TWILIO_AUTH_TOKEN",  None)
    from_number = getattr(settings, "TWILIO_FROM_NUMBER", None)
    to_number   = getattr(settings, "MANAGER_PHONE",      None)

    if not all([account_sid, auth_token, from_number, to_number]):
        logging.warning("Missing Twilio settings — manager call not placed.")
        print("[Twilio Daily] Missing Twilio settings — call not placed.")
        return None

    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice">
    Hello. This is an automated morning reminder from Check Tray.
    Please create today's task schedule
    and enter the feed quantity for the auto feeder
    before 7 A M.
    Thank you. Have a good day.
  </Say>
  <Pause length="1"/>
  <Say voice="alice">
    This message will repeat once.
    Please create today's task schedule
    and enter the feed quantity for the auto feeder.
    Thank you.
  </Say>
</Response>"""

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        call = client.calls.create(
            twiml=twiml,
            to=to_number,
            from_=from_number,
        )
        logging.info(f"✅ Manager morning call placed to {to_number} — SID={call.sid}")
        print(f"[Twilio Daily] Morning reminder call placed. SID={call.sid}")
        return call.sid

    except Exception as ex:
        logging.error(f"❌ Manager call failed — {repr(ex)}")
        print(f"[Twilio Daily] Exception: {repr(ex)}")
        return None


def call_worker_for_task(task) -> str | None:
    """
    Places a voice call to the assigned worker 10 mins before task start.
    Worker phone number taken from task.worker_name.mobno
    """
    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
    auth_token  = getattr(settings, "TWILIO_AUTH_TOKEN",  None)
    from_number = getattr(settings, "TWILIO_FROM_NUMBER", None)

    if not all([account_sid, auth_token, from_number]):
        print("[Twilio Worker] Missing Twilio settings — call not placed.")
        return None

    # ── Get worker details ──
    worker = task.worker_name
    if not worker:
        print(f"[Twilio Worker] Task {task.id} has no assigned worker — skipping.")
        return None

    worker_name   = worker.name or "Worker"
    worker_mobile = str(worker.mobno).strip()

    if not worker_mobile:
        print(f"[Twilio Worker] Worker {worker_name} has no mobile number — skipping.")
        return None

    # ── Get device and task details ──
    dev       = task.device_id
    device_pk = dev.device_id if dev else "unknown"
    start_str = (
        task.start_time.strftime("%I:%M %p on %d %B %Y")
        if task.start_time else "scheduled time"
    )

    # mobno stored as BigInteger e.g. 9876543210
    # Twilio needs +91XXXXXXXXXX format
    country_code = getattr(settings, "WORKER_PHONE_COUNTRY_CODE", "+91")
    to_number    = f"{country_code}{worker_mobile}"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice">
    Hello {worker_name}.
    This is an automated reminder from Check Tray.
    You have a task assigned on Device {device_pk},
    scheduled to start at {start_str}.
    Please be ready at the device before the start time.
    Thank you.
  </Say>
  <Pause length="1"/>
  <Say voice="alice">
    Reminder. Your task on Device {device_pk}
    starts at {start_str}.
    Please be ready. Thank you.
  </Say>
</Response>"""

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        call = client.calls.create(
            twiml=twiml,
            to=to_number,
            from_=from_number,
        )
        logging.info(f"✅ Worker call placed to {worker_name} ({to_number}) task {task.id} — SID={call.sid}")
        print(f"[Twilio Worker] Call placed to {worker_name} ({to_number}) SID={call.sid}")
        return call.sid

    except Exception as ex:
        logging.error(f"❌ Worker call failed for task {task.id} — {repr(ex)}")
        print(f"[Twilio Worker] Exception: {repr(ex)}")
        return None
    




# ── AUTOFEEDER PART   ────────────────────────────────────────────────────────────────





def call_manager_autofeeder_reminder() -> str | None:
    """Daily 6:30 AM call to manager for Autofeeder schedule."""
    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
    auth_token  = getattr(settings, "TWILIO_AUTH_TOKEN",  None)
    from_number = getattr(settings, "TWILIO_FROM_NUMBER", None)
    to_number   = getattr(settings, "MANAGER_PHONE",      None)

    if not all([account_sid, auth_token, from_number, to_number]):
        logging.warning("Missing Twilio settings — autofeeder manager call not placed.")
        print("[Twilio Autofeeder] Missing Twilio settings — call not placed.")
        return None

    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice">
    Hello. This is an automated morning reminder from Auto Feeder.
    Please create today's auto feeder task schedule
    and assign workers for today's feeding tasks.
    Thank you. Have a good day.
  </Say>
  <Pause length="1"/>
  <Say voice="alice">
    This message will repeat once.
    Please create today's auto feeder task schedule
    and assign workers for today's feeding tasks.
    Thank you.
  </Say>
</Response>"""

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        call = client.calls.create(
            twiml=twiml,
            to=to_number,
            from_=from_number,
        )
        logging.info(f"✅ Autofeeder manager call placed to {to_number} — SID={call.sid}")
        print(f"[Twilio Autofeeder] Morning call placed. SID={call.sid}")
        return call.sid
    except Exception as ex:
        logging.error(f"❌ Autofeeder manager call failed — {repr(ex)}")
        print(f"[Twilio Autofeeder] Exception: {repr(ex)}")
        return None


def call_worker_for_autofeeder_task(task) -> str | None:
    """
    Call assigned worker 10 mins before Autofeeder task start.
    Uses task.from_time + task.schedule_date for start datetime.
    """
    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
    auth_token  = getattr(settings, "TWILIO_AUTH_TOKEN",  None)
    from_number = getattr(settings, "TWILIO_FROM_NUMBER", None)

    if not all([account_sid, auth_token, from_number]):
        print("[Twilio Autofeeder Worker] Missing Twilio settings — call not placed.")
        return None

    worker = task.worker_name
    if not worker:
        print(f"[Twilio Autofeeder Worker] Task {task.id} has no assigned worker — skipping.")
        return None

    worker_name   = worker.name or "Worker"
    worker_mobile = str(worker.mobno).strip()
    device_pk     = task.device.device_id if task.device else "unknown"

    # ── Combine schedule_date + from_time for readable start string ──
    if task.schedule_date and task.from_time:
        start_str = task.from_time.strftime("%I:%M %p") + " on " + task.schedule_date.strftime("%d %B %Y")
    elif task.from_time:
        start_str = task.from_time.strftime("%I:%M %p")
    else:
        start_str = "scheduled time"

    country_code = getattr(settings, "WORKER_PHONE_COUNTRY_CODE", "+91")
    to_number    = f"{country_code}{worker_mobile}"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice">
    Hello {worker_name}.
    This is an automated reminder from Auto Feeder.
    You have an auto feeder task assigned on Device {device_pk},
    scheduled to start at {start_str}.
    Please be ready at the device before the start time.
    Thank you.
  </Say>
  <Pause length="1"/>
  <Say voice="alice">
    Reminder. Your auto feeder task on Device {device_pk}
    starts at {start_str}.
    Please be ready. Thank you.
  </Say>
</Response>"""

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        call = client.calls.create(
            twiml=twiml,
            to=to_number,
            from_=from_number,
        )
        logging.info(f"✅ Autofeeder worker call to {worker_name} ({to_number}) task {task.id} — SID={call.sid}")
        print(f"[Twilio Autofeeder Worker] Call placed to {worker_name} ({to_number}) SID={call.sid}")
        return call.sid
    except Exception as ex:
        logging.error(f"❌ Autofeeder worker call failed task {task.id} — {repr(ex)}")
        print(f"[Twilio Autofeeder Worker] Exception: {repr(ex)}")
        return None