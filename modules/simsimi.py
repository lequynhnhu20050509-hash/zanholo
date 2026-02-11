from zlapi.models import *
import requests
import threading
from datetime import datetime, timedelta
from config import PREFIX  # ✅ Lấy prefix từ config.py

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Chat cùng sim",
    'power': "Thành viên"
}

# ====== Cấu hình ======
SIMSIMI_API_KEY = "GZyOSYF-1Pr5bDnMZ-ng2bNQVbkvtH1OeJyNBjoi"
SIMSIMI_API_URL = "https://wsapi.simsimi.com/190410/talk"
last_message_times = {}


# ====== Hàm gọi API SimSimi ======
def get_simsimi_reply(chat_message: str) -> str:
    try:
        response = requests.post(
            SIMSIMI_API_URL,
            json={
                "utext": chat_message,
                "lang": "vn",
                "atext_bad_prob_max": 0.7,
            },
            headers={
                "Content-Type": "application/json",
                "x-api-key": SIMSIMI_API_KEY,
            },
            timeout=10,
        )

        data = response.json()
        reply = data.get("atext")

        if not reply:
            raise ValueError("Không nhận được phản hồi từ SimSimi")

        return reply.strip()

    except Exception as e:
        print(f"[SimSimi Error] {e}")
        return "😓 Xin lỗi, tôi không thể trả lời lúc này. Vui lòng thử lại sau."


# ====== Xử lý lệnh sim ======
def handle_sim_command(message, message_object, thread_id, thread_type, author_id, client):
    user_message = message.strip()

    # Chỉ xử lý khi có prefix !sim
    if not user_message.lower().startswith(f"{PREFIX}sim "):
        return

    # Lấy nội dung người dùng gửi
    chat_content = user_message[len(f"{PREFIX}sim "):].strip()
    if not chat_content:
        client.replyMessage(
            Message(text=f"❗ Vui lòng nhập nội dung.\nVí dụ: {PREFIX}sim Xin chào!"),
            thread_id=thread_id,
            thread_type=thread_type,
            ttl=60000,
            replyMsg=message_object
        )
        return

    # Chống spam (mỗi người 2s mới được gửi tiếp)
    now = datetime.now()
    if author_id in last_message_times and (now - last_message_times[author_id]) < timedelta(seconds=2):
        return
    last_message_times[author_id] = now

    # Chạy trong luồng riêng để không chặn bot
    threading.Thread(target=simsimi_thread,
                     args=(chat_content, message_object, thread_id, thread_type, client)).start()


# ====== Hàm gửi request SimSimi trong luồng ======
def simsimi_thread(chat_content, message_object, thread_id, thread_type, client):
    reply = get_simsimi_reply(chat_content)
    if not reply:
        reply = "🤖 SimSimi không có câu trả lời."
    client.replyMessage(
        Message(text=f"💬 Sim: {reply}"),
        thread_id=thread_id,
        thread_type=thread_type,
        ttl=60000,
        replyMsg=message_object
    )


# ====== Đăng ký module ======
def TQD():
    return {"sim": handle_sim_command}
