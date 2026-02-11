import threading
import time
from zlapi.models import Message, ThreadType, MultiMsgStyle, MessageStyle
from config import PREFIX, ADMIN
import logging

logger = logging.getLogger(__name__)

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Spam cuộc gọi đến người dùng (qua tag hoặc ID).",
    'power': "Admin"
}

spamcall_tasks = {}

def get_user_name(client, uid):
    try:
        info = client.fetchUserInfo(uid)
        return info.changed_profiles.get(str(uid), {}).get('zaloName', str(uid))
    except Exception as e:
        logger.error(f"[get_user_name] Failed to fetch name for user {uid}: {e}")
        return str(uid)

def _call_loop(client, targets, count, stop_event, message_object, thread_id, thread_type, author_name):
    task_id = stop_event
    print(f"[SpamCall] Bắt đầu tác vụ cho: {[name for _, name in targets]}")
    
    for i in range(count):
        if stop_event.is_set():
            print(f"[SpamCall] Tác vụ cho {[name for _, name in targets]} đã bị dừng sớm.")
            break
        for target_id, target_name in targets:
            if stop_event.is_set(): break
            try:
                call_id = client.TaoIDCall()
                print(f"[SpamCall] Đang gọi {target_name} (lần {i+1}/{count})")
                client.sendCall(target_id, call_id)
                time.sleep(1.5)
            except Exception as e:
                print(f"[SpamCall] Lỗi khi gọi {target_name}: {e}")
    
    if not stop_event.is_set():
        targets_str = ", ".join([name for _, name in targets])
        rest_text = f"✅ Đã hoàn tất {count} cuộc gọi đến {targets_str}."
        msg = f"{author_name}\n➜{rest_text}"
        styles = MultiMsgStyle([MessageStyle(offset=0, length=len(author_name), style="color", color="#db342e", auto_format=False), MessageStyle(offset=0, length=len(author_name), style="bold", auto_format=False)])
        client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=60000)
    
    if thread_id in spamcall_tasks and task_id in spamcall_tasks[thread_id]:
        spamcall_tasks[thread_id].remove(task_id)
        if not spamcall_tasks[thread_id]: del spamcall_tasks[thread_id]

def handle_spamcall_command(message, message_object, thread_id, thread_type, author_id, client):
    name = get_user_name(client, author_id)

    if str(author_id) not in ADMIN:
        rest_text = "⚠️ Bạn không có quyền sử dụng lệnh này. Chỉ có admin Latte mới được sử dụng lệnh này"
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False), MessageStyle(offset=0, length=len(name), style="bold", auto_format=False)])
        client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=60000)
        return

    parts = message.split()
    if len(parts) < 2:
        rest_text = f"❌ Sai cú pháp!\nDùng: {PREFIX}call [số lần] [@user | id1 id2...]\nHoặc: {PREFIX}call off"
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False), MessageStyle(offset=0, length=len(name), style="bold", auto_format=False)])
        client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=60000)
        return

    command_action = parts[1].lower()

    if command_action == 'off':
        if thread_id in spamcall_tasks and spamcall_tasks[thread_id]:
            tasks_to_stop = list(spamcall_tasks[thread_id])
            for stop_event in tasks_to_stop: stop_event.set()
            if thread_id in spamcall_tasks: del spamcall_tasks[thread_id]
            rest_text = f"🚫 Đã gửi yêu cầu dừng {len(tasks_to_stop)} tác vụ spam call trong nhóm này."
        else:
            rest_text = "⚠️ Không có tác vụ spam call nào đang chạy trong nhóm này."
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False), MessageStyle(offset=0, length=len(name), style="bold", auto_format=False)])
        client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=60000)
        return
        
    try:
        spam_count = int(parts[1])
        if not (1 <= spam_count <= 200): raise ValueError
    except ValueError:
        rest_text = "❌ Số lần gọi phải là một số từ 1 đến 200."
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False), MessageStyle(offset=0, length=len(name), style="bold", auto_format=False)])
        client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=60000)
        return

    target_ids = []
    if message_object.mentions:
        target_ids = [m.uid for m in message_object.mentions]
    elif len(parts) > 2:
        target_ids = [p for p in parts[2:] if p.isdigit()]
    
    if not target_ids:
        rest_text = "❌ Vui lòng tag hoặc cung cấp ít nhất một ID người dùng hợp lệ!"
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False), MessageStyle(offset=0, length=len(name), style="bold", auto_format=False)])
        client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=60000)
        return
    
    targets = [(uid, get_user_name(client, uid)) for uid in target_ids]

    targets_str = ", ".join([t_name for _, t_name in targets])
    rest_text = f"📞 Bắt đầu tác vụ thực hiện {spam_count} cuộc gọi đến {targets_str}!"
    msg = f"{name}\n➜{rest_text}"
    styles = MultiMsgStyle([MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False), MessageStyle(offset=0, length=len(name), style="bold", auto_format=False)])
    client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=60000)

    stop_event = threading.Event()
    if thread_id not in spamcall_tasks: spamcall_tasks[thread_id] = []
    spamcall_tasks[thread_id].append(stop_event)

    call_thread = threading.Thread(
        target=_call_loop,
        args=(client, targets, spam_count, stop_event, message_object, thread_id, thread_type, name),
        daemon=True
    )
    call_thread.start()

def TQD():
    return {'call': handle_spamcall_command}