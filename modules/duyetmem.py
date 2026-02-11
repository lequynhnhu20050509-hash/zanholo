from zlapi.models import Message, MessageStyle, MultiMsgStyle
from config import ADMIN, PREFIX
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Duyệt tất cả thành viên",
    'power': "Quản trị viên Bot"
}

def get_user_name(client, uid):
    try:
        user_info = client.fetchUserInfo(uid)
        author_info = user_info.changed_profiles.get(str(uid), {}) if user_info and user_info.changed_profiles else {}
        name = author_info.get('zaloName', 'Không xác định')
        return name
    except Exception as e:
        logging.error(f"[get_user_name] Failed to fetch name for user {uid}: {e}")
        return 'Không xác định'

def show_menu():
    return (
        "🗝 QUẢN LÝ DUYỆT MEM CỦA LATTE 🗝\n"
        "━━━━━━━━━━━━━━━\n"
        "📜 Hướng dẫn cho Đại ca:\n"
        f"• Cú pháp: {PREFIX}duyetmem <lệnh>\n"
        "• Chỉ Đại ca (Quản trị viên Bot/Nhóm) dùng được nha 😎\n"
        "━━━━━━━━━━━━━━━\n"
        "📋 Lệnh của Đại ca:\n"
        f"• {PREFIX}duyetmem all: Duyệt hết thành viên đang chờ\n"
        f"• {PREFIX}duyetmem list: Xem số thành viên đang chờ duyệt\n"
        "━━━━━━━━━━━━━━━\n"
        "⚠️ Lưu ý: Nhập đúng lệnh kẻo lộn nha Đại ca!"
    )

def handle_duyetmem_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        name = get_user_name(client, author_id)

        group_info = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        creator_id = group_info.get('creatorId')
        admin_ids = group_info.get('adminIds', [])

        if admin_ids is None:
            admin_ids = []

        all_admin_ids = set(admin_ids)
        all_admin_ids.add(creator_id)
        all_admin_ids.update(ADMIN)

        if author_id not in all_admin_ids:
            rest_text = "🚫 Đại ca ơi, có người dám dùng lệnh của Đại ca 😤"
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            ])
            client.replyMessage(
                Message(text=msg, style=styles),
                message_object, thread_id, thread_type, ttl=12000
            )
            client.sendReaction(message_object, "❌", thread_id, thread_type, reactionType=75)
            return

        command_parts = message.strip().split()

        if len(command_parts) < 2 or command_parts[1].lower() == "help":
            rest_text = show_menu()
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            ])
            client.replyMessage(
                Message(text=msg, style=styles),
                message_object, thread_id, thread_type, ttl=120000
            )
            client.sendReaction(message_object, "ℹ️", thread_id, thread_type, reactionType=75)
            return

        action = command_parts[1].lower()

        pending_members = group_info.pendingApprove.get('uids', [])

        if action == "list":
            if not pending_members:
                rest_text = "🚫 Đại ca ơi, hiện không có ai chờ duyệt cả!"
                msg = f"{name}\n➜{rest_text}"
                styles = MultiMsgStyle([
                    MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                    MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
                ])
                client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=12000
                )
                client.sendReaction(message_object, "🚫", thread_id, thread_type, reactionType=75)
            else:
                rest_text = f"🔍 Đại ca, có {len(pending_members)} thành viên đang chờ duyệt nè!"
                msg = f"{name}\n➜{rest_text}"
                styles = MultiMsgStyle([
                    MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                    MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
                ])
                client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=40000
                )
                client.sendReaction(message_object, "🔍", thread_id, thread_type, reactionType=75)

        elif action == "all":
            if not pending_members:
                rest_text = "🚫 Đại ca ơi, hiện không có ai chờ duyệt cả!"
                msg = f"{name}\n➜{rest_text}"
                styles = MultiMsgStyle([
                    MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                    MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
                ])
                client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=12000
                )
                client.sendReaction(message_object, "🚫", thread_id, thread_type, reactionType=75)
                return

            for member_id in pending_members:
                if hasattr(client, 'handleGroupPending'):
                    client.handleGroupPending(member_id, thread_id)
                else:
                    break
                    
            rest_text = "✅ Đại ca, đã duyệt hết đám thành viên đang chờ!"
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            ])
            client.replyMessage(
                Message(text=msg, style=styles),
                message_object, thread_id, thread_type, ttl=60000
            )
            client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

        else:
            rest_text = f"❌ Đại ca ơi, lệnh sai rồi! Nhập lại nha: {PREFIX}duyetmem [all|list]"
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            ])
            client.replyMessage(
                Message(text=msg, style=styles),
                message_object, thread_id, thread_type, ttl=12000
            )
            client.sendReaction(message_object, "❌", thread_id, thread_type, reactionType=75)

    except Exception as e:
        logging.error(f"[handle_duyetmem_command] Error: {e}")
        rest_text = f"⚠️ Đại ca ơi, có lỗi xảy ra: {e}"
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
        ])
        client.replyMessage(
            Message(text=msg, style=styles),
            message_object, thread_id, thread_type, ttl=12000
        )
        client.sendReaction(message_object, "⚠️", thread_id, thread_type, reactionType=75)

def TQD():
    return {
        'duyetmem': handle_duyetmem_command
    }