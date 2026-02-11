import os
import json
import tempfile
import requests
import subprocess
import urllib.parse
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageOps, ImageFont, ImageFilter
from zlapi.models import Message
from config import ADMIN
import time
import random

# ================== INFO ==================
des = {
    'version': "2.1.0",
    'credits': "Latte",
    'description': "Đổi avatar bot (chỉ admin)",
    'power': "Admin"
}

# ================== CONFIG ==================
BASE_DIR = os.path.dirname(__file__)
FONT_PATH = os.path.join(BASE_DIR, "cache/font/BeVietnamPro-Bold.ttf")
BG_COLOR = (20, 20, 30)
ACCENT = (70, 130, 255)
TEXT_COLOR = (255, 255, 255)
FADE_COLOR = (200, 200, 200)

# ================== FONT HELPER ==================
def get_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except:
        return ImageFont.load_default()

# ================== DRAW RESULT IMAGE ==================
def draw_result_image(avatar_path, author_name):
    CANVAS_W, CANVAS_H = 900, 900
    CARD_W, CARD_H = 800, 350
    card_x = (CANVAS_W - CARD_W) // 2
    card_y = (CANVAS_H - CARD_H) // 2

    # Tạo canvas RGBA
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), BG_COLOR)

    # Glow đỏ
    glow = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0,0,0,0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.rounded_rectangle([card_x-30, card_y-30, card_x+CARD_W+30, card_y+CARD_H+30], radius=50, fill=ACCENT + (180,))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    canvas = Image.alpha_composite(canvas, glow)

    # Khung chính
    c = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0,0,0,0))
    cd = ImageDraw.Draw(c)
    cd.rounded_rectangle([card_x, card_y, card_x+CARD_W, card_y+CARD_H], radius=45, fill=(35,35,50), outline=ACCENT, width=4)
    canvas = Image.alpha_composite(canvas, c)

    # Avatar tròn
    try:
        avatar = Image.open(avatar_path).convert("RGBA")
        avatar = avatar.resize((230, 230))
        mask = Image.new("L", avatar.size, 0)
        ImageDraw.Draw(mask).ellipse((0,0,230,230), fill=255)
        avatar.putalpha(mask)

        # Viền avatar
        border = Image.new("RGBA", (250,250), (0,0,0,0))
        bd = ImageDraw.Draw(border)
        bd.ellipse((0,0,250,250), outline=ACCENT, width=8)
        border.paste(avatar, (10,10), avatar)
        canvas.paste(border, (card_x+40, card_y+60), border)
    except Exception as e:
        print("Avatar load failed:", e)

    # VẼ CHỮ LÊN ẢNH
    draw = ImageDraw.Draw(canvas)
    f_title = get_font(42)
    f_name = get_font(34)
    f_time = get_font(26)

    # Tiêu đề
    title = "🖼️ ẢNH ĐẠI DIỆN NHÓM"
    draw.text((card_x+280, card_y+70), title, font=f_title, fill=ACCENT)

    # Tên người đổi và thời gian
    now_str = datetime.now().strftime("%H:%M • %d/%m/%Y")
    draw.text((card_x+280, card_y+150), f"    👑 Bởi: {author_name}", font=f_name, fill=TEXT_COLOR)
    draw.text((card_x+280, card_y+200), f"      🕓 {now_str}", font=f_time, fill=FADE_COLOR)

    # Lưu file tạm, chuyển sang RGB để chắc chắn hiển thị đúng
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        out_path = tf.name
    canvas.convert("RGB").save(out_path, "PNG", optimize=True)
    return out_path


# ================== STICKER HELPER ==================
def check_ffmpeg_webp_support():
    try:
        result = subprocess.run(["ffmpeg", "-codecs"], capture_output=True, text=True, check=True)
        return "libwebp_anim" in result.stdout or "libwebp" in result.stdout
    except:
        return False

