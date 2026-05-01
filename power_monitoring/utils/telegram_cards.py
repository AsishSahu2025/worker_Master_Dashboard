from PIL import Image, ImageDraw, ImageFont
import io

def generate_cycle_card(device_id, cycles, timestamp):
    width, height = 900, 500
    img = Image.new("RGB", (width, height), (10, 15, 30))
    draw = ImageDraw.Draw(img)

    # -------- Fonts -------- #
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        sub_title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        value_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
    except:
        title_font = sub_title_font = label_font = value_font = None

    # -------- HEADER -------- #
    draw.text((40, 30), "⚡ POWER MONITORING", fill=(0, 255, 200), font=title_font)
    draw.text((40, 90), "🚀 New Cycle Generated", fill=(0, 200, 255), font=sub_title_font)

    # Divider
    draw.line((40, 140, 860, 140), fill=(80, 80, 120), width=2)

    # -------- DETAILS -------- #
    y_start = 170
    gap = 60

    # Device ID
    draw.text((60, y_start), "📟 Device ID", fill="white", font=label_font)
    draw.text((350, y_start), f":  {device_id}", fill=(255, 215, 0), font=value_font)

    # Total Cycles
    draw.text((60, y_start + gap), "🔢 Total Cycles", fill="white", font=label_font)
    draw.text((350, y_start + gap), f":  {len(cycles)}", fill=(0, 255, 255), font=value_font)

    # Status
    draw.text((60, y_start + gap*2), "📊 Status", fill="white", font=label_font)
    draw.text((350, y_start + gap*2), ":  PENDING", fill=(255, 165, 0), font=value_font)

    # Current Time
    draw.text((60, y_start + gap*3), "🕒 Time", fill="white", font=label_font)
    draw.text((350, y_start + gap*3), f":  {timestamp}", fill=(180, 180, 180), font=value_font)

    # -------- FOOTER LINE -------- #
    draw.line((40, 460, 860, 460), fill=(80, 80, 120), width=2)

    # -------- SAVE -------- #
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer


def generate_schedule_card(device_id, sessions, timestamp):
    width, height = 1100, 600
    img = Image.new("RGB", (width, height), (10, 15, 30))
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 45)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
        value_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        title_font = label_font = value_font = small_font = None

    # -------- HEADER -------- #
    draw.text((40, 30), "⚡ POWER MONITORING", fill=(0, 255, 200), font=title_font)
    draw.text((40, 85), "📅 Schedule Created", fill=(0, 200, 255), font=label_font)

    draw.line((40, 120, 1060, 120), fill=(80, 80, 120), width=2)

    # -------- DEVICE -------- #
    draw.text((40, 140), "📟 Device", fill="white", font=label_font)
    draw.text((200, 140), f": {device_id}", fill=(255, 215, 0), font=value_font)

    # -------- TABLE HEADER -------- #
    y = 200
    draw.text((40, y), "Cycle", fill=(0,255,255), font=label_font)
    draw.text((120, y), "Worker", fill=(0,255,255), font=label_font)
    draw.text((300, y), "Start", fill=(0,255,255), font=label_font)
    draw.text((480, y), "End", fill=(0,255,255), font=label_font)
    draw.text((660, y), "Status", fill=(0,255,255), font=label_font)

    # -------- DATA -------- #
    y += 50
    for s in sessions[:5]:
        start = s.start_time.strftime("%H:%M:%S") if s.start_time else "-"
        end = s.end_time.strftime("%H:%M:%S") if s.end_time else "-"
        worker_name = s.worker.name if s.worker else "N/A"

        draw.text((40, y), str(s.cycle_number), fill="white", font=label_font)
        draw.text((120, y), worker_name, fill=(255,255,255), font=label_font)
        draw.text((300, y), start, fill=(0,255,150), font=label_font)
        draw.text((480, y), end, fill=(0,255,150), font=label_font)
        draw.text((660, y), s.status, fill=(255,165,0), font=label_font)

        y += 40

    # -------- FOOTER -------- #
    draw.line((40, 540, 1060, 540), fill=(80, 80, 120), width=2)
    draw.text((40, 560), f"🕒 {timestamp}", fill="gray", font=small_font)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer

