import asyncio
import tempfile
import os
from django.utils import timezone
import requests

async def _render_png(html_content: str, output_path: str) -> None:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        page = await browser.new_page(
            viewport={"width": 900, "height": 1200},
            device_scale_factor=2,
        )

        await page.set_content(html_content)
        await page.wait_for_selector(".card")

        card = await page.query_selector(".card")

        if not card:
            raise Exception("Card not found")

        await card.screenshot(path=output_path)
        await browser.close()



def _send_photo(image_path: str):
    token = "8650685796:AAEWB2H-Jsr-34Oycq2EDi-EgbzGTKS0hkw"
    chat_id = [-5186117690, 1836771564]   

    with open(image_path, "rb") as f:
        return requests.post(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            data={"chat_id": chat_id},
            files={"photo": f},
        )
    

def notify_power_schedule(device_id, sessions):

    # -------- BUILD CYCLE CARDS -------- #
    cycle_html = ""

    for s in sessions:
        time = s.start_time.strftime("%I:%M %p").lstrip("0") if s.start_time else "--"
        worker = s.worker.name if s.worker else "--"

        cycle_html += f"""
        <div class="cycle">
            <div class="cycle-left">C{s.cycle_number}</div>
            <div class="cycle-right">
                <div class="assigned">Assigned to</div>
                <div class="name">{worker}</div>
                <div class="time">⏰ {time}</div>
            </div>
        </div>
        """

    now = timezone.now()

    schedule_date = now.strftime("%d %b %Y")
    generated_time = now.strftime("%I:%M %p").lstrip("0")

    # -------- HTML -------- #
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>

    body {{
        background: #0f1a24;
        display: flex;
        justify-content: center;
        padding: 40px;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    .card {{
        width: 820px;
        background: #1c2b3a;
        border-radius: 28px;
        overflow: hidden;
        color: white;
    }}

    .header {{
        padding: 25px 30px;
        font-size: 26px;
        font-weight: 700;
        color: #c8d6e5;
        border-bottom: 1px solid #24394d;
    }}

    .status-bar {{
        background: #0c3b2e;
        color: #2ecc71;
        padding: 14px 30px;
        font-weight: 700;
        letter-spacing: 1px;
    }}

    .info {{
        padding: 25px 30px;
        border-bottom: 1px solid #24394d;
    }}

    .info-row {{
        display: grid;
        grid-template-columns: 40px 1fr auto;
        align-items: center;
        padding: 14px 0;
        border-bottom: 1px solid #223344;
        gap: 10px;
    }}

    .icon {{
    font-size: 18px;
    text-align: center;
    }}

    .label {{
        color: #f5b942;
        font-weight: 600;
    }}

    .value {{
        color: #ffffff;
        font-weight: 500;
    }}

    .section-title {{
        padding: 20px 30px 10px;
        color: #6fa8dc;
        font-weight: 700;
        font-size: 20px;
    }}

    .cycles {{
        padding: 10px 20px 25px;
    }}

    .cycle {{
        display: flex;
        background: #223447;
        border-radius: 16px;
        padding: 15px;
        margin-bottom: 15px;
        align-items: center;
    }}

    .cycle-left {{
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: #2f4b63;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 18px;
        margin-right: 15px;
    }}

    .cycle-right {{
        display: flex;
        flex-direction: column;
    }}

    .assigned {{
        color: #8aa4bf;
        font-size: 14px;
    }}

    .name {{
        font-size: 20px;
        font-weight: 600;
        margin: 3px 0;
    }}

    .time {{
        color: #f5b942;
        font-weight: 600;
    }}

    .footer {{
        padding: 18px 30px;
        background: #16232f;
        display: flex;
        justify-content: space-between;
        font-size: 14px;
    }}

    .footer-left {{
        color: #5d7a95;
    }}

    .footer-right {{
        background: #0c3b2e;
        color: #2ecc71;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
    }}

    </style>
    </head>

    <body>

    <div class="card">

        <div class="header">📅 Task Schedule Confirmed</div>

        <div class="status-bar">● ✔ SCHEDULE CONFIRMED</div>

        <div class="info">

            <div class="info-row">
                <span class="icon">🆔</span>
                <span class="label">DEVICE ID</span>
                <span class="value">{device_id}</span>
            </div>

            <div class="info-row">
                <span class="icon">🔁</span>
                <span class="label">TOTAL CYCLES</span>
                <span class="value">{len(sessions)}</span>
            </div>

            <div class="info-row">
                <span class="icon">📅</span>
                <span class="label">SCHEDULE DATE</span>
                <span class="value">{schedule_date}</span>
            </div>

            <div class="info-row">
                <span class="icon">⏰</span>
                <span class="label">GENERATED AT</span>
                <span class="value">{generated_time}</span>
            </div>

        </div>

        <div class="section-title">👷 Cycle Assignments</div>

        <div class="cycles">
            {cycle_html}
        </div>

        <div class="footer">
            <div class="footer-left">myapp · Schedule Notification</div>
            <div class="footer-right">📋 MANAGER SCHEDULED</div>
        </div>

    </div>

    </body>
    </html>
    """

    # -------- RENDER -------- #
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = tmp.name

    try:
        asyncio.run(_render_png(html, path))
        _send_photo(path)
    finally:
        if os.path.exists(path):
            os.remove(path)