def get_file_type(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        content_type = response.headers.get("Content-Type", "").lower()
        if "image" in content_type:
            return "image"
        elif "video" in content_type:
            return "video"
        return "unknown"
    except:
        return "unknown"

def upload_to_uguu(file_path):
    try:
        with open(file_path, 'rb') as file:
            response = requests.post("https://uguu.se/upload", files={'files[]': file})
            return response.json().get('files')[0].get('url')
    except:
        return None

def convert_media_and_upload(media_url, file_type, unique_id, client):
    script_dir = os.path.dirname(__file__)
    temp_dir = os.path.join(script_dir, 'cache', 'temp')
    os.makedirs(temp_dir, exist_ok=True)

    temp_input = os.path.join(temp_dir, f"pro_input_{unique_id}")
    temp_webp = os.path.join(temp_dir, f"tranquan_{unique_id}.webp")
    files_to_cleanup = [temp_input, temp_webp]

    try:
        # tải file gốc
        response = requests.get(media_url, stream=True, timeout=15)
        response.raise_for_status()
        with open(temp_input, "wb") as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)

        # nếu là ảnh tĩnh
        if file_type == "image":
            with Image.open(temp_input).convert("RGBA") as img:
                img.thumbnail((512, 512), Image.Resampling.LANCZOS)
                img.save(temp_webp, format="WEBP", quality=80, lossless=False)

        # nếu là video/GIF động
        else:
            subprocess.run([
                "ffmpeg", "-y", "-i", temp_input,
                "-vf", "scale=512:-2",
                "-c:v", "libwebp_anim",
                "-loop", "0",
                "-r", "15",
                "-an",
                "-lossless", "0",
                "-q:v", "80",
                "-loglevel", "error",
                temp_webp
            ], check=True, capture_output=True, text=True)

        return upload_to_uguu(temp_webp)

    finally:
        for f in files_to_cleanup:
            if os.path.exists(f):
                os.remove(f)


def get_user_name_by_id(bot, user_id):
    try:
        info = bot.fetchUserInfo(user_id)
        if hasattr(info, "changed_profiles") and user_id in info.changed_profiles:
            profile = info.changed_profiles[user_id]
            return getattr(profile, "zaloName", None) or getattr(profile, "displayName", "Unknown User")
        return "Unknown User"
    except Exception:
        return "Unknown User"


# ================== MAIN COMMAND ==================
def handle_change_avatar(message, message_object, thread_id, thread_type, author_id, client): 
    if author_id not in ADMIN:
        client.replyMessage(Message("❌ Chỉ admin mới có quyền đổi avatar bot!"), message_object, thread_id, thread_type)
        return

    try:
        # Kiểm tra reply có ảnh không
        if not (hasattr(message_object, "quote") and message_object.quote and "attach" in message_object.quote):
            client.replyMessage(Message("❌ Vui lòng reply 1 ảnh để đổi avatar nhóm!"), message_object, thread_id, thread_type)
            return

        attach_data = message_object.quote["attach"]
        attach_json = json.loads(attach_data)
        photo_url = attach_json.get("hdUrl") or attach_json.get("href")
        if not photo_url:
            client.replyMessage(Message("❌ Không tìm thấy URL ảnh trong reply!"), message_object, thread_id, thread_type)
            return

        photo_url = urllib.parse.unquote(photo_url.replace("\\/", "/"))
        if "jxl" in photo_url:
            photo_url = photo_url.replace("jxl", "jpg")

        # Kiểm tra loại file
        file_type = get_file_type(photo_url)
        if file_type != "image":
            client.replyMessage(Message("❌ Chỉ hỗ trợ ảnh để đổi avatar nhóm!"), message_object, thread_id, thread_type)
            return

        # Thông báo đang xử lý
        processing_msg = Message(text="➜ ⏳ Đang tiến hành đổi avatar nhóm")
        client.replyMessage(processing_msg, message_object, thread_id, thread_type, ttl=120000)

        # Tạo ID duy nhất
        unique_id = f"{thread_id}_{int(time.time())}_{random.randint(1000,9999)}"
        jpg_url = convert_media_and_upload(photo_url, "image", unique_id, client)
        if not jpg_url:
            client.replyMessage(Message("❌ Không thể tạo sticker từ ảnh."), message_object, thread_id, thread_type)
            return

        # Tải ảnh về máy
        local_path = f"group_avatar_{unique_id}.jpg"
        res = requests.get(jpg_url, stream=True)
        if res.status_code == 200:
            with open(local_path, "wb") as f:
                for chunk in res.iter_content(1024):
                    f.write(chunk)
        else:
            client.replyMessage(Message(f"❌ Không tải được ảnh: HTTP {res.status_code}"), message_object, thread_id, thread_type)
            return

        # Đổi avatar bot
        client.changeGroupAvatar(groupId=thread_id, filePath=local_path)

        # Lấy tên người đổi avatar
        author_name = get_user_name_by_id(client, author_id)

        # Vẽ ảnh kết quả
        img_path = draw_result_image(local_path, author_name)
        client.sendLocalImage(img_path, thread_id=thread_id, thread_type=thread_type)

        # Xóa tạm
        os.remove(local_path)
        os.remove(img_path)

    except Exception as e:
        client.replyMessage(Message(f"❌ Lỗi: {e}"), message_object, thread_id, thread_type)
        
def TQD():
    return {
        "avtgr": handle_change_avatar
    }
