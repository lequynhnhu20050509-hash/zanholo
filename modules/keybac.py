import threading
from threading import Thread
from zlapi import *
from zlapi.models import *
from config import ADMIN, PREFIX

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Bổ nhiệm phó nhóm",
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

def key(message, message_object, thread_id, thread_type, author_id, bot):
    """Quản lý trưởng{PREFIX}phó nhóm."""
    def send_key_response():
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

            parts = message_object.content.split()
            if len(parts) < 2:
                response = (
                    "➜ Vui lòng @tag tên người dùng hoặc nhập lệnh sau lệnh {PREFIX}key 🤧\n"
                    "➜ Ví dụ: {PREFIX}key @user hoặc {PREFIX}key remove @user hoặc {PREFIX}key list ✅"
                )
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)
                return

            # Xác định hành động: mặc định là 'add' nếu người dùng chỉ gõ {PREFIX}key @user
            if parts[1].startswith('@'):
                sub_action = 'add'
                uids = extract_uids_from_mentions(message_object)
            else:
                sub_action = parts[1].lower()
                uids = extract_uids_from_mentions(message_object)

            response = ""

            if sub_action == 'add':
                if not uids:
                    response = (
                        "➜ Vui lòng @tag tên người dùng sau lệnh: {PREFIX}key 🤧\n"
                        "➜ Ví dụ: {PREFIX}key @user ✅"
                    )
                else:
                    for uid in uids:
                        try:
                            bot.addGroupAdmins(uid, thread_id)
                            user_name = get_user_name_by_id(bot, uid)
                            response += f"➜ Đã thêm {user_name} làm phó nhóm ✅\n"
                        except Exception as e:
                            response += f"➜ 😲 Không thể thêm {get_user_name_by_id(bot, uid)} làm phó nhóm: {str(e)} 🤧\n"

            elif sub_action == 'remove':
                if not uids:
                    response = (
                        "➜ Vui lòng @tag tên người dùng sau lệnh: {PREFIX}key remove 🤧\n"
                        "➜ Ví dụ: {PREFIX}key remove @user ✅"
                    )
                else:
                    for uid in uids:
                        try:
                            bot.removeGroupAdmins(uid, thread_id)
                            user_name = get_user_name_by_id(bot, uid)
                            response += f"➜ Đã xóa {user_name} khỏi vai trò phó nhóm ✅\n"
                        except Exception as e:
                            response += f"➜ 😲 Không thể xóa {get_user_name_by_id(bot, uid)} khỏi vai trò phó nhóm: {str(e)} 🤧\n"

            elif sub_action == 'list':
                try:
                    if admin_ids:
                        response = "➜ 🛡️ Danh sách phó nhóm 👑\n"
                        for idx, uid in enumerate(admin_ids, start=1):
                            response += f"      ➜ {idx}. 👑 {get_user_name_by_id(bot, uid)}\n"
                    else:
                        response = "➜ Không có phó nhóm nào trong danh sách 🤧"
                except Exception as e:
                    response = f"➜ 😲 Không thể lấy danh sách phó nhóm: {str(e)} 🤧"
            else:
                response = f"➜ Lệnh {PREFIX}key {sub_action} không được hỗ trợ 🤧"

            if response:
                bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)

        except Exception as e:
            print(f"Error in key: {e}")
            bot.replyMessage(Message(text="➜ 🐞 Đã xảy ra lỗi gì đó 🤧"), message_object, thread_id=thread_id, thread_type=thread_type, ttl=30000)

    thread = Thread(target=send_key_response)
    thread.start()

    
def TQD():
    """Trả về dictionary chứa các lệnh."""
    return {
        'key': key,        
    }