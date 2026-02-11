from zlapi.models import Message, ZaloAPIException, MultiMsgStyle, MessageStyle
from config import ADMIN, IMEI

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Lệnh rời nhóm",
    'power': "Admin"
}

def handle_leave_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        msg = "Bạn không có quyền sử dụng lệnh này! Chỉ có admin Latte mới được sử dụng lệnh này"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(msg), style="font", size="10", auto_format=False),
        ])
        client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=60000)
        return

    try:
        # --- Gửi tin nhắn trước khi rời ---
        leave_text = "T Q D\n➜👋 Tạm biệt mọi người!\nHẹn gặp lại vào một ngày đẹp trời"
        leave_styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len("T Q D"), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len("T Q D"), style="bold", size="20", auto_format=False)
        ])
        client.sendMessage(
            Message(text=leave_text, style=leave_styles),
            thread_id,
            thread_type,
            ttl=20000
        )

        
        

        # --- Rời nhóm ---
        client.leaveGroup(thread_id, imei=IMEI)

    except ZaloAPIException as e:
        msg = f"err: {e}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(msg), style="font", size="10", auto_format=False),
        ])
        client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=60000)
    except Exception as e:
        msg = f"error: {e}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(msg), style="font", size="10", auto_format=False),
        ])
        client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=60000)


def TQD():
    return {
        'leave': handle_leave_command
    }
