from config import ADMIN, PREFIX
from zlapi.models import *
import time
import json

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Xoá, chặn, mở bạn bè",
    'power': "Admin"
}


# 🧩 Hàm tiện ích: Lấy tên người dùng từ user_id
def get_user_name_by_id(bot, user_id):
    try:
        info = bot.fetchUserInfo(user_id)
        if hasattr(info, "changed_profiles") and user_id in info.changed_profiles:
            profile = info.changed_profiles[user_id]
            return getattr(profile, "zaloName", None) or getattr(profile, "displayName", "Unknown User")
        return "Unknown User"
    except Exception:
        return "Unknown User"


# 🚫 Chặn người dùng
def blockto(message, message_object, thread_id, thread_type, author_id, self):
    if author_id not in ADMIN:
        self.replyMessage(Message(text="🚦Bạn không có quyền sử dụng lệnh này. Chỉ có admin Latte mới được sử dụng lệnh này"),
                          message_object, thread_id, thread_type, ttl=60000)
        return

    if thread_type == ThreadType.USER:
        user_id = thread_id
    elif message_object.mentions:
        user_id = message_object.mentions[0]['uid']
    else:
        self.replyMessage(Message(text="🚦 Vui lòng tag người dùng để chặn hoặc dùng lệnh trong chat riêng."),
                          message_object, thread_id, thread_type, ttl=60000)
        return

    try:
        user_name = get_user_name_by_id(self, user_id)
        self.blockUser(user_id)
        self.replyMessage(Message(text=f"🚦 Đã chặn {user_name}."),
                          message_object, thread_id, thread_type, ttl=60000)
    except Exception as e:
        self.replyMessage(Message(text=f"🚦 Không thể chặn người dùng: {e}"),
                          message_object, thread_id, thread_type, ttl=60000)


# ✅ Mở chặn người dùng
def unblockto(message, message_object, thread_id, thread_type, author_id, self):
    if author_id not in ADMIN:
        self.replyMessage(Message(text="🚦Bạn không có quyền sử dụng lệnh này."),
                          message_object, thread_id, thread_type, ttl=60000)
        return

    if thread_type == ThreadType.USER:
        user_id = thread_id
    elif message_object.mentions:
        user_id = message_object.mentions[0]['uid']
    else:
        self.replyMessage(Message(text="🚦 Vui lòng tag người dùng để mở chặn hoặc dùng lệnh trong chat riêng."),
                          message_object, thread_id, thread_type, ttl=60000)
        return

    try:
        user_name = get_user_name_by_id(self, user_id)
        self.unblockUser(user_id)
        self.replyMessage(Message(text=f"🚦 Đã mở chặn {user_name}."),
                          message_object, thread_id, thread_type, ttl=60000)
    except Exception as e:
        self.replyMessage(Message(text=f"🚦 Không thể mở chặn người dùng: {e}"),
                          message_object, thread_id, thread_type, ttl=60000)

# ➖ Xóa kết bạn
def removefrito(message, message_object, thread_id, thread_type, author_id, self):
    if author_id not in ADMIN:
        self.replyMessage(Message(text="🚦Bạn không có quyền sử dụng lệnh này."),
                          message_object, thread_id, thread_type, ttl=60000)
        return

    try:
        user_id = thread_id if thread_type == ThreadType.USER else (
            message_object.mentions[0]['uid'] if message_object.mentions else None)

        if not user_id:
            self.replyMessage(Message(text="🚦 Vui lòng tag người dùng để xóa kết bạn."),
                              message_object, thread_id, thread_type, ttl=60000)
            return

        if user_id == self.uid:
            self.replyMessage(Message(text="🚦 Không thể xóa chính mình."),
                              message_object, thread_id, thread_type, ttl=60000)
            return

        user_name = get_user_name_by_id(self, user_id)
        self.unfriendUser(user_id)
        self.replyMessage(Message(text=f"🚦 Đã xóa kết bạn với {user_name}."),
                          message_object, thread_id, thread_type, ttl=60000)
    except Exception as e:
        self.replyMessage(Message(text=f"🚦 Không thể xóa kết bạn: {e}"),
                          message_object, thread_id, thread_type, ttl=60000)


# 🧠 Đăng ký lệnh
def TQD():
    return {        
        "removefr": removefrito,
        "block": blockto,
        "unblock": unblockto
    }
