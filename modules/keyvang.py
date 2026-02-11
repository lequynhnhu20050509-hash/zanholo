import threading
from threading import Thread
from zlapi import *
from zlapi.models import *
from config import ADMIN

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Chuyển quyền sở hữu nhóm",
    'power': "Admin"
}

def get_user_name_by_id(bot, author_id):
    """Lấy tên người dùng từ ID."""
    try:
        user = bot.fetchUserInfo(author_id).changed_profiles[author_id].displayName
        return user
    except:
        return "Unknown User"

def extract_uids_from_mentions(message_object):
    """Trích xuất danh sách UID từ mentions."""
    uids = []
    if message_object.mentions:
        uids = [mention['uid'] for mention in message_object.mentions if 'uid' in mention]
    return uids

def keyvang(message, message_object, thread_id, thread_type, author_id, bot):
    """Chuyển quyền sở hữu nhóm."""
    def send_keyvang_response():
        try:
            if author_id not in ADMIN:
                response = "➜ Lệnh này chỉ khả thi với admin 🤧"
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)
                return

            if thread_type != ThreadType.GROUP:
                response = "➜ Lệnh này chỉ khả thi trong nhóm 🤧"
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)
                return

            group = bot.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
            if bot.uid != group.creatorId:
                response = "➜ Lệnh này không khả thi do 🤖BOT không phải là chủ nhóm 🤧"
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)
                return

            uids = extract_uids_from_mentions(message_object)
            if not uids:
                response = f"➜ Vui lòng @tag người dùng để chuyển quyền chủ nhóm 🤧\n➜ Ví dụ: /keyvang @user ✅"
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)
                return

            if len(uids) > 1:
                response = "➜ Chỉ có thể chuyển quyền chủ nhóm cho một người dùng duy nhất 🤧"
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)
                return

            uid = uids[0]
            try:
                bot.changeGroupOwner(uid, thread_id)
                user_name = get_user_name_by_id(bot, uid)
                response = f"➜ Đã chuyển quyền chủ nhóm cho {user_name} thành công ✅"
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)
            except Exception as e:
                user_name = get_user_name_by_id(bot, uid)
                response = f"➜ 😲 Không thể chuyển quyền chủ nhóm cho {user_name}: {str(e)} 🤧"
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)

        except Exception as e:
            print(f"Error in keyvang: {e}")
            bot.replyMessage(Message(text="➜ 🐞 Đã xảy ra lỗi gì đó 🤧"), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)

    thread = Thread(target=send_keyvang_response)
    thread.start()

def TQD():
    """Trả về dictionary chứa các lệnh."""
    return {
        'keyvang': keyvang
    }
    