import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import requests
import base64
import emoji
import concurrent.futures
import time
import psutil
import platform
import json
import tempfile
from zlapi.models import Message

des = {'version': "1.3.7", 'credits': "Latte", 'description': "cấu hình bot", 'power': "Thành viên"}
start_time = time.time()
start_ram_used = psutil.virtual_memory().used
FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
EMOJI_FONT_PATH = "modules/cache/font/NotoEmoji-Bold.ttf"

AUTO_APPROVE_PATH = "data/auto_approve_settings.json"
ANTIALL_PATH = "data/antiall_settings.json"
ANTIPHOTO_PATH = "data/antiphoto_settings.json"
ANTIRICON_PATH = "data/antiricon_settings.json"
ANTIFILE_PATH = "data/antifile_settings.json"
ANTIVIDEO_PATH = "data/antivideo_settings.json"
ANTISTICKER_PATH = "data/antisticker_settings.json"

def get_font(size):
    try: 
        return ImageFont.truetype(FONT_PATH, size)
    except IOError: 
        return ImageFont.load_default(size=size)

def get_emoji_font(size):
    try: 
        return ImageFont.truetype(EMOJI_FONT_PATH, size)
    except IOError: 
        return get_font(size)

def calculate_text_width(text, font, emoji_font):
    return sum(emoji_font.getlength(c) if emoji.emoji_count(c) else font.getlength(c) for c in text)

def draw_text_center(draw, text, position, font, emoji_font, box_width, text_color=(255,255,255), align="center", shadow=False, shadow_color=(0,0,0), author_font=None):
    x, y = position
    lines = text.splitlines()
    line_spacing = int(font.size * 1.4)
    for i, line in enumerate(lines):
        f = author_font if i == 0 and author_font else font
        line_width = calculate_text_width(line, f, emoji_font)
        if align == "center": tx = x - line_width // 2
        elif align == "left": tx = x
        else: tx = x - line_width
        ty = y + i * line_spacing
        if shadow: draw.text((tx+2, ty+2), line, fill=shadow_color, font=f)
        draw.text((tx, ty), line, fill=text_color, font=f)

def draw_item(draw, icon, name, enabled, position, font, emoji_font, value_font, box_size, icon_size=66):
    x, y = position
    box_w, box_h = box_size
    radius = 32
    fill = (40, 40, 40, 220) if enabled else (45, 45, 45, 190)
    outline = (0, 200, 0) if enabled else (180, 0, 0)
    draw.rounded_rectangle([x, y, x+box_w, y+box_h], radius, fill=fill, outline=outline, width=4)
    icon_font = emoji_font
    icon_x = x + 30
    icon_y = y + box_h//2 - icon_size//2
    draw.text((icon_x, icon_y), icon, font=icon_font, fill=(255,255,255))
    text_x = x + 100
    text_y = y + box_h//2 - font.size//2
    draw.text((text_x, text_y), name, font=font, fill=(220,220,220))
    status = "Bật ⭕" if enabled else "Tắt ❌"
    status_color = (0,255,0) if enabled else (255,0,0)
    value_width = value_font.getlength(status)
    status_x = x + box_w - 40 - value_width
    status_y = y + box_h//2 - value_font.size//2
    draw.text((status_x, status_y), status, font=value_font, fill=status_color)

def fetch_image(url):
    if not url: return None
    try:
        if url.startswith('data:image'): 
            return Image.open(BytesIO(base64.b64decode(url.split(',', 1)[1]))).convert("RGB")
        response = requests.get(url, stream=True, timeout=3)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGB")
    except: 
        return None

def format_time(seconds):
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{int(days)} Ngày, {int(hours)} Giờ, {int(minutes)} Phút, {int(seconds)} Giây"

def system_info(author_name):
    uptime = format_time(time.time() - start_time)
    return (f"🧭 Hoạt động: {uptime}")

