import json
import sys
import os
from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import ADMIN

des = {
    'version': '2.0.1',
    'credits': "Latte",
    'description': 'Đổi prefix',
    'power': 'Quản trị viên Bot'
}

def is_admin(author_id):
    return author_id == ADMIN

def prf():
    with open('seting.json', 'r') as f:
        return json.load(f).get('prefix')

def set_new_prefix(new_prefix):
    with open('seting.json', 'r') as f:
        data = json.load(f)

    data['prefix'] = new_prefix

    with open('seting.json', 'w') as f:
        json.dump(data, f, indent=4)

def handle_setprefix_command(message, message_object, thread_id, thread_type, author_id, client):
    styles = MultiMsgStyle([
        MessageStyle(offset=0, length=10000, style="font", size="10", auto_format=False),
    ])

    if not is_admin(author_id):
        response_message = "🚨 Bạn không đủ quyền hạn để sử dụng lệnh này."
        client.replyMessage(Message(text=response_message, style=styles), message_object, thread_id, thread_type, ttl=30000)
        return

    text = message.split()

    if len(text) < 2:
        error_message = "🚨 Vui lòng nhập prefix mới."
        client.sendMessage(Message(text=error_message, style=styles), thread_id, thread_type, ttl=30000)
        return

    new_prefix = text[1]
    set_new_prefix(new_prefix)

    success_message = f"🚨 Đã đổi prefix thành: {new_prefix}. Đang khởi động lại hệ thống..."
    client.replyMessage(Message(text=success_message, style=styles), message_object, thread_id, thread_type, ttl=10000)

    try:
        client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
        python = sys.executable
        os.execl(python, python, *sys.argv)
    except Exception as e:
        error_message = f"🚨 Lỗi xảy ra khi khởi động lại hệ thống: {str(e)}"
        client.replyMessage(Message(text=error_message, style=styles), message_object, thread_id, thread_type, ttl=30000)

def TQD():
    return {
        'prefix': handle_setprefix_command
    }