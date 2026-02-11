import json
import time
import threading
from zlapi.models import Message, Mention, MultiMsgStyle, MessageStyle
import logging
from config import PREFIX

logging.basicConfig(level=logging.DEBUG)

with open('seting.json', 'r') as f:
    settings = json.load(f)

ADMIN_ID = settings['admin']

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "var 36 thanh hóa ăn rau má phá đường tàu 🤯🔥",
    'power': "Quản trị viên Bot"
}

is_var_running = False

def stop_var(client, message_object, thread_id, thread_type):
    global is_var_running
    is_var_running = False
    if message_object:
        client.replyMessage(Message(text="🚨 Success!"), message_object, thread_id, thread_type, ttl=30000)
    else:
        client.send(Message(text="🚨 Success!"), thread_id, thread_type, ttl=30000)

def check_admin_permissions(author_id, creator_id, admin_ids):
    all_admin_ids = set(admin_ids)
    all_admin_ids.add(str(creator_id))
    all_admin_ids.add(str(ADMIN_ID))
    return str(author_id) in all_admin_ids

def send_error_message(client, thread_id, thread_type, error_message):
    client.send(Message(text=error_message), thread_id, thread_type, ttl=30000)

def handle_var_command(message, message_object, thread_id, thread_type, author_id, client):
    global is_var_running
    command_parts = message.split()
    if len(command_parts) < 2:
        if message_object:
            client.replyMessage(Message(text=f"🚦 sai cú pháp dùng {PREFIX}var on/off"), message_object, thread_id, thread_type, ttl=30000)
        else:
            client.send(Message(text=f"🚦 sai cú pháp dùng {PREFIX}var on/off"), thread_id, thread_type, ttl=30000)
        return
        
    group_info = client.fetchGroupInfo(thread_id)
    if not group_info or thread_id not in group_info.gridInfoMap:
        send_error_message(client, thread_id, thread_type, "🚦 ❌️ Không thể var tin nhắn riêng.")
        return
    group_data = group_info.gridInfoMap[thread_id]
    creator_id = group_data.get('creatorId')
    admin_ids = group_data.get('adminIds', [])
    if not check_admin_permissions(author_id, creator_id, admin_ids):
        send_error_message(client, thread_id, thread_type, "🚦 Chỉ admin mới có thể sử dụng.")
        return
    
    action = command_parts[1].lower()

    if action == "off":
        if not is_var_running:
            if message_object:
                client.replyMessage(Message(text="🚦 Hiện tại không có var nào đang chạy!"), message_object, thread_id, thread_type, ttl=30000)
            else:
                client.send(Message(text="🚦 Hiện tại không có var nào đang chạy!"), thread_id, thread_type, ttl=30000)
        else:
            stop_var(client, message_object, thread_id, thread_type)
        return

    if action != "on":
        if message_object:
            client.replyMessage(Message(text=f"🚦 sai cú pháp dùng {PREFIX}var on/off"), message_object, thread_id, thread_type, ttl=30000)
        else:
            client.send(Message(text=f"🚦 sai cú pháp dùng {PREFIX}var on/off"), thread_id, thread_type, ttl=30000)
        return
    
    try:
        with open("spam/lag.txt", "r", encoding="utf-8") as file:
            Ngon = file.readlines()
    except FileNotFoundError:
        send_error_message(client, thread_id, thread_type, "🚦 Không tìm thấy tệp noidung.txt")
        return
    except Exception as e:
        send_error_message(client, thread_id, thread_type, f"🚦 Lỗi khi đọc tệp: {e}")
        return
    if not Ngon:
        send_error_message(client, thread_id, thread_type, "🚦 Tệp nội dung rỗng")
        return
    
    is_var_running = True
    def var_loop():
        while is_var_running:
            for noidung in Ngon:
                if not is_var_running:
                    break
                noidung = noidung.strip()
                mention = Mention("-1", length=len(noidung), offset=0)
                styles = MultiMsgStyle([
                    MessageStyle(offset=0, length=100000, style="font", size="10000000", auto_format=False),
                    MessageStyle(offset=0, length=10000, style="bold", size="10000000", auto_format=False),                
                    MessageStyle(offset=0, length=10000, style="color", color="#db342e", auto_format=False),
                ])
                client.send(Message(text=noidung, mention=mention, style=styles), thread_id, thread_type)
                time.sleep(0.3)
    
    var_thread = threading.Thread(target=var_loop)
    var_thread.start()
    
def TQD():
    return {
        'var': handle_var_command
    }