def get_max_box_size(features, font, emoji_font, value_font, icon_size, min_box_w=480, box_h=110, max_box_w=760):
    total_widths = [30+icon_size+30+calculate_text_width(n,font,emoji_font)+40+value_font.getlength("Bật ⭕")+40 for i,n,e in features]
    max_w = max(total_widths) if total_widths else min_box_w
    return int(max(min_box_w, min(max_box_w, max_w))), box_h

def process_info_image(
    avatar_url, author_name,
    undo_enabled, loctk_enabled, antispam_enabled,
    antiricon_enabled, antifile_enabled, antivideo_enabled,
    antisticker_enabled, welcome_enabled, antilink_enabled,
    client, thread_id, interaction_enabled, autosend_enabled,
    auto_approve_enabled, antiall_enabled, antiphoto_enabled,
    system_info_text
):
    features = [
        ("🚫", "Chống thu hồi", undo_enabled),
        ("🚫", "Lọc thô tục", loctk_enabled),
        ("🔰", "Chống spam", antispam_enabled),
        ("😡", "Chống spam icon", antiricon_enabled),
        ("📁", "Chống gửi file", antifile_enabled),
        ("📹", "Chống gửi video", antivideo_enabled),
        ("🎨", "Chống gửi sticker", antisticker_enabled),
        ("🔔", "Sự kiện nhóm", welcome_enabled),
        ("📎", "Chặn liên kết", antilink_enabled),
        ("📷", "Chống ảnh", antiphoto_enabled),
        ("💬", "Tương tác", interaction_enabled),
        ("📜", "Tự động gửi", autosend_enabled),
        ("👥", "Phê duyệt TV", auto_approve_enabled),
        ("🚨", "Chống all ẩn", antiall_enabled)
    ]

    # ─── Font setup ───────────────────────────────────────────────
    item_font = get_font(38)
    value_font = get_font(46)
    emoji_font = get_emoji_font(46)
    title_font = get_font(46)
    name_font = get_font(74)
    info_font = get_font(38)
    em_font_info = get_emoji_font(38)

    # ─── Kích thước, bố cục ──────────────────────────────────────
    cols = 2
    gap_x, gap_y = 60, 36
    icon_size = 58
    box_w, box_h = get_max_box_size(features, item_font, emoji_font, value_font, icon_size)
    grid_rows = (len(features) + cols - 1) // cols
    grid_height = grid_rows * box_h + (grid_rows - 1) * gap_y
    left_margin, top_margin, title_area, bottom_margin = 60, 90, 480, 120
    grid_top = top_margin + title_area + 20
    width = 1920
    height = max(1080, grid_top + grid_height + bottom_margin)

    # ─── Nền chính ───────────────────────────────────────────────
    image = Image.new("RGBA", (width, height), (24, 27, 38, 255))

    # Nền mờ từ avatar (blur background)
    avatar_image = fetch_image(avatar_url)
    if avatar_image:
        bg = avatar_image.resize((width, height)).filter(ImageFilter.GaussianBlur(radius=16))
        bg = ImageEnhance.Brightness(bg).enhance(0.38)
        image = Image.alpha_composite(bg.convert("RGBA"), image)

    draw = ImageDraw.Draw(image, "RGBA")

    # ─── Header (vẽ SAU khi có nền để không bị che) ──────────────
    header_height = 280
    header_rect = [60, 60, width - 60, 60 + header_height]
    draw.rounded_rectangle(header_rect, radius=40, fill=(35, 40, 55, 255))

    # Hiệu ứng gradient nhẹ trong header (tùy chọn)
    grad = Image.new("RGBA", (width - 120, header_height), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(grad)
    for i in range(header_height):
        color = (30 + i // 8, 40 + i // 12, 55 + i // 16, 255)
        grad_draw.line([(0, i), (width - 120, i)], fill=color)
    image.paste(grad, (60, 60), grad)

    # ─── Avatar ──────────────────────────────────────────────────
    AVATAR_SIZE = 220
    mask = Image.new("L", (AVATAR_SIZE, AVATAR_SIZE), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, AVATAR_SIZE, AVATAR_SIZE), fill=255)
    if avatar_image:
        avatar_resized = avatar_image.resize((AVATAR_SIZE, AVATAR_SIZE))
        border = Image.new("RGBA", (AVATAR_SIZE + 8, AVATAR_SIZE + 8), (0, 255, 255, 200))
        border_mask = Image.new("L", (AVATAR_SIZE + 8, AVATAR_SIZE + 8), 0)
        ImageDraw.Draw(border_mask).ellipse((0, 0, AVATAR_SIZE + 8, AVATAR_SIZE + 8), fill=255)
        image.paste(border, (left_margin +26, top_margin - 4), border_mask)
        image.paste(avatar_resized, (left_margin + 30, top_margin), mask)

    # ─── Tên & Thông tin hệ thống ────────────────────────────────
    draw_text_center(
        draw,
        author_name,
        (left_margin + AVATAR_SIZE + 120, top_margin + 20),
        name_font,
        em_font_info,
        width - AVATAR_SIZE - left_margin - 80,
        align="left",
        shadow=True,
        author_font=name_font
    )
    draw_text_center(
        draw,
        system_info_text,
        (left_margin + AVATAR_SIZE + 100, top_margin + 120),
        info_font,
        em_font_info,
        width - AVATAR_SIZE - left_margin - 120,
        align="left"
    )

    # ─── Tiêu đề chính ───────────────────────────────────────────
    draw_text_center(
        draw,
        "📊 Cấu hình nhóm",
        (width // 2, top_margin + AVATAR_SIZE + 150),
        title_font,
        emoji_font,
        width - 200,
        text_color=(0, 230, 250),
        align="center"
    )

    # ─── Lưới tính năng ─────────────────────────────────────────
    grid_width = cols * box_w + (cols - 1) * gap_x
    start_x = width // 2 - grid_width // 2

    for idx, (icon, label, status) in enumerate(features):
        grid_row, grid_col = divmod(idx, cols)
        px = start_x + grid_col * (box_w + gap_x)
        py = grid_top + grid_row * (box_h + gap_y)

        draw.rounded_rectangle([px + 4, py + 4, px + box_w + 4, py + box_h + 4],
                               radius=32, fill=(0, 0, 0, 100))

        card = Image.new("RGBA", (box_w, box_h), (30, 30, 35, 230))
        draw_card = ImageDraw.Draw(card)
        draw_card.rounded_rectangle([0, 0, box_w, box_h],
                                    radius=32, fill=(30, 30, 35, 230))
        image.paste(card, (px, py), card)

        draw_item(draw, icon, label, status,
                  (px, py), item_font, emoji_font, value_font,
                  (box_w, box_h), icon_size=icon_size)

    # ─── Footer ─────────────────────────────────────────────────
    footer_text = f"ZaloBot v{des['version']} | {des['credits']}"
    footer_font = get_font(28)
    text_bbox = footer_font.getbbox(footer_text)
    text_w = text_bbox[2] - text_bbox[0]
    draw.text(((width - text_w) // 2, height - 48),
              footer_text, font=footer_font,
              fill=(120, 220, 255, 200))

    return image.convert("RGB")


def autosave(img, quality=97):
    with tempfile.NamedTemporaryFile(suffix=".jpg",delete=False) as tf:
        img.convert("RGB").save(tf,"JPEG",quality=quality,dpi=(180,180),optimize=True,progressive=True,subsampling=0)
        return tf.name

def admin():
    try:
        with open('seting.json','r') as f: 
            return json.load(f).get('account_bot')
    except: 
        return None

def handle_detail_command(message, message_object, thread_id, thread_type, author_id, client):
    output_path = None
    try:
        settings_paths = {
            "undo": "data/undo_settings.json", "loctk": "data/loctk_settings.json",
            "antispam": "data/spam_settings.json", "antiricon": ANTIRICON_PATH,
            "antifile": ANTIFILE_PATH, "antivideo": ANTIVIDEO_PATH,
            "antisticker": ANTISTICKER_PATH, "welcome": "data/welcome_setting.json", 
            "antilink": "data/antilink_settings.json", "antiphoto": "data/antiphoto_settings.json", 
            "autosend": "modules/cache/sendtask_autosend.json"
        }
        settings = {}
        for key,path in settings_paths.items():
            if os.path.exists(path):
                try:
                    with open(path,"r",encoding='utf-8') as f: settings[key] = json.load(f)
                except json.JSONDecodeError: settings[key] = {}

        undo_enabled=settings.get("undo",{}).get("groups",{}).get(str(thread_id),False)
        loctk_enabled=settings.get("loctk",{}).get(str(thread_id),False)
        antispam_enabled=settings.get("antispam",{}).get(str(thread_id),False)
        antiricon_enabled=settings.get("antiricon",{}).get(str(thread_id),False)
        antifile_enabled=settings.get("antifile",{}).get(str(thread_id),False)
        antivideo_enabled=settings.get("antivideo",{}).get(str(thread_id),False)
        antisticker_enabled=settings.get("antisticker",{}).get(str(thread_id),False)
        welcome_enabled=str(thread_id) in settings.get("welcome",{}).get("groups",[])
        antilink_enabled=settings.get("antilink",{}).get(str(thread_id),False)
        antiphoto_enabled=settings.get("antiphoto",{}).get(str(thread_id),False)
        autosend_enabled=str(thread_id) in settings.get("autosend",{}).get("groups",[])

        # ✅ Load tương tác từ chat_ai.json
        interaction_enabled = False
        chat_ai_path = "chat_ai.json"
        if os.path.exists(chat_ai_path):
            try:
                with open(chat_ai_path, "r", encoding="utf-8") as f:
                    chat_data = json.load(f)
                chat_config = chat_data.get("chat", {})
                interaction_enabled = chat_config.get(str(thread_id), False)
            except json.JSONDecodeError:
                interaction_enabled = False

        # Auto approve
        auto_approve_enabled = False
        if os.path.exists(AUTO_APPROVE_PATH):
            with open(AUTO_APPROVE_PATH, "r") as f:
                auto_approve_enabled = json.load(f).get(str(thread_id), False)

        # Anti all
        antiall_enabled = False
        if os.path.exists(ANTIALL_PATH):
            with open(ANTIALL_PATH, "r") as f:
                antiall_enabled = json.load(f).get(str(thread_id), False)

        user_id_to_fetch = admin() or author_id
        user_info = client.fetchUserInfo(user_id_to_fetch) or {}
        user_data = user_info.get('changed_profiles',{}).get(str(user_id_to_fetch),{})
        avatar_url = user_data.get("avatar")
        author_name = user_data.get("displayName", "Unknown")
        system_info_text = system_info(author_name)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            image_to_save = executor.submit(
                process_info_image, avatar_url, author_name, undo_enabled, loctk_enabled,
                antispam_enabled, antiricon_enabled, antifile_enabled, antivideo_enabled,
                antisticker_enabled, welcome_enabled, antilink_enabled, client, thread_id,
                interaction_enabled, autosend_enabled, auto_approve_enabled, antiall_enabled,
                antiphoto_enabled, system_info_text
            ).result()

        output_path = autosave(image_to_save)
        if os.path.exists(output_path):
            with Image.open(output_path) as im:
                width, height = im.size
            client.sendLocalImage(output_path, thread_id=thread_id, thread_type=thread_type, width=width, height=height, ttl=120000)

    except Exception as e:
        client.sendMessage(Message(text=f"• Đã xảy ra lỗi: {str(e)}"), thread_id, thread_type, ttl=60000)
    finally:
        if output_path and os.path.exists(output_path):
            os.remove(output_path)

def TQD():
    return {'detail': handle_detail_command}
