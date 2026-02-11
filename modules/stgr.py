import json
from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import ADMIN
from config import PREFIX

def load_settings():
    try:
        with open('setting.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

settings = load_settings()
ADM = settings.get('adm', [])

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Thay đổi cài đặt nhóm.",
    'power': "Admin"
}

def get_user_name(client, author_id):
    """Lấy tên user từ author_id"""
    try:
        user_info = client.fetchUserInfo(author_id)
        author_info = user_info.changed_profiles.get(author_id, {}) if user_info and user_info.changed_profiles else {}
        return author_info.get('zaloName', 'Không xác định')
    except:
        return 'Không xác định'

def send_styled_message(client, thread_id, thread_type, name, rest_text, message_object=None, ttl=200000):
    msg = f"{name}\n➜{rest_text}"
    styles = MultiMsgStyle([
        MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
        MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
    ])
    client.sendMessage(Message(text=msg, style=styles), thread_id, thread_type, ttl=ttl)
    if message_object:
        client.sendReaction(message_object, "⚙️", thread_id, thread_type)

def send_plain_message(client, thread_id, thread_type, message, message_object=None, ttl=200000):
    client.sendMessage(Message(text=message), thread_id, thread_type, ttl=ttl)
    if message_object:
        client.sendReaction(message_object, "⚙️", thread_id, thread_type)

def check_admin_permissions(author_id, creator_id, admin_ids):
    all_admin_ids = set(admin_ids)
    all_admin_ids.add(creator_id)
    all_admin_ids.update(ADMIN)
    all_admin_ids.update(ADM)
    return author_id in all_admin_ids

def validate_setting(setting):
    valid_settings = {
        "lockname": ("blockName", "Khóa thay đổi tên nhóm"),
        "styleadmin": ("signAdminMsg", "Ghi chú admin trong tin nhắn"),
        "addmbonly": ("addMemberOnly", "Chỉ cho phép admin thêm thành viên"),
        "onlytopic": ("setTopicOnly", "Chỉ cho phép admin đặt chủ đề"),
        "historymsg": ("enableMsgHistory", "Bật lịch sử tin nhắn"),
        "lockpost": ("lockCreatePost", "Khóa tạo bài viết"),
        "lockpoll": ("lockCreatePoll", "Khóa tạo khảo sát"),
        "joinonly": ("joinAppr", "Yêu cầu phê duyệt khi gia nhập"),
        "lockchat": ("lockSendMsg", "Khóa gửi tin nhắn"),
        "showmb": ("lockViewMember", "Khóa xem danh sách thành viên")
    }
    return valid_settings.get(setting.lower())

def handle_block_name(action, thread_id, client):
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        client.changeGroupSetting(groupId=thread_id, blockName=new_value)
        return f"đã {'bật' if new_value == 1 else 'tắt'} khóa thay đổi tên nhóm! {'🔒' if new_value == 1 else '🔓'}"
    return "hành động không hợp lệ. Vui lòng dùng on hoặc off! ❌"

def handle_sign_admin_msg(action, thread_id, client):
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        client.changeGroupSetting(groupId=thread_id, signAdminMsg=new_value)
        return f"đã {'bật' if new_value == 1 else 'tắt'} ghi chú admin trong tin nhắn! {'📝' if new_value == 1 else '📝❌'}"
    return "hành động không hợp lệ. Vui lòng dùng on hoặc off! ❌"

def handle_add_member_only(action, thread_id, client):
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        client.changeGroupSetting(groupId=thread_id, addMemberOnly=new_value)
        return f"đã {'bật' if new_value == 1 else 'tắt'} chỉ cho phép admin thêm thành viên! {'👥🔒' if new_value == 1 else '👥🔓'}"
    return "hành động không hợp lệ. Vui lòng dùng on hoặc off! ❌"

def handle_set_topic_only(action, thread_id, client):
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        client.changeGroupSetting(groupId=thread_id, setTopicOnly=new_value)
        return f"đã {'bật' if new_value == 1 else 'tắt'} chỉ cho phép admin đặt chủ đề! {'📌🔒' if new_value == 1 else '📌🔓'}"
    return "hành động không hợp lệ. Vui lòng dùng on hoặc off! ❌"

def handle_enable_msg_history(action, thread_id, client):
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        client.changeGroupSetting(groupId=thread_id, enableMsgHistory=new_value)
        return f"đã {'bật' if new_value == 1 else 'tắt'} lịch sử tin nhắn! {'📚' if new_value == 1 else '📚❌'}"
    return "hành động không hợp lệ. Vui lòng dùng on hoặc off! ❌"

def handle_lock_create_post(action, thread_id, client):
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        client.changeGroupSetting(groupId=thread_id, lockCreatePost=new_value)
        return f"đã {'bật' if new_value == 1 else 'tắt'} khóa tạo bài viết! {'📄🔒' if new_value == 1 else '📄🔓'}"
    return "hành động không hợp lệ. Vui lòng dùng on hoặc off! ❌"

def handle_lock_create_poll(action, thread_id, client):
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        client.changeGroupSetting(groupId=thread_id, lockCreatePoll=new_value)
        return f"đã {'bật' if new_value == 1 else 'tắt'} khóa tạo khảo sát! {'📊🔒' if new_value == 1 else '📊🔓'}"
    return "hành động không hợp lệ. Vui lòng dùng on hoặc off! ❌"

