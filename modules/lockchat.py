from zlapi.models import Message
from config import ADMIN
import json

# Mô tả module
des = {
    'version': "2.0.2",
    'credits': "Latte",
    'description': "Bật tắt chat",
    'power': "Admin",
}

# Hàm tạo style cho tin nhắn
def styled(text, b=True, i=True, color="15a85f", size=15):
    styles = [{
        "start": 0,
        "len": len(text) + 1,
        "st": ",".join(filter(None, [
            "b" if b else "",
            "i" if i else "",
            f"c_{color}",
            f"f_{size}"
        ]))
    }]
    return json.dumps({"styles": styles, "ver": 0})

# Lệnh khoachat → khóa chat
def khoachat(message, message_object, thread_id, thread_type, author_id, client, ADMIN=ADMIN):
    if str(author_id) not in ADMIN:
        client.replyMessage(
            Message(text="• Bạn Không Có Quyền!"),
            message_object, thread_id, thread_type, ttl=60000
        )
        return

    client.changeGroupSetting(thread_id, lockSendMsg=1)
    text = "🔒 Nhóm đã khoá chat"
    style = styled(text, color="db342e")
    client.replyMessage(
        Message(text=text, style=style),
        message_object, thread_id, thread_type, ttl=60000
    )

# Lệnh mochat → mở chat
def mochat(message, message_object, thread_id, thread_type, author_id, client, ADMIN=ADMIN):
    if str(author_id) not in ADMIN:
        client.replyMessage(
            Message(text="• Bạn Không Có Quyền!"),
            message_object, thread_id, thread_type, ttl=60000
        )
        return

    client.changeGroupSetting(thread_id, lockSendMsg=0)
    text = "🔓 Nhóm đã mở chat"
    style = styled(text, color="15a85f")
    client.replyMessage(
        Message(text=text, style=style),
        message_object, thread_id, thread_type, ttl=60000
    )

# Hàm trả về dict các lệnh
def TQD():
    return {
        'khoachat': khoachat,
        'mochat': mochat
    }
