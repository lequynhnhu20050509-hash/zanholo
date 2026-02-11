import threading
from zlapi.models import *
from config import PREFIX, ADMIN
import json

ADMIN_ID = ADMIN

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Lấy thông tin của tin nhắn",
    'power': "Thành viên"
}

def get_user_name_by_id(bot, author_id):
    try:
        user_info = bot.fetchUserInfo(author_id).changed_profiles[author_id]
        return user_info.zaloName or user_info.displayName
    except Exception:
        return "Người Dùng Ẩn Danh"

def handle_src_command(message, message_object, thread_id, thread_type, author_id, bot):
    def src():
        try:
            if message_object.quote:
                q = message_object.quote

                data = {
                    "ownerId": getattr(q, "ownerId", None),
                    "cliMsgId": getattr(q, "cliMsgId", None),
                    "globalMsgId": getattr(q, "globalMsgId", None),
                    "cliMsgType": getattr(q, "cliMsgType", None),


                    

                    "ts": getattr(q, "ts", None),
                    "msg": getattr(q, "msg", None),

                    # attach
                    "attach": json.loads(q.attach) if getattr(q, "attach", None) else {},

                    "fromD": getattr(q, "fromD", None),

                    
                    
                }

                
                response = f"[{get_user_name_by_id(bot, author_id)}] source của bạn đây ✅\n{json.dumps(data, ensure_ascii=False, indent=4)}\n"
            else:
                response = "❌ Vui lòng reply vào một tin nhắn để lấy dữ liệu."

            bot.replyMessage(Message(text=response), message_object, thread_id=thread_id, thread_type=thread_type, ttl=100000)
        except Exception as e:
            print(f"Error: {e}")
            bot.replyMessage(Message(text="🐞 Đã xảy ra lỗi gì đó 🤧"), message_object, thread_id=thread_id, thread_type=thread_type)

    thread = threading.Thread(target=src)
    thread.start()

def TQD():
    return {
        "src": handle_src_command
    }