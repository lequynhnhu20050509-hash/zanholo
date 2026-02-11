import threading
from threading import Thread  # Thêm import Thread
from zlapi import *
from zlapi.models import *
from config import ADMIN

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Kick thành viên",
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

def kick(message, message_object, thread_id, thread_type, author_id, bot):
    """Kick người dùng cụ thể khỏi nhóm."""
    def send_kick_response():
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
            admin_ids = group.adminIds.copy()
            if group.creatorId not in admin_ids:
                admin_ids.append(group.creatorId)
            
            if bot.uid not in admin_ids:
                response = "➜ Lệnh này không khả thi do 🤖BOT không có quyền cầm 🔑 key nhóm 🤧"
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)
                return

            uids = extract_uids_from_mentions(message_object)
            if not uids:
                response = "➜ Vui lòng @tag người dùng để kick 🤧\n➜ Ví dụ: /kick @user ✅"
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)
                return

            response = ""
            for uid in uids:
                if uid in admin_ids:
                    response += f"➜ 😲 Không thể kick admin {get_user_name_by_id(bot, uid)} 🤧\n"
                    continue
                try:
                    bot.kickUsersInGroup(uid, thread_id)
                    bot.blockUsersInGroup(uid, thread_id)
                    user_name = get_user_name_by_id(bot, uid)
                    response += f"➜ 💪 Đã kick người dùng 😫 {user_name} khỏi nhóm thành công ✅\n"
                except Exception as e:
                    user_name = get_user_name_by_id(bot, uid)
                    response += f"➜ 😲 Không thể kick người dùng 😫 {user_name} khỏi nhóm: {str(e)} 🤧\n"

            if response:
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)
        except Exception as e:
            print(f"Error in kick: {e}")
            bot.replyMessage(Message(text="➜ 🐞 Đã xảy ra lỗi gì đó 🤧"), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)

    thread = Thread(target=send_kick_response)
    thread.start()

def TQD():
    """Trả về dictionary chứa các lệnh."""
    return {
        'kick': kick
    }