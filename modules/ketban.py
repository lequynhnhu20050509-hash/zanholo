import re
import time
from zlapi import ZaloAPI
from zlapi.models import ThreadType, Message
from config import ADMIN

# Thông tin mô tả
des = {
    'version': "2.6.0",
    'credits': "Latte",
    'description': "Gửi kết bạn",
    'power': "Admin",
}

# 🧩 Lấy tên người dùng theo UID
def get_user_name_by_id(bot, user_id):
    try:
        info = bot.fetchUserInfo(user_id)
        if hasattr(info, "changed_profiles") and user_id in info.changed_profiles:
            profile = info.changed_profiles[user_id]
            return getattr(profile, "zaloName", None) or getattr(profile, "displayName", "Unknown User")
        return "Unknown User"
    except Exception:
        return "Unknown User"

# ⚙️ Xử lý lệnh kb
def handle_kb_command(message, message_object, thread_id, thread_type, author_id, client):
    # ✅ Chỉ admin mới dùng
    if author_id not in ADMIN:
        client.replyMessage(
            Message(text="🚫 Bạn không có quyền sử dụng lệnh này, Chỉ có admin Latte mới được sử dụng lệnh này 👑"),
            message_object, thread_id, thread_type
        )
        return

    parts = message.strip().split()
    args = parts[1:] if len(parts) > 1 else []

    # 🧩 Gửi kết bạn cho tất cả thành viên trong nhóm
    if len(args) == 1 and args[0].lower() == "all":
        try:
            group_info = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
            members = group_info.get('memVerList', [])
            total_members = len(members)
            success = 0

            for mem in members:
                try:
                    user_id = mem.split('_', 1)[0]
                    user_name = get_user_name_by_id(client, user_id)
                    msg_text = f"👋 Xin chào {user_name}! Tôi muốn kết bạn với bạn!"
                    client.sendFriendRequest(userId=user_id, msg=msg_text)
                    success += 1
                    time.sleep(0.5)
                except Exception as e:
                    print(f"⚠️ Lỗi khi gửi kết bạn cho {mem}: {e}")

            msg = (
                f"🎯 Hoàn tất gửi kết bạn!\n"
                f"👥 Tổng thành viên: {total_members}\n"
                f"✅ Thành công: {success}/{total_members}"
            )
            client.replyMessage(Message(text=msg), message_object, thread_id, thread_type, ttl=60000)

        except Exception as e:
            client.sendMessage(
                Message(text=f"💥 Lỗi khi gửi kết bạn hàng loạt: {str(e)} 😞"),
                thread_id, thread_type
            )
        return

    # 👥 Gửi kết bạn cho người được tag, reply hoặc chat riêng
    user_ids = []
    if getattr(message_object, "mentions", None):
        user_ids = [str(m.uid) for m in message_object.mentions]
    elif getattr(message_object, "quote", None):
        user_ids.append(str(message_object.quote.ownerId))
    elif thread_type == ThreadType.USER:
        # Chat riêng => đối phương là thread_id
        user_ids.append(str(thread_id))

    # Nếu không có ai => báo lỗi
    if not user_ids:
        client.sendMessage(
            Message(text="⚠️ Vui lòng @tag hoặc trả lời người cần kết bạn 👑"),
            thread_id, thread_type, ttl=20000
        )
        return

    success = 0
    user_names = []

    for uid in user_ids:
        try:
            user_name = get_user_name_by_id(client, uid)
            msg_text = f"👋 Xin chào {user_name}! Tôi muốn kết bạn với bạn 🌟"
            client.sendFriendRequest(userId=uid, msg=msg_text)
            success += 1
            user_names.append(user_name)
            time.sleep(0.5)
        except Exception as e:
            print(f"❌ Lỗi khi gửi kết bạn đến {uid}: {e}")

    # Thông báo kết quả
    if len(user_ids) == 1:
        # Chat riêng hoặc gửi 1 người
        text = f"✅ Đã gửi lời mời kết bạn đến {user_names[0]} 👑"
    else:
        # Gửi nhiều người
        text = f"✅ Đã gửi lời mời kết bạn đến {success}/{len(user_ids)} người 👑"

    client.sendMessage(
        Message(text=text),
        thread_id, thread_type, ttl=25000
    )

# 🔧 Đăng ký lệnh
def TQD():
    return {
        'kb': handle_kb_command
    }
