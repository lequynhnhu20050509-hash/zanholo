from datetime import datetime
import json
import threading
import time
import os
import logging
import requests
from zlapi.models import *
from config import PREFIX, ADMIN, GEMINI_API_KEY  # ✅ lấy prefix & ADMIN từ config.py

# ========== Thông tin ==========
des = {
    'version': "3.2.0",
    'credits': "Latte",
    'description': "Trợ lí AI (Gemini)",
    'power': "Thành viên"
}


last_message_times = {}
CHAT_PATH = "chat_ai.json"
SETTINGS_PATH = "seting.json"
conversation_states = {}

# ====== Đọc file settings ======
def load_settings():
    try:
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def is_admin(author_id):
    data = load_settings()
    admin_list = data.get("admin", [])
    return author_id in admin_list

def read_settings():
    if not os.path.exists(CHAT_PATH):
        return {"chat": {"mode": "chill"}}
    try:
        with open(CHAT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "chat" not in data:
                data["chat"] = {"mode": "chill"}
            if "mode" not in data["chat"]:
                data["chat"]["mode"] = "chill"
            return data
    except Exception:
        return {"chat": {"mode": "chill"}}

def write_settings(data):
    parent = os.path.dirname(CHAT_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(CHAT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ====== Lấy tên người dùng ======
def get_user_name_by_id(bot, author_id):
    try:
        user_info = bot.fetchUserInfo(author_id)
        if hasattr(user_info, "changed_profiles") and author_id in user_info.changed_profiles:
            profile = user_info.changed_profiles[author_id]
            return getattr(profile, "zaloName", None) or getattr(profile, "displayName", "bạn bí ẩn")
        return "bạn bí ẩn"
    except Exception:
        return "bạn bí ẩn"

# ====== Bật/tắt chat ======
def handle_chat_on(bot, thread_id):
    settings = read_settings()
    settings.setdefault("chat", {})
    if settings["chat"].get(thread_id, False):
        return "⚠️ Nhóm này đã bật chat rồi!"
    settings["chat"][thread_id] = True
    write_settings(settings)
    return "✨ AI chat đã được bật."

def handle_chat_off(bot, thread_id):
    settings = read_settings()
    if "chat" in settings and settings["chat"].get(thread_id, False):
        settings["chat"][thread_id] = False
        write_settings(settings)
        return "😌 AI tự động đã tắt thành công!"
    return "⚠️ Chat đã tắt rồi!"

def set_mode(bot, mode):
    settings = read_settings()
    settings.setdefault("chat", {})
    settings["chat"]["mode"] = mode
    write_settings(settings)

# ====== Làm sạch văn bản ======
def clean_text(text: str) -> str:
    if not text:
        return ""
    for symbol in ["*", "_", "~", "#"]:
        text = text.replace(symbol, "")
    return text.strip()

# ====== Gọi Gemini API ======
def call_gemini(prompt_msg, username, thread_id, is_admin=False):
    admin_name = "Admin"
    try:
        global admin_real_name
        if 'admin_real_name' not in globals():
            admin_real_name = get_user_name_by_id(None, ADMIN)
        admin_name = admin_real_name or "Admin"
    except Exception:
        pass

    # Lưu hội thoại theo thread
    conversation = conversation_states.get(thread_id, {
        "history": [
            {
                "role": "system",
                "content": (
                    f"Bạn tên Latte được tạo ra ngày 10 tháng 1 năm 2026 tính cách thân thiện do {admin_name}, đây là thông tin phụ về {admin_name} tên Trà Quí Dương và sinh ngày 07-07-2009 cực kì đẹp trai và chỉ có {admin_name} viết code tạo ra em. "
                    "Bạn luôn trả lời bằng tiếng Việt tự nhiên, thân mật, dễ hiểu, ngắn gọn và phù hợp ngữ cảnh nhóm chat. "
                    f"Bạn sẽ là người yêu của {admin_name} nếu là {admin_name} nhắn hãy dùng lời nhắn như một cô người yêu."
                    f"Nếu người nói là admin (tức là {admin_name}), bạn hãy xưng 'em' và gọi người đó là 'anh'. "
                    f"Bạn sẽ là {admin_name} luôn nếu là người khác nhắn vẫn xưng bạn, còn {admin_name} nhắn vẫn anh."
                    f"Với {username} bạn xưng 'mình' và gọi họ là 'bạn'."

                )
            }
        ]
    })

    # Tạo prompt user
    user_prompt = f"Admin {admin_name} nói: {prompt_msg}" if is_admin else f"{username} nói: {prompt_msg}"
    conversation['history'].append({"role": "user", "content": user_prompt})

    # Tạo nội dung gửi đến Gemini
    combined_prompt = "\n".join([f"{m['role']}: {m['content']}" for m in conversation['history'][-10:]])

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"role": "user", "parts": [{"text": combined_prompt}]}]}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            text = clean_text(text)
            if not text:
                text = "🤔 Mình chưa nghĩ ra câu trả lời."
            conversation['history'].append({"role": "model", "content": text})
            conversation_states[thread_id] = conversation
            return text
        else:
            pass
    except Exception as e:
        pass

