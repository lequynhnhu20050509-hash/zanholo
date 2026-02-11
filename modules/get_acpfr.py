import time
from zlapi.models import Message, MultiMsgStyle, MessageStyle, ThreadType
from config import PREFIX, ADMIN
des = {
    'version': '1.0.1',
    'credits': "Latte",
    'description': 'Xem lời mời kb và acp',
    'power': 'Quản trị viên Bot'
}

def get_user_name(client, author_id):
    try:
        user_info = client.fetchUserInfo(author_id)
        author_info = user_info.changed_profiles.get(str(author_id), {}) if user_info and user_info.changed_profiles else {}
        return author_info.get('zaloName', 'Không xác định')
    except Exception:
        return 'Không xác định'

def _reply_styled_message(client, text, message_object, thread_id, thread_type, author_id, ttl=120000):
    name = get_user_name(client, author_id)
    full_text = f"{name}\n➜{text}"
    styles = MultiMsgStyle([
        MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
        MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
    ])
    client.replyMessage(Message(text=full_text, style=styles),
                        message_object, thread_id, thread_type, ttl=ttl)

def handle_friend_command(message, message_object, thread_id, thread_type, author_id, client):
    parts = message.strip().lower().split()
    
    if str(author_id) not in ADMIN:
        _reply_styled_message(client, "Bạn không có quyền sử dụng lệnh này. Chỉ có admin Latte mới được sử dụng lệnh này 🚦", message_object, thread_id, thread_type, author_id)
        return

    if len(parts) < 2:
        help_text = (
            f"Hướng dẫn sử dụng lệnh {PREFIX}friend:\n"
            f"➜ {PREFIX}friend list - Xem số lượng lời mời kết bạn đang chờ.\n"
            f"➜ {PREFIX}friend acceptall - Chấp nhận tất cả lời mời kết bạn."
        )
        _reply_styled_message(client, help_text, message_object, thread_id, thread_type, author_id, ttl=120000)
        return

    cmd = parts[1]

    if cmd == 'list':
        try:
            requests_data = client.getReceivedFriendRequests()
            recomm_items = requests_data.get('recommItems', [])
            
            if not recomm_items:
                _reply_styled_message(client, "Không có lời mời kết bạn nào đang chờ. ✅", message_object, thread_id, thread_type, author_id)
                return

            response_text = f"💌 Acc đang có tổng cộng {len(recomm_items)} lời mời kết bạn đang chờ."
            
            _reply_styled_message(client, response_text.strip(), message_object, thread_id, thread_type, author_id, ttl=120000)

        except Exception as e:
            _reply_styled_message(client, f"Đã xảy ra lỗi khi lấy danh sách: {e}", message_object, thread_id, thread_type, author_id)

    elif cmd == 'acpall':
        try:
            _reply_styled_message(client, "Đang bắt đầu quá trình chấp nhận tất cả lời mời kết bạn...", message_object, thread_id, thread_type, author_id)
            
            requests_data = client.getReceivedFriendRequests()
            recomm_items = requests_data.get('recommItems', [])
            
            if not recomm_items:
                _reply_styled_message(client, "Không có lời mời nào để chấp nhận. ✅", message_object, thread_id, thread_type, author_id)
                return

            success_count = 0
            fail_count = 0
            
            for item in recomm_items:
                user_info = item.get('dataInfo', {})
                user_id = user_info.get('userId')
                if user_id:
                    try:
                        client.acceptFriendRequest(user_id)
                        success_count += 1
                    except Exception as e:
                        fail_count += 1
                        print(f"[FRIEND] Lỗi khi chấp nhận lời mời từ ID {user_id}: {e}")
            
            summary_text = f"Hoàn tất! ✅\n- Đã chấp nhận thành công: {success_count}\n- Thất bại: {fail_count}"
            _reply_styled_message(client, summary_text, message_object, thread_id, thread_type, author_id)

        except Exception as e:
            _reply_styled_message(client, f"Đã xảy ra lỗi trong quá trình chấp nhận: {e}", message_object, thread_id, thread_type, author_id)
    
    else:
        help_text = (
            f"Lệnh '{cmd}' không hợp lệ.\n"
            f"Vui lòng sử dụng {PREFIX}friend list hoặc {PREFIX}friend acceptall."
        )
        _reply_styled_message(client, help_text, message_object, thread_id, thread_type, author_id)


def TQD():
    return {
        'friend': handle_friend_command,
    }