def generate_live_data_card(device_id, session_id, r, y, b, wh, timestamp):
    width, height = 900, 500
    img = Image.new("RGB", (width, height), (10, 15, 30))
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
        value_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except:
        title_font = label_font = value_font = None

    # -------- HEADER -------- #
    draw.text((40, 20), "⚡ LIVE ENERGY DATA", fill=(0, 255, 200), font=title_font)
    draw.line((40, 80, 860, 80), fill=(80, 80, 120), width=2)

    # -------- DEVICE INFO -------- #
    draw.text((60, 110), "Device", fill="white", font=label_font)
    draw.text((300, 110), f": {device_id}", fill=(255, 215, 0), font=value_font)

    draw.text((60, 150), "Session", fill="white", font=label_font)
    draw.text((300, 150), f": {session_id}", fill=(0, 255, 255), font=value_font)

    # -------- CURRENT -------- #
    draw.text((60, 200), "Current (A)", fill="white", font=label_font)
    draw.text((300, 200), f": R={r:.2f}  Y={y:.2f}  B={b:.2f}", fill=(0, 255, 150), font=value_font)

    # -------- VOLTAGE -------- #
    draw.text((60, 250), "Voltage (V)", fill="white", font=label_font)
    draw.text((300, 250), ": 230 / 230 / 230", fill=(200, 200, 255), font=value_font)

    # -------- ENERGY -------- #
    draw.text((60, 300), "Energy", fill="white", font=label_font)
    draw.text((300, 300), f": {wh:.4f} Wh", fill=(255, 140, 0), font=value_font)

    # -------- TIME -------- #
    draw.text((60, 360), "Time", fill="white", font=label_font)
    draw.text((300, 360), f": {timestamp}", fill=(180, 180, 180), font=value_font)

    # -------- SAVE -------- #
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer

def generate_abort_card(device_id, cycle_no, timestamp):
    width, height = 900, 400
    img = Image.new("RGB", (width, height), (20, 10, 10))
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
    except:
        title_font = text_font = None

    # Header
    draw.text((40, 20), "🛑 SESSION ABORTED", fill=(255, 80, 80), font=title_font)

    # Box
    draw.rounded_rectangle((40, 100, 860, 300), radius=20, fill=(40, 20, 20))

    draw.text((80, 140), f"Device ID  : {device_id}", fill="white", font=text_font)
    draw.text((80, 190), f"Cycle No   : {cycle_no}", fill="white", font=text_font)
    draw.text((80, 240), f"Status     : ABORTED", fill=(255, 100, 100), font=text_font)

    # Footer
    draw.text((40, 340), f"🕒 {timestamp}", fill="gray", font=text_font)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer


def generate_status_update_card(device_id, cycle_no, status, timestamp):
    # -------- Canvas -------- #
    width, height = 900, 450
    img = Image.new("RGB", (width, height), (20, 20, 20))
    draw = ImageDraw.Draw(img)

    # -------- Colors -------- #
    WHITE = (255, 255, 255)
    GRAY = (160, 160, 160)
    LINE = (60, 60, 60)

    # Status colors
    STATUS_COLOR = {
        "PENDING": (255, 193, 7),
        "PROCESSING": (0, 123, 255),
        "COMPLETED": (40, 167, 69),
        "FAILED": (220, 53, 69),
        "ABORTED": (255, 87, 34)
    }

    color = STATUS_COLOR.get(status, WHITE)

    # -------- Fonts -------- #
    try:
        title_font = ImageFont.truetype("arial.ttf", 40)
        label_font = ImageFont.truetype("arial.ttf", 26)
        value_font = ImageFont.truetype("arial.ttf", 32)
    except:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        value_font = ImageFont.load_default()

    # -------- Title -------- #
    draw.text((30, 30), "📊 SESSION STATUS UPDATE", fill=WHITE, font=title_font)

    # -------- Divider -------- #
    draw.line((30, 90, width - 30, 90), fill=LINE, width=2)

    # -------- Content -------- #
    y = 120

    def row(label, value, val_color=WHITE):
        nonlocal y
        draw.text((40, y), label, fill=GRAY, font=label_font)
        draw.text((300, y), value, fill=val_color, font=value_font)
        y += 60

    row("Session ID:", str(cycle_no))
    row("Device:", device_id)
    row("Status:", status, color)
    row("Updated At:", timestamp)

    # -------- Save to buffer -------- #
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.name = "status.png"
    buffer.seek(0)

    return buffer