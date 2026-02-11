from zlapi.models import *
from zlapi import Message, ThreadType
from config import PREFIX, ADMIN

des = {
    'version': "2.3.0",
    'credits': "Latte",
    'description': "Xoá tin nhắn theo số lượng hoặc xoá của chính admin",
    'power': "Admin"
}

def handle_delmsg_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        client.replyMessage(Message(text="🚫 Bạn không có quyền thực hiện lệnh này!"), message_object, thread_id, thread_type, ttl=60000)
        return

    parts = message.split()
    if len(parts) < 2:
        client.replyMessage(Message(text=f"⚠️ Cú pháp: {PREFIX}delmsg <số lượng> [all]"), message_object, thread_id, thread_type, ttl=60000)
        return

    try:
        num_to_delete = int(parts[1])
        if num_to_delete <= 0:
            raise ValueError
    except ValueError:
        client.replyMessage(Message(text="⚠️ Số lượng không hợp lệ!"), message_object, thread_id, thread_type, ttl=60000)
        return

    delete_all = len(parts) > 2 and parts[2].lower() == "all"

    try:
        group_data = client.getRecentGroup(thread_id)
        messages = getattr(group_data, "groupMsgs", [])
        if not messages:
            client.replyMessage(Message(text="⚠️ Không có tin nhắn nào để xóa!"), message_object, thread_id, thread_type, ttl=60000)
            return
    except Exception as e:
        client.replyMessage(Message(text=f"⚠️ Lỗi khi lấy tin nhắn: {e}"), message_object, thread_id, thread_type, ttl=60000)
        return

    deleted_count = 0
    failed_count = 0

    for msg in reversed(messages):
        if deleted_count >= num_to_delete:
            break

        msg_user_id = str(msg['uidFrom']) if msg['uidFrom'] != '0' else author_id

        # Nếu không phải "all", chỉ xóa tin của admin
        if not delete_all:
            if msg_user_id != str(author_id):
                continue

        try:
            deleted_msg = client.deleteGroupMsg(msg['msgId'], msg_user_id, msg['cliMsgId'], thread_id)
            if deleted_msg.status == 0:
                deleted_count += 1
            else:
                failed_count += 1
        except:
            failed_count += 1

    client.replyMessage(
        Message(text=f"🚦 Đã xóa {deleted_count} tin nhắn. {'Không thể xóa ' + str(failed_count) + ' tin nhắn.' if failed_count else ''}"),
        message_object, thread_id, thread_type, ttl=60000
    )


def TQD():
    return {
        'delmsg': handle_delmsg_command
    }
