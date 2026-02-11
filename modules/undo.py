import json
from zlapi.models import *
from zlapi import Message, ThreadType
from config import PREFIX, ADMIN

des = {
    'version': "3.2.0",
    'credits': "Latte",
    'description': "Thu hồi tin nhắn",
    'power': "Admin"
}


# ==========================
# 🔹 UNDO REPLY
# ==========================
def handle_undo_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        client.replyMessage(
            Message(text="🚫 Bạn không có quyền để thực hiện lệnh này!"),
            message_object, thread_id, thread_type, ttl=60000
        )
        return

    if not message_object.quote:
        client.replyMessage(
            Message(text=f"⚠️ Bạn phải reply vào tin nhắn cần thu hồi!\nCú pháp: {PREFIX}undo <reply tin nhắn>"),
            message_object, thread_id, thread_type, ttl=60000
        )
        return

    # Lấy thông tin tin nhắn được reply
    reply_msg = message_object.quote
    msg_id = getattr(reply_msg, "msgId", None) or getattr(reply_msg, "globalMsgId", None)
    cli_msg_id = getattr(reply_msg, "cliMsgId", None) or getattr(reply_msg, "localMsgId", None)

    # Fallback nếu globalMsgId = 0
    if not msg_id or msg_id == 0:
        try:
            recent = client.getRecentGroup(thread_id)
            messages = getattr(recent, "groupMsgs", [])
            for msg in messages:
                if str(msg.get("cliMsgId")) == str(cli_msg_id):
                    msg_id = msg.get("msgId") or msg.get("globalMsgId")
                    break
        except Exception as e:
            client.replyMessage(
                Message(text=f"⚠️ Không thể tra tin nhắn trong nhóm: {e}"),
                message_object, thread_id, thread_type, ttl=60000
            )
            return

    if not msg_id or not cli_msg_id:
        client.replyMessage(
            Message(text="⚠️ Không thể lấy thông tin tin nhắn được reply!"),
            message_object, thread_id, thread_type, ttl=60000
        )
        return

    try:
        result = client.undoMessage(
            msgId=msg_id,
            cliMsgId=cli_msg_id,
            thread_id=thread_id,
            thread_type=thread_type
        )
        if result:
            client.replyMessage(
                Message(text="✅ Đã thu hồi tin nhắn được reply."),
                message_object, thread_id, thread_type, ttl=60000
            )
        else:
            client.replyMessage(
                Message(text="⚠️ Không thể thu hồi tin nhắn được reply."),
                message_object, thread_id, thread_type, ttl=60000
            )
    except Exception as e:
        client.replyMessage(
            Message(text=f"🐞 Lỗi khi thu hồi tin nhắn reply: {e}"),
            message_object, thread_id, thread_type, ttl=60000
        )


# ==========================
# 🔹 UNDO ALL
# ==========================
def handle_undoall_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        client.replyMessage(
            Message(text="🚫 Bạn không có quyền để thực hiện lệnh này!"),
            message_object, thread_id, thread_type, ttl=60000
        )
        return

    num_to_undo = 100  # có thể tùy chỉnh số lượng thu hồi
    undone_count = 0
    failed_count = 0

    try:
        # Lấy tin nhắn theo thread
        if thread_type == ThreadType.GROUP:
            data = client.getRecentGroup(thread_id)
            messages = getattr(data, "groupMsgs", [])
        elif thread_type == ThreadType.USER:
            data = client.getRecentGroup(thread_id)
            messages = getattr(data, "groupMsgs", [])
        else:
            client.replyMessage(
                Message(text="❌ Loại thread không hợp lệ!"),
                message_object, thread_id, thread_type, ttl=60000
            )
            return

        if not messages:
            client.replyMessage(
                Message(text="⚠️ Không có tin nhắn nào để thu hồi!"),
                message_object, thread_id, thread_type, ttl=60000
            )
            return

        if len(messages) < num_to_undo:
            num_to_undo = len(messages)

        for i in range(num_to_undo):
            msg = messages[-(i + 1)]
            msg_id = msg.get("msgId") or msg.get("globalMsgId")
            cli_msg_id = msg.get("cliMsgId") or msg.get("localMsgId")
            if not msg_id or not cli_msg_id:
                failed_count += 1
                continue
            try:
                result = client.undoMessage(
                    msgId=msg_id,
                    cliMsgId=cli_msg_id,
                    thread_id=thread_id,
                    thread_type=thread_type
                )
                if result:
                    undone_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1

    except Exception as e:
        client.replyMessage(
            Message(text=f"⚠️ Lỗi khi lấy tin nhắn: {e}"),
            message_object, thread_id, thread_type, ttl=60000
        )
        return

    # Gửi kết quả
    if failed_count > 0:
        client.replyMessage(
            Message(text=f"🚦 Đã thu hồi {undone_count} tin nhắn. Không thể thu hồi {failed_count} tin."),
            message_object, thread_id, thread_type, ttl=60000
        )
    else:
        client.replyMessage(
            Message(text=f"✅ Đã thu hồi {undone_count} tin nhắn thành công!"),
            message_object, thread_id, thread_type, ttl=60000
        )


# ==========================
# 🔹 ĐĂNG KÝ LỆNH
# ==========================
def TQD():
    return {
        "undo": handle_undo_command,      # Reply tin nhắn → thu hồi 1 tin
        "undoall": handle_undoall_command # Thu hồi toàn bộ tin nhắn gần nhất
    }
