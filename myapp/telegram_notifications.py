import logging
import html
import asyncio
import tempfile
import os
from datetime import datetime

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)



TELEGRAM_BOT_TOKEN = settings.FEEDING_BOT_TOKEN
# Telegram Bot API URL
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
TELEGRAM_GROUP_CHAT_ID = settings.FEEDING_GROUP_CHAT_ID


def _e(text) -> str:
    """Escape HTML special characters"""
    return html.escape("" if text is None else str(text), quote=False)


def _normalize_chat_id(chat_id):
    """Normalize chat ID to proper format"""
    if chat_id is None:
        return None
    s = str(chat_id).strip()
    if not s:
        return None
    # If it's a numeric string (including negative), convert to int
    if s.startswith('-') and s[1:].isdigit():
        return int(s)
    elif s.isdigit():
        return int(s)
    return s


def _build_schedule_card(data: dict) -> str:
    """
    Build HTML card for task schedule notification
    data = {
        "device_id": "...",
        "feed_amount": "...",
        "total_cycles": N,
        "schedule_date": "...",
        "generate_time": "...",
        "assignments": [
            {"cycle": 1, "worker_name": "...", "time": "..."},
            {"cycle": 2, "worker_name": "...", "time": "..."},
            ...
        ]
    }
    """
    device_id = data.get("device_id", "—")
    feed_amount = data.get("feed_amount", "—")
    total_cycles = data.get("total_cycles", 0)
    schedule_date = data.get("schedule_date", "—")
    generate_time = data.get("generate_time", "—")
    assignments = data.get("assignments", [])

    # Header
    header_html = f"""
    <div class="header">
        <div class="header-left">
            <span class="header-icon">📅</span>
            <span class="header-title">Task Schedule Confirmed</span>
        </div>
    </div>
    """

    # Status bar
    status_html = """
    <div class="status-bar">
        <div class="status-dot"></div>
        <span class="status-label">✅ SCHEDULE CONFIRMED</span>
    </div>
    """

    # Basic info fields
    basic_fields = [
        ("🆔", "Device ID", device_id),
        ("🍽️", "Feed Amount", f"{feed_amount} Kg"),
        ("🔄", "Total Cycles", str(total_cycles)),
        ("📆", "Schedule Date", schedule_date),
        ("⏰", "Generated At", generate_time),
    ]

    basic_rows = ""
    for icon, label, value in basic_fields:
        basic_rows += f"""
        <div class="row">
            <span class="icon">{icon}</span>
            <div class="field">
                <span class="label">{label}</span>
                <span class="value">{_e(str(value))}</span>
            </div>
        </div>"""

    # Assignment rows (one per cycle)
    assignment_header = """
    <div class="assignment-header">
        <span class="assignment-title">👷 Cycle Assignments</span>
    </div>
    """
    
    assignment_rows = ""
    for assignment in assignments:
        cycle = assignment.get("cycle", "—")
        worker_name = assignment.get("worker_name", "—")
        time = assignment.get("time", "—")
        
        assignment_rows += f"""
        <div class="assignment-row">
            <span class="cycle-badge">C{cycle}</span>
            <div class="assignment-info">
                <div class="assignment-label">Assigned to</div>
                <div class="assignment-value">{_e(worker_name)}</div>
                <div class="assignment-time">⏰ {_e(time)}</div>
            </div>
        </div>"""

    # Footer
    footer_html = """
    <div class="footer">
        <span class="footer-text">myapp · Schedule Notification</span>
        <span class="schedule-badge">📋 MANAGER SCHEDULED</span>
    </div>
    """

    # Build complete card
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

  .status-bar {{
    padding: 20px 36px;
    background: #0d2b1a;
    display: flex;
    align-items: center;
    gap: 14px;
    border-bottom: 2px solid #1a2738;
  }}

  .status-dot {{
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #2ecc71;
    flex-shrink: 0;
  }}

  .status-label {{
    color: #2ecc71;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 1.2px;
  }}

  .body {{
    padding: 10px 36px 20px;
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

  .assignment-header {{
    padding: 20px 36px;
    background: #1b4f72;
    border-bottom: 2px solid #1a2738;
  }}

  .assignment-title {{
    color: #5dade2;
    font-size: 24px;
    font-weight: 700;
  }}

  .assignment-row {{
    padding: 16px 36px;
    border-bottom: 1px solid #1c2b3a;
    display: flex;
    align-items: center;
    gap: 16px;
  }}

  .assignment-row:last-child {{ border-bottom: none; }}

  .cycle-badge {{
    background: #2e4a62;
    color: #5dade2;
    font-family: 'JetBrains Mono', monospace;
    font-size: 20px;
    font-weight: 700;
    padding: 8px 18px;
    border-radius: 20px;
    flex-shrink: 0;
  }}

  .assignment-info {{
    flex: 1;
  }}

  .assignment-label {{
    color: #8b9da7;
    font-size: 16px;
    margin-bottom: 4px;
  }}

  .assignment-value {{
    color: #ffffff;
    font-size: 22px;
    font-weight: 600;
    margin-bottom: 4px;
  }}

  .assignment-time {{
    color: #f5b942;
    font-family: 'JetBrains Mono', monospace;
    font-size: 18px;
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

  .schedule-badge {{
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
    {header_html}
    {status_html}
    <div class="body">
      {basic_rows}
    </div>
    {assignment_header}
    {assignment_rows}
    {footer_html}
  </div>
</body>
</html>"""


async def _render_png(html_content: str, output_path: str) -> None:
    """Render HTML card to PNG using Playwright"""
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # 2x viewport + device_scale_factor=2 = true HD/Retina PNG
        page = await browser.new_page(
            viewport={"width": 840, "height": 1600},
            device_scale_factor=2,
        )
        await page.set_content(html_content, wait_until="networkidle")
        card = await page.query_selector(".card")
        await card.screenshot(path=output_path, type="png")
        await browser.close()


def _send_photo(image_path: str, chat_id=None) -> dict | None:
    """Send photo to Telegram group"""
    token = TELEGRAM_BOT_TOKEN
    target_chat_id = chat_id or _normalize_chat_id(TELEGRAM_GROUP_CHAT_ID)
    
    if not token or target_chat_id is None:
        logger.error("[MyApp Telegram] TELEGRAM_BOT_TOKEN or TELEGRAM_GROUP_CHAT_ID not set.")
        print(f"[DEBUG] Token: {token}, Chat ID: {target_chat_id}")
        return None
    
    print(f"[DEBUG] Sending to Telegram: Token={token[:20]}..., Chat ID={target_chat_id}")
    
    try:
        with open(image_path, "rb") as f:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": target_chat_id},
                files={"photo": ("card.png", f, "image/png")},
                timeout=30,
            )
        print(f"[DEBUG] Response status: {r.status_code}")
        print(f"[DEBUG] Response body: {r.text[:500]}")
        
        if r.status_code != 200:
            logger.error(f"[MyApp Telegram] HTTP {r.status_code}: {r.text[:600]}")
            return None
        try:
            data = r.json()
            print(f"[DEBUG] Telegram API response: {data}")
        except ValueError:
            logger.error(f"[MyApp Telegram] Non-JSON body: {r.text[:600]}")
            return None
        if not data.get("ok"):
            logger.error(f"[MyApp Telegram] API error: {data}")
            return None
        return data
    except Exception as ex:
        logger.error(f"[MyApp Telegram] Exception: {repr(ex)}")
        print(f"[DEBUG] Exception: {repr(ex)}")
        return None


def notify_task_schedule(data: dict) -> dict | None:
    """
    Build HTML card, render to PNG, and send via Telegram
    """
    html_card = _build_schedule_card(data)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        asyncio.run(_render_png(html_card, tmp_path))
        return _send_photo(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def notify_task_abort(data: dict) -> dict | None:
    """
    Send abort notification to Telegram
    Format: Device BFL_FdtryA001 cycle 3 has been aborted ❌. Assigned worker: Dibya.
    """
    device_id = data.get("device_id", "—")
    cycle = data.get("cycle", "—")
    worker_name = data.get("worker_name", "—")
    
    # Simple text message
    message = f"Device {device_id} cycle {cycle} has been aborted ❌. Assigned worker: {worker_name}."
    
    token = TELEGRAM_BOT_TOKEN
    target_chat_id = _normalize_chat_id(TELEGRAM_GROUP_CHAT_ID)
    
    if not token or target_chat_id is None:
        logger.error("[MyApp Telegram Abort] TELEGRAM_BOT_TOKEN or TELEGRAM_GROUP_CHAT_ID not set.")
        return None
    
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={
                "chat_id": target_chat_id,
                "text": message
            },
            timeout=30,
        )
        
        print(f"[DEBUG] Abort message sent: {message}")
        
        if r.status_code != 200:
            logger.error(f"[MyApp Telegram Abort] HTTP {r.status_code}: {r.text[:600]}")
            return None
        
        try:
            data = r.json()
        except ValueError:
            logger.error(f"[MyApp Telegram Abort] Non-JSON body: {r.text[:600]}")
            return None
        
        if not data.get("ok"):
            logger.error(f"[MyApp Telegram Abort] API error: {data}")
            return None
        
        return data
    except Exception as ex:
        logger.error(f"[MyApp Telegram Abort] Exception: {repr(ex)}")
        return None


def notify_task_completion(data: dict) -> dict | None:
    """
    Send task completion notification to Telegram
    Format: Device (fdtryA001) cycle n has been completed successfully ✅. Worker assigned by (Worker name).
    """
    device_id = data.get("device_id", "—")
    cycle = data.get("cycle", "—")
    worker_name = data.get("worker_name", "—")
    
    # Simple text message
    message = f"Device ({device_id}) cycle {cycle} has been completed successfully ✅. Worker assigned by ({worker_name})."
    
    token = TELEGRAM_BOT_TOKEN
    target_chat_id = _normalize_chat_id(TELEGRAM_GROUP_CHAT_ID)
    
    if not token or target_chat_id is None:
        logger.error("[MyApp Telegram Complete] TELEGRAM_BOT_TOKEN or TELEGRAM_GROUP_CHAT_ID not set.")
        return None
    
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={
                "chat_id": target_chat_id,
                "text": message
            },
            timeout=30,
        )
        
        print(f"[DEBUG] Completion message sent: {message}")
        
        if r.status_code != 200:
            logger.error(f"[MyApp Telegram Complete] HTTP {r.status_code}: {r.text[:600]}")
            return None
        
        try:
            data = r.json()
        except ValueError:
            logger.error(f"[MyApp Telegram Complete] Non-JSON body: {r.text[:600]}")
            return None
        
        if not data.get("ok"):
            logger.error(f"[MyApp Telegram Complete] API error: {data}")
            return None
        
        return data
    except Exception as ex:
        logger.error(f"[MyApp Telegram Complete] Exception: {repr(ex)}")
        return None
