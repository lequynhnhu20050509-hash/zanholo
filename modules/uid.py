from zlapi.models import *

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Lấy id zalo người dùng hoặc id người được tag",
    'power': "Thành viên"
}

def get_uid(bot, message_object, author_id, thread_id, thread_type, message_text):
    """
    - Nếu có tag → UID người được tag
    - Nếu 'me' → UID chính mình
    - Nếu chat riêng → UID người đối phương
    - Còn lại → UID người gửi
    """
    msg = message_text.strip().lower()

    # Nếu có tag
    if message_object.mentions:
        return message_object.mentions[0]['uid']

    # Nếu người dùng gõ 'me'
    if msg.endswith("me"):
        return author_id

    # Nếu là chat riêng (1:1)
    if thread_type == ThreadType.USER:
        return thread_id  # chỉ UID đối phương

    # Mặc định
    return author_id


# --- Lấy tên người dùng theo UID ---
def get_user_name_by_id(bot, user_id):
    try:
        info = bot.fetchUserInfo(user_id)
        if hasattr(info, "changed_profiles") and user_id in info.changed_profiles:
            profile = info.changed_profiles[user_id]
            return getattr(profile, "zaloName", None) or getattr(profile, "displayName", "Unknown User")
        return "Unknown User"
    except Exception:
        return "Unknown User"


def handle_meid_command(message, message_object, thread_id, thread_type, author_id, client):
    # tách nội dung lệnh, ví dụ "-uid me"
    parts = message.strip().split(" ", 1)
    arg = parts[1] if len(parts) > 1 else ""

    uid = get_uid(client, message_object, author_id, thread_id, thread_type, arg)
    name = get_user_name_by_id(client, uid)

    reply = Message(
        text=f"👤 Tên: {name}\n🆔 UID: {uid}"
    )
    client.replyMessage(reply, message_object, thread_id, thread_type, ttl=60000)


def TQD():
    return {
        'uid': handle_meid_command
    }