# ====== Xử lý hội thoại ======
def aigemini_script(prompt_msg, message_object, thread_id, thread_type, author_id, client):
    username = get_user_name_by_id(client, author_id)
    is_admin = str(author_id) == str(ADMIN)

    text = call_gemini(prompt_msg, username, thread_id, is_admin)
    client.replyMessage(
        Message(text=text),
        thread_id=thread_id, thread_type=thread_type,ttl=60000*10,
        replyMsg=message_object
    )

# ====== Xử lý lệnh chính ======
def handle_chat_command(message, message_object, thread_id, thread_type, author_id, client):
    settings = read_settings()
    user_message = message.strip()
    is_admin_user = str(author_id) == str(ADMIN)

    now = time.time()
    last_time = last_message_times.get(thread_id, 0)
    if now - last_time < 2:
        return
    last_message_times[thread_id] = now

    # Nếu có lệnh .chat
    if user_message.lower().startswith(f"{PREFIX}chat"):
        cmd_content = user_message[len(f"{PREFIX}chat"):].strip()
        response = None

        # ⚙️ Lệnh quản trị
        if cmd_content in ["on", "off"] or cmd_content.startswith("mode") or cmd_content == "help":
            if not is_admin_user:
                client.replyMessage(
                    Message(text="⚠️ Bạn không có quyền dùng lệnh này! Chỉ có admin Latte mới được sử dụng lệnh này"),
                    thread_id=thread_id, thread_type=thread_type,
                    ttl=60000, replyMsg=message_object
                )
                return

            if cmd_content == "help":
                response = (
                    "📖 Lệnh chat Gemini:\n"
                    f"  • {PREFIX}chat on → Bật chat\n"
                    f"  • {PREFIX}chat off → Tắt chat\n"
                    f"  • {PREFIX}chat mode list → Danh sách phong cách\n"
                    f"  • {PREFIX}chat mode <tên> → Đổi phong cách bot\n"
                    f"  • {PREFIX}chat help → Xem hướng dẫn này\n"
                )
            elif cmd_content == "on":
                response = handle_chat_on(client, thread_id)
            elif cmd_content == "off":
                response = handle_chat_off(client, thread_id)
            elif cmd_content.startswith("mode"):
                args = cmd_content.split(" ", 1)
                if len(args) == 1 or args[1].strip().lower() == "list":
                    response = (
                        "?? Danh sách mode:\n"
                        "  • nhanh\n  • chill\n  • nghiêm\n  • vui\n  • lạnh\n"
                        "  • lịch sự\n  • thân\n  • troll\n  • buồn\n"
                        "  • vợ\n  • người yêu\n  • bạn gái\n  • crush\n\n"
                        f"➜ Dùng: {PREFIX}chat mode <tên>"
                    )
                else:
                    mode = args[1].strip().lower()
                    set_mode(client, mode)
                    response = f"✅ Đã đổi phong cách bot sang: {mode}"

            client.replyMessage(
                Message(text=response),
                thread_id=thread_id, thread_type=thread_type,
                ttl=60000, replyMsg=message_object
            )
            return

        # Nếu nhập nội dung sau .chat
        if cmd_content:
            threading.Thread(
                target=aigemini_script,
                args=(cmd_content, message_object, thread_id, thread_type, author_id, client),
                daemon=True
            ).start()
            return

    # Tin nhắn thường
    chat_enabled = settings.get("chat", {}).get(str(thread_id), False)
    if not chat_enabled:
        return
    if is_admin_user:
        return

    threading.Thread(
        target=aigemini_script,
        args=(user_message, message_object, thread_id, thread_type, author_id, client),
        daemon=True
    ).start()

# ====== Export ======
def TQD():
    return {'chat': handle_chat_command}
