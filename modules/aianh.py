import os
import json
import time
import base64
import requests
import urllib.parse
import logging
import tempfile
import subprocess
from PIL import Image
from zlapi.models import Message, Mention
from config import PREFIX, ADMIN
import threading
from config import GEMINI_API_KEY
# ===========================
# ℹ️ Thông tin module
# ===========================
des = {
    'version': "2.5.1",
    'credits': "Latte",
    'description': "AI phân tích ảnh có lịch sử hội thoại và lệnh admin",
    'power': "Thành viên"
}



GEMINI_MODEL = "models/gemini-2.0-flash"

SUPPORTED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
SUPPORTED_VIDEO_EXTENSIONS = ["mp4", "mpeg", "mov", "avi", "x-flv", "mpg", "webm", "wmv", "3gpp"]
SUPPORTED_AUDIO_EXTENSIONS = ["mp3", "wav", "aiff", "aac", "ogg", "flac"]

# ===========================
# 💾 Biến lưu lịch sử hội thoại (RAM)
# ===========================
conversation_states = {}

# ===========================
# 🧩 Helper chung
# ===========================
def get_file_extension(url):
    return url.split("?")[0].split(".")[-1].lower()

def remove_mention(text):
    return text.replace("@bot", "").strip()

def send_success_message(message, message_object, thread_id, thread_type, client, author_id):
    client.replyMessage(
        Message(text=message, mention=Mention(author_id, length=len("@member"), offset=0)),
        message_object, thread_id, thread_type,ttl=60000*10
    )

def send_error_message(message, message_object, thread_id, thread_type, client, ttl):
    client.replyMessage(Message(text=message), message_object, thread_id, thread_type, ttl=ttl)

# ===========================
# 🖼️ / 🎬 / 🎵 Media Helper
# ===========================
def check_ffmpeg_webp_support():
    try:
        result = subprocess.run(["ffmpeg", "-codecs"], capture_output=True, text=True, check=True)
        return "libwebp_anim" in result.stdout or "libwebp" in result.stdout
    except:
        return False

def convert_media_auto(media_url, unique_id):
    temp_dir = tempfile.gettempdir()
    temp_input = os.path.join(temp_dir, f"input_{unique_id}")
    temp_webp = os.path.join(temp_dir, f"output_{unique_id}.webp")
    files_to_cleanup = [temp_input, temp_webp]

    try:
        res = requests.get(media_url, stream=True, timeout=20)
        res.raise_for_status()
        with open(temp_input, "wb") as f:
            for chunk in res.iter_content(8192):
                f.write(chunk)

        ext = get_file_extension(media_url)
        is_image = ext in SUPPORTED_IMAGE_EXTENSIONS
        is_video = ext in SUPPORTED_VIDEO_EXTENSIONS

        if is_image:
            with Image.open(temp_input).convert("RGBA") as img:
                img.thumbnail((512, 512), Image.Resampling.LANCZOS)
                img.save(temp_webp, format="WEBP", quality=80, lossless=False)
        else:
            try:
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
            except:
                return None
        return temp_webp

    finally:
        for f in files_to_cleanup[:-1]:
            if os.path.exists(f):
                os.remove(f)

# ===========================
# 🖼️ Helper lấy ảnh từ reply
# ===========================
def get_photo_url_from_reply(message_object, client, thread_id, thread_type):
    try:
        if not (hasattr(message_object, "quote") and message_object.quote and "attach" in message_object.quote):
            return None
        attach_data = message_object.quote["attach"]
        attach_json = json.loads(attach_data)
        photo_url = attach_json.get("hdUrl") or attach_json.get("href")
        if photo_url:
            photo_url = urllib.parse.unquote(photo_url.replace("\\/", "/"))
            if "jxl" in photo_url:
                photo_url = photo_url.replace("jxl", "jpg")
        return photo_url
    except Exception:
        return None

# ===========================
# Lấy tên người dùng
# ===========================
def get_user_name_by_id(bot, user_id):
    try:
        info = bot.fetchUserInfo(user_id)
        if hasattr(info, "changed_profiles") and user_id in info.changed_profiles:
            profile = info.changed_profiles[user_id]
            return getattr(profile, "zaloName", None) or getattr(profile, "displayName", "Unknown User")
        return "Unknown User"
    except Exception:
        return "Unknown User"

