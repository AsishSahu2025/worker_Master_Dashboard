
"""
Telegram alerts for Checktray tasks — sends a styled PNG card via sendPhoto.
Requires: pip install playwright && playwright install chromium
"""
from __future__ import annotations

import html
import re
import asyncio
import tempfile
import os

import requests
from django.conf import settings
from django.utils import timezone
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from checktray.models import ChecktrayTask

from django.utils import timezone


def _e(text) -> str:
    return html.escape("" if text is None else str(text), quote=False)


def _normalize_chat_id(chat_id):
    if chat_id is None:
        return None
    s = str(chat_id).strip()
    if not s:
        return None
    if re.fullmatch(r"-?\d+", s):
        try:
            return int(s)
        except ValueError:
            return s
    return s


def _status_meta(raw: str) -> dict:
    return {
        "Completed":         {"emoji": "✅", "label": "COMPLETED",  "bg": "#0d2b1a", "color": "#2ecc71", "dot": "#2ecc71"},
        "Running":           {"emoji": "🟢", "label": "RUNNING",    "bg": "#0d1f35", "color": "#5dade2", "dot": "#5dade2"},
        "Pending":           {"emoji": "⏳", "label": "PENDING",    "bg": "#2e2200", "color": "#f5b942", "dot": "#f5b942"},
        "ScheduleRequested": {"emoji": "📅", "label": "SCHEDULED",  "bg": "#1a1040", "color": "#bb8fce", "dot": "#bb8fce"},
        "No Status":         {"emoji": "⚪", "label": "NO STATUS",  "bg": "#1c1c1c", "color": "#888888", "dot": "#888888"},
    }.get(raw, {"emoji": "📌", "label": raw.upper() or "UNKNOWN",   "bg": "#1c1c1c", "color": "#aaaaaa", "dot": "#aaaaaa"})


def _format_start_line(dt) -> str:
    if not dt:
        return "—"
    return dt.strftime("%I:%M %p").lstrip("0") + "  ·  " + dt.strftime("%d %b %Y")