def handle_join_appr(action, thread_id, client):
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        client.changeGroupSetting(groupId=thread_id, joinAppr=new_value)
        return f"đã {'bật' if new_value == 1 else 'tắt'} yêu cầu phê duyệt khi gia nhập! {'🚪🔒' if new_value == 1 else '🚪🔓'}"
    return "hành động không hợp lệ. Vui lòng dùng on hoặc off! ❌"

def handle_lock_send_msg(action, thread_id, client):
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        client.changeGroupSetting(groupId=thread_id, lockSendMsg=new_value)
        return f"đã {'bật' if new_value == 1 else 'tắt'} khóa gửi tin nhắn! {'💬🔒' if new_value == 1 else '💬🔓'}"
    return "hành động không hợp lệ. Vui lòng dùng on hoặc off! ❌"

def handle_lock_view_member(action, thread_id, client):
    new_value = 1 if action == "on" else 0 if action == "off" else None
    if new_value is not None:
        client.changeGroupSetting(groupId=thread_id, lockViewMember=new_value)
        return f"đã {'bật' if new_value == 1 else 'tắt'} khóa xem danh sách thành viên! {'👀🔒' if new_value == 1 else '👀🔓'}"
    return "hành động không hợp lệ. Vui lòng dùng on hoặc off! ❌"

def show_menu():
    return (
        "⚙️ QUẢN LÝ CÀI ĐẶT NHÓM ⚙️\n"
        "━━━━━━━━━━━━━━\n"
        "📜 Hướng dẫn cho Đại ca:\n"
        f"• Cú pháp: {PREFIX}stg <cài đặt> <on/off>\n"
        "• Chỉ Đại ca (Admin Bot/Nhóm/Phụ) dùng được nha 😎\n"
        "━━━━━━━━━━━━━━\n"
        "📋 Danh sách cài đặt:\n"
        "• lockname: Khóa thay đổi tên nhóm\n"
        "• styleadmin: Ghi chú admin trong tin nhắn\n"
        "• addmbonly: Chỉ admin được thêm thành viên\n"
        "• onlytopic: Chỉ admin được đặt chủ đề\n"
        "• historymsg: Bật lịch sử tin nhắn\n"
        "• lockpost: Khóa tạo bài viết\n"
        "• lockpoll: Khóa tạo khảo sát\n"
        "• joinonly: Yêu cầu phê duyệt khi gia nhập\n"
        "• lockchat: Khóa gửi tin nhắn\n"
        "• showmb: Khóa xem danh sách thành viên\n"
        "━━━━━━━━━━━━━━\n"
        "⚠️ Lưu ý: Nhập đúng cài đặt và on/off nha Đại ca!"
    )

def handle_group_setting_command(message, message_object, thread_id, thread_type, author_id, client):
    text = message.split()
    name = get_user_name(client, author_id)

    if len(text) < 2 or text[1].lower() == "help":
        send_plain_message(client, thread_id, thread_type, show_menu(), message_object=message_object)
        return

    if len(text) < 3:
        rest_text = "ơi, dùng cú pháp: stg <cài đặt> <on/off> ❌"
        send_styled_message(client, thread_id, thread_type, name, rest_text, message_object=message_object)
        return

    setting = text[1].lower()
    action = text[2].lower()

    group_info = client.fetchGroupInfo(thread_id)
    if not group_info or thread_id not in group_info.gridInfoMap:
        rest_text = "ơi, không thể lấy thông tin nhóm! ❌"
        send_styled_message(client, thread_id, thread_type, name, rest_text, message_object=message_object)
        return

    group_data = group_info.gridInfoMap[thread_id]
    creator_id = group_data.get('creatorId')
    admin_ids = group_data.get('adminIds', [])

    if not check_admin_permissions(author_id, creator_id, admin_ids):
        rest_text = "ơi, chỉ admin bot, admin nhóm hoặc admin phụ mới dùng được! 🚫"
        send_styled_message(client, thread_id, thread_type, name, rest_text, message_object=message_object)
        return

    setting_info = validate_setting(setting)
    if not setting_info:
        rest_text = "ơi, cài đặt không hợp lệ! Xem danh sách cài đặt bằng stg help ❌"
        send_styled_message(client, thread_id, thread_type, name, rest_text, message_object=message_object)
        return

    setting_func, setting_description = setting_info
    setting_action_map = {
        "lockname": handle_block_name,
        "styleadmin": handle_sign_admin_msg,
        "addmbonly": handle_add_member_only,
        "onlytopic": handle_set_topic_only,
        "historymsg": handle_enable_msg_history,
        "lockpost": handle_lock_create_post,
        "lockpoll": handle_lock_create_poll,
        "joinonly": handle_join_appr,
        "lockchat": handle_lock_send_msg,
        "showmb": handle_lock_view_member
    }

    result_message = setting_action_map[setting](action, thread_id, client)
    send_styled_message(client, thread_id, thread_type, name, result_message, message_object=message_object)

def TQD():
    return {
        'stgr': handle_group_setting_command
    }