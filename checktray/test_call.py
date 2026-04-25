"""
Temporary test file — delete after testing.
"""
from django.conf import settings
from twilio.rest import Client


def test_call_now():
    """
    Call the manager immediately for testing.
    Simulates what would happen 10 mins before a 6:20 PM schedule.
    """
    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
    auth_token  = getattr(settings, "TWILIO_AUTH_TOKEN",  None)
    from_number = getattr(settings, "TWILIO_FROM_NUMBER", None)
    to_number   = getattr(settings, "MANAGER_PHONE",      None)

    if not all([account_sid, auth_token, from_number, to_number]):
        print("[Twilio Test] Missing settings.")
        return None

    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="alice">
    Hello. This is an automated alert from Check Tray.
    Device D001 has a task scheduled to start at 6 20 PM today.
    Please ensure the device and worker are ready.
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
        print(f"[Twilio Test] Call placed! SID={call.sid}")
        return call.sid
    except Exception as ex:
        print(f"[Twilio Test] Exception: {repr(ex)}")
        return None