def _starts_in_line(task: ChecktrayTask) -> str:
    st = task.start_time
    now = timezone.now()
    raw = (task.status or "").strip()

    if raw == "Completed":
        if task.stop_time:
            return "Finished at " + task.stop_time.strftime("%I:%M %p").lstrip("0") + "  ·  " + task.stop_time.strftime("%d %b %Y")
        return "Finished ✅"

    if raw == "Running":
        return "Running now 🏃"

    if not st:
        return "—"

    sec = int((st - now).total_seconds())

    if sec < -300:
        return "Start time passed — waiting ⏳"
    if sec <= 90:
        return "Starting now 🚀"
    if sec < 3600:
        m = max(1, (sec + 59) // 60)
        return f"in {m} min"
    if sec < 86400:
        h, rem = divmod(sec, 3600)
        m = rem // 60
        return f"in {h}h {m}m" if m else f"in {h}h"

    d = sec // 86400
    return "in 1 day" if d == 1 else f"in {d} days"


def _build_html_card(task: ChecktrayTask) -> str:
    dev         = task.device_id
    device_pk   = dev.device_id if dev else "—"
    device_name = getattr(dev, "device_type", None) or "—"
    worker      = task.worker_name.name if task.worker_name else "—"
    image_cycle = task.image_update or "—"
    start_line  = _format_start_line(task.start_time)
    starts_in   = _starts_in_line(task)
    raw_status  = (task.status or "").strip()
    meta        = _status_meta(raw_status)

    # ── banner for Pending only ───────────────────────────────────
    if raw_status == "Pending":
        banner_bg    = "#2e2200"
        banner_color = "#f5b942"
        banner_icon  = "⏳"
        banner_text  = "Device Schedule Confirmed"
        banner_sub   = "Task is queued and waiting to run"
    else:
        banner_bg = banner_color = banner_icon = banner_text = banner_sub = None

    banner_html = ""
    if banner_text:
        banner_html = f"""
    <div class="banner" style="background:{banner_bg};">
      <div class="banner-icon">{banner_icon}</div>
      <div>
        <div class="banner-title" style="color:{banner_color};">{banner_text}</div>
        <div class="banner-sub">{banner_sub}</div>
      </div>
    </div>"""

    fields = [
        ("🆔", "Device ID",   device_pk),
        ("🖥️", "Device",      device_name),
        ("👷", "Worker",      worker),
        ("🖼️", "Image Cycle", image_cycle),
        ("🕐", "Start Time",  start_line),
        ("⏱️", "Starts In",   starts_in),
    ]

    rows_html = ""
    for icon, label, value in fields:
        rows_html += f"""
        <div class="row">
          <span class="icon">{icon}</span>
          <div class="field">
            <span class="label">{label}</span>
            <span class="value">{_e(str(value))}</span>
          </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=DM+Sans:wght@400;600;700&display=swap');

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    background: #17212b;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 840px;
    padding: 48px;
    font-family: 'DM Sans', sans-serif;
  }}

  .card {{
    background: #232e3c;
    border-radius: 32px;
    width: 100%;
    overflow: hidden;
  }}

  .header {{
    padding: 32px 36px 24px;
    border-bottom: 2px solid #1a2738;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}

  .header-left {{
    display: flex;
    align-items: center;
    gap: 14px;
  }}

  .header-icon {{ font-size: 38px; }}

  .header-title {{
    color: #aac8e4;
    font-size: 26px;
    font-weight: 700;
    letter-spacing: 0.3px;
  }}

  .task-badge {{
    background: #1b4f72;
    border-radius: 40px;
    padding: 8px 22px;
    color: #5dade2;
    font-size: 22px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
  }}

  .banner {{
    display: flex;
    align-items: center;
    gap: 20px;
    border-bottom: 2px solid #1a2738;
    padding: 26px 36px;
  }}

  .banner-icon {{
    font-size: 48px;
    flex-shrink: 0;
  }}

  .banner-title {{
    font-size: 26px;
    font-weight: 700;
    letter-spacing: 0.3px;
    margin-bottom: 4px;
  }}

  .banner-sub {{
    color: #4a6278;
    font-size: 20px;
    font-weight: 400;
  }}

  .status-bar {{
    padding: 20px 36px;
    background: {meta['bg']};
    display: flex;
    align-items: center;
    gap: 14px;
    border-bottom: 2px solid #1a2738;
  }}

  .status-dot {{
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: {meta['dot']};
    flex-shrink: 0;
  }}

  .status-label {{
    color: {meta['color']};
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 1.2px;
  }}

  .body {{
    padding: 10px 36px 10px;
  }}

  .row {{
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 18px 0;
    border-bottom: 1px solid #1c2b3a;
  }}

  .row:last-child {{ border-bottom: none; }}

  .icon {{
    font-size: 26px;
    width: 36px;
    text-align: center;
    flex-shrink: 0;
  }}

  .field {{
    flex: 1;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 14px;
  }}

  .label {{
    color: #f5b942;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    white-space: nowrap;
  }}

  .value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 22px;
    font-weight: 400;
    text-align: right;
    color: #ffffff;
  }}

  .footer {{
    padding: 20px 36px;
    background: #1b2838;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-top: 2px solid #1a2738;
  }}

  .footer-text {{
    color: #2e4560;
    font-size: 18px;
    letter-spacing: 0.4px;
  }}

  .starts-badge {{
    background: #1a2e1a;
    border-radius: 40px;
    padding: 8px 22px;
    color: #58d68d;
    font-size: 20px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
  }}
</style>
</head>
<body>
  <div class="card">

    <div class="header">
      <div class="header-left">
        <span class="header-icon">📋</span>
        <span class="header-title">Check Tray Update</span>
      </div>
    </div>

    {banner_html}

    <div class="status-bar">
      <div class="status-dot"></div>
      <span class="status-label">{meta['emoji']}  {meta['label']}</span>
    </div>

    <div class="body">
      {rows_html}
    </div>

    <div class="footer">
      <span class="footer-text">checktray · automated alert</span>
      <span class="starts-badge">▶ {_e(starts_in)}</span>
    </div>

  </div>
</body>
</html>"""


async def _render_png(html_content: str, output_path: str) -> None:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": 840, "height": 1200},
            device_scale_factor=2,
        )
        await page.set_content(html_content, wait_until="networkidle")
        card = await page.query_selector(".card")
        await card.screenshot(path=output_path, type="png")
        await browser.close()


