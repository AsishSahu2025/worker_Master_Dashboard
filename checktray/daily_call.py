"""
Daily morning call to manager at 6:30 AM
reminding them to create today's task schedule.
"""
from __future__ import annotations

from django.conf import settings
from twilio.rest import Client


def call_manager_daily_reminder() -> str | None:
    """
    Places a voice call to the manager reminding them
    to create today's schedule before 7:00 AM.
    """
    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
    auth_token  = getattr(settings, "TWILIO_AUTH_TOKEN",  None)
    from_number = getattr(settings, "TWILIO_FROM_NUMBER", None)
    to_number   = getattr(settings, "MANAGER_PHONE",      None)

    if not all([account_sid, auth_token, from_number, to_number]):
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
        client = Client(account_sid, auth_token)
        call = client.calls.create(
            twiml=twiml,
            to=to_number,
            from_=from_number,
        )
        print(f"[Twilio Daily] Morning reminder call placed. SID={call.sid}")
        return call.sid
    except Exception as ex:
        print(f"[Twilio Daily] Exception: {repr(ex)}")
        return None