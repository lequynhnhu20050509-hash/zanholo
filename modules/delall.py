from zlapi.models import *
from zlapi import Message, ThreadType
from config import PREFIX
from config import ADMIN

des = {
    'version': "2.1.0",
    'credits': "Latte",
    'description': "Xoá tin nhắn",
    'power': "Admin"
}

# ==========================
# 🔹 XOÁ TIN NHẮN REPLY
# ==========================
def handle_del_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        client.replyMessage(Message(text="🚫 Bạn không có quyền thực hiện lệnh này!"), message_object, thread_id, thread_type, ttl=60000)
        return

    if not message_object.quote:
        client.replyMessage(Message(text=f"⚠️ Bạn phải reply vào tin nhắn cần xoá.\nCú pháp: {PREFIX}del <reply tin nhắn>"), message_object, thread_id, thread_type, ttl=60000)
        return

    reply_msg = message_object.quote
    msg_id = getattr(reply_msg, "msgId", None) or getattr(reply_msg, "globalMsgId", None)
    cli_msg_id = getattr(reply_msg, "cliMsgId", None) or getattr(reply_msg, "localMsgId", None)
    user_id = getattr(reply_msg, "ownerId", author_id)

    if not msg_id or not cli_msg_id:
        # Fallback: dò lại trong group nếu globalMsgId = 0
        try:
            recent = client.getRecentGroup(thread_id)
            messages = getattr(recent, "groupMsgs", [])
            for msg in messages:
                if str(msg.get("cliMsgId")) == str(cli_msg_id):
                    msg_id = msg.get("msgId") or msg.get("globalMsgId")
                    user_id = msg.get("uidFrom") or author_id
                    break
        except Exception as e:
            client.replyMessage(Message(text=f"⚠️ Không thể tra tin nhắn: {e}"), message_object, thread_id, thread_type, ttl=60000)
            return

    if not msg_id or not cli_msg_id:
        client.replyMessage(Message(text="⚠️ Không thể lấy thông tin tin nhắn reply!"), message_object, thread_id, thread_type, ttl=60000)
        return

    try:
        deleted_msg = client.deleteGroupMsg(msg_id, user_id, cli_msg_id, thread_id)
        if deleted_msg.status == 0:
            client.replyMessage(Message(text="✅ Đã xoá tin nhắn được reply!"), message_object, thread_id, thread_type, ttl=60000)
        else:
            client.replyMessage(Message(text="⚠️ Không thể xoá tin nhắn này."), message_object, thread_id, thread_type, ttl=60000)
    except Exception as e:
        client.replyMessage(Message(text=f"🐞 Lỗi khi xoá tin nhắn reply: {e}"), message_object, thread_id, thread_type, ttl=60000)


# ==========================
# 🔹 XOÁ TẤT CẢ TIN NHẮN
# ==========================
def handle_go_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        noquyen = "Bạn không có quyền để thực hiện điều này!"
        client.replyMessage(Message(text=noquyen), message_object, thread_id, thread_type,ttl=60000)
        return

    num_to_delete = 100

    try:
        group_data = client.getRecentGroup(thread_id)

        if not group_data or not hasattr(group_data, 'groupMsgs'):
            client.replyMessage(Message(text="Không có tin nhắn nào để xóa!"), message_object, thread_id, thread_type,ttl=60000)
            return
        
        messages_to_delete = group_data.groupMsgs
        
        if not messages_to_delete:
            client.replyMessage(Message(text="Không có tin nhắn nào để xóa!"), message_object, thread_id, thread_type,ttl=60000)
            return

    except Exception as e:
        client.replyMessage(Message(text=f"Lỗi khi lấy tin nhắn: {str(e)}"), message_object, thread_id, thread_type,ttl=60000)
        return

    if len(messages_to_delete) < num_to_delete:
        
        num_to_delete = len(messages_to_delete)

    deleted_count = 0
    failed_count = 0

    for i in range(num_to_delete):
        msg = messages_to_delete[-(i + 1)]

        user_id = str(msg['uidFrom']) if msg['uidFrom'] != '0' else author_id
        try:
            deleted_msg = client.deleteGroupMsg(msg['msgId'], user_id, msg['cliMsgId'], thread_id)
            if deleted_msg.status == 0:
                deleted_count += 1
            else:
                failed_count += 1
        except Exception as e:
            failed_count += 1
            continue

    if failed_count > 0:
        client.replyMessage(
            Message(text=f"🚦Đã xóa {deleted_count} tin nhắn. Không thể xóa {failed_count} tin nhắn."),
            message_object, thread_id, thread_type,ttl=60000
        )
    else:
        client.replyMessage(Message(text=f"🚦Đã xóa {deleted_count} tin nhắn thành công!"), message_object, thread_id, thread_type,ttl=60000)


def TQD():
    return {
        'del': handle_del_command,   # Xoá tin nhắn reply
        'delall': handle_go_command  # Xoá toàn bộ tin nhắn gần nhất
    }