def _send_photo(image_path: str) -> dict | None:
    # token = (getattr(settings, "TELEGRAM_BOT_TOKEN", None) or "").strip() or None
    # chat_id = _normalize_chat_id(getattr(settings, "TELEGRAM_GROUP_CHAT_ID", None))
    token = (getattr(settings, "CHECKTRAY_BOT_TOKEN", None) or "").strip() or None
    chat_id = _normalize_chat_id(getattr(settings, "CHECKTRAY_GROUP_CHAT_ID", None))
    if not token or chat_id is None:
        print("[Checktray Telegram] TELEGRAM_BOT_TOKEN or TELEGRAM_GROUP_CHAT_ID not set.")
        return None
    try:
        with open(image_path, "rb") as f:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": chat_id},
                files={"photo": ("card.png", f, "image/png")},
                timeout=30,
            )
        if r.status_code != 200:
            print("[Checktray Telegram] HTTP", r.status_code, r.text[:600])
            return None
        try:
            data = r.json()
        except ValueError:
            print("[Checktray Telegram] Non-JSON body:", r.text[:600])
            return None
        if not data.get("ok"):
            print("[Checktray Telegram] API:", data)
        return data
    except Exception as ex:
        print("[Checktray Telegram] Exception:", repr(ex))
        return None


def _send_message(text: str) -> dict | None:
    """Send a plain text message via Telegram sendMessage."""
    # token = (getattr(settings, "TELEGRAM_BOT_TOKEN", None) or "").strip() or None
    # chat_id = _normalize_chat_id(getattr(settings, "TELEGRAM_GROUP_CHAT_ID", None))
    token = (getattr(settings, "CHECKTRAY_BOT_TOKEN", None) or "").strip() or None
    chat_id = _normalize_chat_id(getattr(settings, "CHECKTRAY_GROUP_CHAT_ID", None))
    if not token or chat_id is None:
        print("[Checktray Telegram] TELEGRAM_BOT_TOKEN or TELEGRAM_GROUP_CHAT_ID not set.")
        return None
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            timeout=30,
        )
        if r.status_code != 200:
            print("[Checktray Telegram] HTTP", r.status_code, r.text[:600])
            return None
        try:
            data = r.json()
        except ValueError:
            print("[Checktray Telegram] Non-JSON body:", r.text[:600])
            return None
        if not data.get("ok"):
            print("[Checktray Telegram] API:", data)
        return data
    except Exception as ex:
        print("[Checktray Telegram] Exception:", repr(ex))
        return None


def notify_checktray_task(task_id: int) -> dict | None:
    """
    - Pending   → PNG card
    - Completed → plain text message
    - Running / anything else → do nothing
    """
    try:
        task = ChecktrayTask.objects.select_related("device_id", "worker_name").get(pk=task_id)
    except ChecktrayTask.DoesNotExist:
        print(f"[Checktray Telegram] Task id={task_id} not found.")
        return None

    raw_status = (task.status or "").strip()

    # ── Pending: send PNG card ──
    if raw_status == "Pending":
        html_card = _build_html_card(task)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            asyncio.run(_render_png(html_card, tmp_path))
            return _send_photo(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ── Completed: plain text only ──
    if raw_status == "Completed":
        dev = task.device_id
        device_pk = dev.device_id if dev else "—"
        text = f"Device ({device_pk}) completed successfully ✅"
        return _send_message(text)

    # ── Running / anything else: do nothing ──
    print(f"[Checktray Telegram] Skipping notification for status: {raw_status}")
    return None


def notify_checktray_abort(task) -> dict | None:
    """
    Called directly with the task object BEFORE it is deleted in paho_mqtt.py.
    Sends a plain text abort message to Telegram.
    """
    try:
        dev = task.device_id
        device_pk = dev.device_id if dev else "—"
        text = f"Device ({device_pk}) Cycle is ABORTED ❌"
        return _send_message(text)
    except Exception as ex:
        print("[Checktray Telegram] Abort notify exception:", repr(ex))
        return None
    

def notify_checktray_cancel(task) -> dict | None:
    """
    Called directly BEFORE deleting task when schedule is cancelled.
    """
    try:
        dev = task.device_id
        device_pk = dev.device_id if dev else "—"

        text = f"Device ({device_pk}) schedule has been CANCELLED ❌"

        return _send_message(text)

    except Exception as ex:
        print("[Checktray Telegram] Cancel notify exception:", repr(ex))
        return None