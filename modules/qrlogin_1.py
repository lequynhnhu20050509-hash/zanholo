from zlapi.models import Message, ThreadType
from zlapi import ZaloAPI, ZaloLoginError
import time
import os
import json
import threading
import pytz
from datetime import datetime, timedelta
from config import ADMIN, PREFIX

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Đăng nhập QR - Tạo bot Zalo",
    'power': "Thành viên"
}

def load_config():
    try:
        with open('seting.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        # Trả về cấu trúc mặc định phù hợp với seting.json của bạn
        return {
            "prefix": "-",
            "name_bot": "T Q D", 
            "version": "2.0.1",
            "autorestart": "True",
            "admin": "2143747344068352058",
            "account_bot": "2143747344068352058",
            "adm": [ 
               "4680318018018866697",
               "4464938994651336204",
               "1835794555224761984"],
            "data": []  # Thêm data array cho các bot
        }

def save_config(config):
    try:
        with open('seting.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def login_qr_process(client, thread_id, thread_type, author_id):
    qr_file_path = f"qr_{thread_id}_{int(time.time())}.png"
    
    try:
        client.send(Message(text="⏳ Đang tạo mã QR..."), thread_id, thread_type)
        
        temp_client = ZaloAPI(phone=None, password=None, imei=None, auto_login=False)
        
        def send_qr(path_to_qr):
            if os.path.exists(path_to_qr):
                client.sendLocalImage(
                    imagePath=path_to_qr, 
                    thread_id=thread_id, 
                    thread_type=thread_type, 
                    message=Message(text="🪪 Quét mã QR trong 120 giây!"), 
                    ttl=120000
                )
        
        temp_client.loginWithQR(qr_path=qr_file_path, on_qr_generated=send_qr)
        
        if temp_client.isLoggedIn():
            imei = temp_client._state.user_imei
            cookies = temp_client.getSession()
            user_info = temp_client.getCurrentUser()
            user_name = user_info.get('name', 'Không xác định')
            
            # Gửi thông báo chi tiết kèm imei + cookies
            client.send(Message(
                text=f"✅ Đăng nhập thành công!\n"
                     f"👤 Tên: {user_name}\n\n"
                     f" IMEI: {imei}\n\n"
                     f"Cookies: {json.dumps(cookies)}"
            ), thread_id, thread_type)
            
            config = load_config()
            
            if "data" not in config:
                config["data"] = []
            
            existing_bot = next((bot for bot in config["data"] if str(bot.get("author_id")) == str(author_id)), None)
            
            vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            now = datetime.now(vietnam_tz)
            
            bot_data = {
                "prefix": PREFIX,
                "session_cookies": cookies,
                "imei": imei,
                "is_main_bot": False,
                "username": user_name,
                "author_id": author_id,
                "status": True,
                "kich_hoat": now.strftime('%d/%m/%Y'),
                "het_han": (now + timedelta(days=30)).strftime('%d/%m/%Y'),
                "zalo_name": user_name,
                "created_at": now.strftime('%d/%m/%Y %H:%M:%S'),
                "last_updated": now.strftime('%d/%m/%Y %H:%M:%S')
            }
            
            if existing_bot:
                existing_bot.update(bot_data)
                client.send(Message(text="🔄 Đã cập nhật thông tin bot!"), thread_id, thread_type)
            else:
                config["data"].append(bot_data)
                client.send(Message(text=f"🚀 Đã tạo bot thành công!\nPrefix: {PREFIX}"), thread_id, thread_type)
            
            save_config(config)
                
    except ZaloLoginError:
        client.send(Message(text="❌ Hết thời gian quét mã QR!"), thread_id, thread_type)
    except Exception as e:
        client.send(Message(text=f"❌ Lỗi: {str(e)}"), thread_id, thread_type)
    finally:
        if os.path.exists(qr_file_path):
            try:
                os.remove(qr_file_path)
            except:
                pass


def handle_qrlogin_command(message, message_object, thread_id, thread_type, author_id, client):
    # Kiểm tra xem có phải là tin nhắn riêng không
    if thread_type != ThreadType.USER:
        client.replyMessage(Message(text="🚦 Lệnh này chỉ dùng trong tin nhắn riêng tư!"), message_object, thread_id, thread_type)
        return
    
    # Phân tích lệnh
    parts = message.split()
    if len(parts) > 1 and parts[1].lower() == 'confirm':
        # Bỏ qua cảnh báo nếu có confirm
        pass
    else:
        # Kiểm tra nếu đã có bot
        config = load_config()
        if "data" not in config:
            config["data"] = []
            
        existing_bot = next((bot for bot in config["data"] if str(bot.get("author_id")) == str(author_id)), None)
        
        if existing_bot and existing_bot.get("status"):
            client.replyMessage(
                Message(text=f"⚠️ Bạn đã có bot đang hoạt động!\nGõ `{PREFIX}qrlogin confirm` để xác nhận đăng nhập lại."),
                message_object, thread_id, thread_type
            )
            return
    
    # Bắt đầu quá trình đăng nhập QR
    client.replyMessage(Message(text="🔄 Bắt đầu tạo mã QR đăng nhập..."), message_object, thread_id, thread_type)
    threading.Thread(target=login_qr_process, args=(client, thread_id, thread_type, author_id), daemon=True).start()

def TQD():
    return {
        'qrlogin': handle_qrlogin_command
    }