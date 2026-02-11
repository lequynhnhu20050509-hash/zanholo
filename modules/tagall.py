from zlapi.models import Message, Mention
from config import ADMIN

des = {
    'version': "5.0.1",
    'credits': "Latte",
    'description': "Thông báo cho nhóm",
    'power': "Admin"
}

def handle_tagall_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        client.replyMessage(
            Message(text="🚫 Bạn không có quyền để thực hiện điều này! Chỉ có admin Latte mới được sử dụng lệnh này"),
            message_object, thread_id, thread_type,ttl=20000
        )
        return

    noidung = message.split()
    
    if len(noidung) < 2:
        error_message = Message(text="Vui lòng nhập nội dung cần thông báo.")
        client.sendMessage(error_message, thread_id, thread_type,ttl=20000)
        return

    noidung1 = " ".join(noidung[1:])
    mention = Mention("-1", length=len(noidung1), offset=0)

    content = f"{noidung1}"
    
    client.replyMessage(
        Message(
            text=content, mention=mention
        ),
        message_object,
        thread_id=thread_id,
        thread_type=thread_type,ttl=60000
    )

def TQD():
    return {
        'all': handle_tagall_command
    }
