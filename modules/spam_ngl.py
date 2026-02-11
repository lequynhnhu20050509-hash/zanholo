from zlapi.models import Message, ThreadType
from datetime import datetime
import threading
import requests
import time
import random
import os

des = {
    'version': "2.01",
    'credits': "Latte",
    'description': "Spam ngl bằng API",
    'power': "Thành viên"
}

def get_user_name_by_id(bot, user_id):
    try:
        info = bot.fetchUserInfo(user_id)
        if hasattr(info, "changed_profiles") and user_id in info.changed_profiles:
            profile = info.changed_profiles[user_id]
            return getattr(profile, "zaloName", None) or getattr(profile, "displayName", "Unknown User")
        return "Unknown User"
    except Exception:
        return "Unknown User"

# 🚀 Hàm spam NGL bằng API
def ngl_spam_api(username, count, message):
    success = 0
    bad = 0
    url = "https://adidaphat.site/ngl"

    for i in range(count):
        params = {
            'username': username,
            'message': message,
            'amount': 1  # Gửi 1 lần mỗi request
        }

        try:
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200 and ("success" in res.text.lower() or res.json().get("status") == "success"):
                success += 1
            else:
                bad += 1
        except Exception as e:
            bad += 1

        # Delay ngẫu nhiên để tránh bị block
        time.sleep(random.uniform(0.8, 2.0))

    return success, bad

# 🔧 Command /ngl
def handle_ngl_command(message, message_object, thread_id, thread_type, author_id, client):
    user_name = get_user_name_by_id(client, author_id)
    parts = message.strip().split()

    if len(parts) < 4:
        client.sendMessage(
            Message(text=f"❌ Sai cú pháp!\n\n📌 Dùng đúng dạng:\n{PREFIX}ngl <username> <số_lượng> <nội_dung>`\n\nVí dụ:\n{PREFIX}ngl tqd772009 3 Chào bạn, tôi là bot được tạo bởi Duong\n\n[Ask by: {user_name}]"),
            thread_id, thread_type, ttl=60000
        )
        return

    username = parts[1]

    try:
        count = int(parts[2])
        if count <= 0 or count > 100:  # Giới hạn tối đa 100 để tránh lag
            raise ValueError
    except ValueError:
        client.sendMessage(
            Message(text=f"❌ Số lượng phải là số nguyên dương (tối đa 100)!\n\n[Ask by: {user_name}]"),
            thread_id, thread_type, ttl=60000
        )
        return

    spam_text = ' '.join(parts[3:]).strip()
    if not spam_text:
        client.sendMessage(
            Message(text=f"❌ Nội dung tin nhắn không được để trống!\n\n[Ask by: {user_name}]"),
            thread_id, thread_type, ttl=60000
        )
        return

    # Thông báo bắt đầu
    client.sendMessage(
        Message(text=f"🚀 Đang gửi {count} tin đến {username}\n📝 Nội dung: {spam_text}\n⏳ Vui lòng chờ..."),
        thread_id, thread_type, ttl=60000
    )

    # Chạy spam trong thread riêng
    def do_spam():
        success, bad = ngl_spam_api(username, count, spam_text)
        now = datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
        result = f"""
✨ [ 𝙉𝙂𝙇 𝙎𝙋𝘼𝙈 𝙆𝙀𝙏 𝙌𝙐𝘼 ] ✨
━━━━━━━━━━━━━━━━━━━━━━━
👤 Người dùng: {user_name}
🎯 Username đích: {username}
📨 Đã gửi: {count} tin

✅ Thành công: {success}
❌ Thất bại: {bad}

📝 Nội dung: {spam_text}
🕒 Thời gian: {now}
━━━━━━━━━━━━━━━━━━━━━━━
📌 Cảm ơn đã dùng bot! 💜
"""
        client.sendMessage(Message(text=result.strip()), thread_id, thread_type, ttl=60000)

    threading.Thread(target=do_spam, daemon=True).start()

def TQD():
    return {
        'ngl': handle_ngl_command
    }