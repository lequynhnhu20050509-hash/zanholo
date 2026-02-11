import os
import time
import json
import random
import threading
from zlapi.models import Message, ThreadType
from config import ADMIN

# ================== Thông tin mô-đun ==================
des = {
    'version': "3.1.0",
    'credits': "Latte",
    'description': "Sticker lag",
    'power': "Admin"
}

# ================== Dữ liệu sticker ==================
stickers = [
    {"sticker_type": 7, "sticker_id": str(i), "category_id": "10746"}
    for i in range(23339, 23352)
]

# ================== Biến điều khiển ==================
delay_time = 1.0
stklag_running = False
stklag_thread = None
RUNNING_FILE = "stklag_running.json"

# ================== Hỗ trợ đọc/ghi nhóm đang chạy ==================
def save_running(thread_id, thread_type):
    data = {"thread_id": thread_id, "thread_type": str(thread_type)}
    with open(RUNNING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Đã lưu nhóm đang chạy: {thread_id}")

def clear_running():
    if os.path.exists(RUNNING_FILE):
        os.remove(RUNNING_FILE)
        print("Đã xoá file stklag_running.json cũ")

def load_running():
    if not os.path.exists(RUNNING_FILE):
        return None
    try:
        with open(RUNNING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

# ================== Luồng gửi sticker ==================
def send_stickers_loop(client, thread_id, thread_type):
    global stklag_running, delay_time
    while stklag_running:
        sticker = random.choice(stickers)
        try:
            client.sendSticker(
                sticker["sticker_type"],
                sticker["sticker_id"],
                sticker["category_id"],
                thread_id,
                thread_type,
                ttl=60000
            )
        except Exception as e:
            print(f"Lỗi gửi sticker: {e}")
        time.sleep(delay_time)
    print("⛔ Luồng gửi sticker đã dừng.")

# ================== Auto restart ==================
def auto_restart_stklag(client):
    global stklag_running, stklag_thread
    data = load_running()
    if not data:
        print("Không có nhóm nào đang chạy stklag.")
        return
    try:
        thread_id = data["thread_id"]
        type_str = data["thread_type"].split(".")[-1]
        thread_type = ThreadType[type_str]
        print(f"Tự khởi chạy lại STKLAG cho nhóm {thread_id}")
        stklag_running = True
        stklag_thread = threading.Thread(
            target=send_stickers_loop, args=(client, thread_id, thread_type)
        )
        stklag_thread.start()
    except Exception as e:
        print(f"Lỗi auto restart STKLAG: {e}")

# ================== Xử lý lệnh ==================
def handle_stklag_command(message, message_object, thread_id, thread_type, author_id, client):
    global delay_time, stklag_running, stklag_thread

    # Kiểm tra quyền
    if author_id not in ADMIN:
        client.sendMessage(Message(text="❌ Bạn không có quyền dùng lệnh này."), thread_id, thread_type, ttl=15000)
        return

    args = message.strip().split()
    if len(args) == 1:
        status = "🟢 Đang chạy" if stklag_running else "🔴 Đã dừng"
        client.sendMessage(Message(text=f"⚙️ Sticker lag: {status}\n⏱ Delay: {delay_time}s"), thread_id, thread_type, ttl=15000)
        return

    cmd = args[1].lower()

    # SET
    if cmd == "set" and len(args) >= 3:
        try:
            delay_time = float(args[2])
            client.sendMessage(Message(text=f"✅ Delay đặt thành {delay_time}s"), thread_id, thread_type, ttl=15000)
        except:
            client.sendMessage(Message(text="⚠️ Dùng: stklag set <số giây>"), thread_id, thread_type, ttl=15000)
        return

    # ON
    if cmd == "on":
        if stklag_running:
            client.sendMessage(Message(text="⚠️ Sticker lag đang chạy rồi."), thread_id, thread_type, ttl=15000)
            return
        stklag_running = True
        clear_running()
        save_running(thread_id, thread_type)
        client.sendMessage(Message(text=f"🚀 Bắt đầu gửi sticker mỗi {delay_time}s..."), thread_id, thread_type, ttl=15000)
        stklag_thread = threading.Thread(target=send_stickers_loop, args=(client, thread_id, thread_type))
        stklag_thread.start()
        return

    # STOP
    if cmd == "stop":
        if not stklag_running:
            client.sendMessage(Message(text="ℹ️ Sticker lag chưa bật."), thread_id, thread_type, ttl=15000)
            return
        stklag_running = False
        clear_running()
        client.sendMessage(Message(text="🛑 Đã dừng gửi sticker."), thread_id, thread_type, ttl=15000)
        return

    # INFO
    if cmd == "info":
        info = (
            f"📘 Thông tin sticker lag\n"
            f"Phiên bản: {des['version']}\n"
            f"Tác giả: {des['description']}\n"
            f"Trạng thái: {'🟢 Đang chạy' if stklag_running else '🔴 Dừng'}\n"
            f"Delay: {delay_time}s\n"
            f"Số lượng sticker: {len(stickers)}\n"
            f"Lệnh: stklag on / stop / set <số> / info"
        )
        client.sendMessage(Message(text=info), thread_id, thread_type, ttl=15000)
        return

    # Không hợp lệ
    client.sendMessage(Message(text="⚙️ Lệnh không hợp lệ. Dùng: on / stop / set / info"), thread_id, thread_type, ttl=15000)

# ================== Export ==================
def TQD():
    return {'stklag': handle_stklag_command}