# ===========================
# 🚀 Thread gọi Gemini API (có lưu lịch sử)
# ===========================
def call_gemini_thread(parts, message_object, thread_id, thread_type, client, author_id):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    key = f"{thread_id}_{author_id}"
    history = conversation_states.get(key, [])

    # Thêm câu hỏi user
    history.append({"role": "user", "parts": parts})
    conversation_states[key] = history[-5:]  # Giữ 5 lượt gần nhất

    data = {"contents": conversation_states[key]}

    try:
        response = requests.post(api_url, headers=headers, json=data,timeout=60)
        response.raise_for_status()
        result = response.json()

        if "candidates" in result and result["candidates"]:
            for candidate in result["candidates"]:
                if "content" in candidate and "parts" in candidate["content"]:
                    for part in candidate["content"]["parts"]:
                        if "text" in part:
                            reply_text = part["text"].replace("*", "").strip()
                            # Lưu phản hồi model
                            conversation_states[key].append({"role": "model", "parts": [{"text": reply_text}]})
                            conversation_states[key] = conversation_states[key][-5:]
                            return send_success_message(
                                f"@member\n\n{reply_text}",
                                message_object, thread_id, thread_type,client, author_id
                            )
        send_error_message("⚠️ API không phản hồi.", message_object, thread_id, thread_type, client, ttl=15000)
    except Exception as e:
        logging.error(f"Gemini API error: {e}")
        send_error_message("❌ Lỗi khi gọi API.", message_object, thread_id, thread_type, client, ttl=15000)

# ===========================
# 🎯 Hàm chính Gemini (aianh)
# ===========================
def handle_aianh(message, message_object, thread_id, thread_type, author_id, client, alias_command="aianh"):
    text = message.strip()
    content = remove_mention(text).replace(f"{PREFIX}{alias_command}", "").strip()
    quote = getattr(message_object, "quote", None)

    # ===== Lệnh admin =====
    if content.lower() == "rs" and author_id in ADMIN:
        conversation_states.clear()
        return send_success_message(
            "@member\n🧹 Đã xóa toàn bộ lịch sử hội thoại!",
            message_object, thread_id, thread_type, client, author_id,ttl=15000
        )

    if content.lower() == "info" and author_id in ADMIN:
        info_text = []
        for key, val in conversation_states.items():
            tid, uid = key.split("_")
            name = get_user_name_by_id(client, uid)
            # Chỉ đếm lượt user hỏi
            user_turns = sum(1 for x in val if x["role"] == "user")
            info_text.append(f"{name} → {user_turns} lượt")
        return send_success_message(
            "@member\n📋 Lịch sử hiện tại:\n" + ("\n".join(info_text) if info_text else "Trống"),
            message_object, thread_id, thread_type, client, author_id,ttl=15000
        )

    # ===== Các lệnh bình thường (cần reply media) =====
    if not content or not quote:
        return send_error_message(
            f"⚠️ Vui lòng nhập câu hỏi hoặc reply vào tin nhắn có hình/video/âm thanh.\nVí dụ:\n{PREFIX}{alias_command} Đây là gì?",
            message_object, thread_id, thread_type, client, ttl=15000
        )

    user_input = content
    if len(user_input) > 10000:
        return send_error_message(
            "⚠️ Nội dung quá dài, vui lòng rút gọn!", 
            message_object, thread_id, thread_type, client, ttl=15000
        )

    parts = [{"text": f"{user_input}\n\n(Trả lời bằng tiếng Việt)"}]

    # ===== Xử lý media từ reply =====
    file_url = None
    if quote:
        file_url = get_photo_url_from_reply(message_object, client, thread_id, thread_type)
        if not file_url and hasattr(quote, "attach") and quote.attach:
            attach_data = quote.attach
            attachments = []
            try:
                if isinstance(attach_data, str):
                    attach_json = json.loads(attach_data)
                    attachments = [attach_json] if isinstance(attach_json, dict) else attach_json
                elif isinstance(attach_data, list):
                    attachments = attach_data
            except Exception:
                pass
            for attach in attachments:
                file_url = attach.get("hdUrl") or attach.get("href") or attach.get("oriUrl") or attach.get("thumbUrl")
                if file_url:
                    file_url = urllib.parse.unquote(file_url.replace("\\/", "/"))
                    break

    if file_url:
        try:
            webp_path = convert_media_auto(file_url, unique_id=f"{thread_id}_{author_id}_{int(time.time())}")
            if webp_path:
                with open(webp_path, "rb") as f:
                    base64_data = base64.b64encode(f.read()).decode("utf-8")
                parts.append({"inline_data": {"mime_type": "image/webp", "data": base64_data}})
                os.remove(webp_path)
            else:
                pass
        except Exception as e:
            pass

    # ===== Gọi Gemini API =====
    threading.Thread(
        target=call_gemini_thread,
        args=(parts, message_object, thread_id, thread_type, client, author_id),
        daemon=True
    ).start()

# ===========================
# 🔁 Export
# ===========================
def TQD():
    return {"aianh": handle_aianh}
