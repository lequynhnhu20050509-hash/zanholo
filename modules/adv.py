import json
import os
import time
import threading
from zlapi.models import *
from config import ADMIN, PREFIX
from datetime import datetime

des = {
    'version': '1.0.7',
    'credits': "Latte",
    'description': 'Tự động quảng cáo.',
    'power': 'Quản trị viên Bot'
}

CONFIG_PATH = 'modules/cache/adv_config.json'
STATUS_PATH = 'modules/cache/adv_status.json'
DISABLE_PATH = 'modules/cache/adv_disable.json'
CARD_PATH = 'modules/cache/adv_card.json'

json_lock = threading.Lock()

def is_admin(author_id):
    return author_id == ADMIN

def load_json(path, default):
    with json_lock:
        if not os.path.exists(path):
            return default
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ADV] Lỗi đọc JSON {path}: {e}")
            return default

def save_json(path, data):
    with json_lock:
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[ADV] Lỗi ghi JSON {path}: {e}")

def get_user_name(client, author_id):
    try:
        user_info = client.fetchUserInfo(author_id)
        author_info = user_info.changed_profiles.get(author_id, {}) if user_info and user_info.changed_profiles else {}
        return author_info.get('zaloName', 'Không xác định')
    except Exception as e:
        print(f"[ADV] Lỗi lấy tên người dùng {author_id}: {e}")
        return 'Không xác định'

def adv_broadcast(client):
    config = load_json(CONFIG_PATH, {})
    status = load_json(STATUS_PATH, {'on': False, 'interval_min': 60, 'last_adv_time': 0})
    adv_disable = load_json(DISABLE_PATH, [])
    card_config = load_json(CARD_PATH, {'enabled': False, 'user_id': None, 'phone': None})

    if not status.get('on', False) or not config.get('content'):
        print("[ADV] Không gửi: adv off hoặc chưa có nội dung")
        return

    try:
        all_groups = list(client.fetchAllGroups().gridVerMap.keys())
    except Exception as e:
        print(f"[ADV] Lỗi lấy danh sách nhóm: {e}")
        return

    processed_groups = set()
    failed, disabled, success = [], [], []

    for group_id in all_groups:
        if group_id in processed_groups or group_id in adv_disable:
            if group_id in adv_disable:
                disabled.append(group_id)
            continue

        try:
            client.send(
                Message(text=config['content'], parse_mode="HTML"),
                thread_id=group_id,
                thread_type=ThreadType.GROUP,
                ttl=1800000
            )

            if card_config.get('enabled') and card_config.get('user_id') and card_config.get('phone'):
                try:
                    user_info = client.fetchUserInfo(card_config['user_id']).changed_profiles.get(card_config['user_id'])
                    if user_info and user_info.avatar:
                        client.sendBusinessCard(
                            userId=card_config['user_id'],
                            qrCodeUrl=user_info.avatar,
                            thread_id=group_id,
                            thread_type=ThreadType.GROUP,
                            phone=card_config['phone'],
                            ttl=1800000
                        )
                except Exception as e:
                    print(f"[ADV] Lỗi gửi danh thiếp cho nhóm {group_id}: {e}")
                    
            success.append(group_id)
            processed_groups.add(group_id)
            time.sleep(2)
        except Exception as e:
            failed.append(f"{group_id} (Lỗi: {e})")
            processed_groups.add(group_id)
            
    if success:
        status['last_adv_time'] = int(time.time())
        save_json(STATUS_PATH, status)

    print(f"[ADV] Gửi thành công: {len(success)}, thất bại: {len(failed)}, bị tắt: {len(disabled)}")

def adv_scheduler(client):
    print("[ADV] Scheduler started")
    last_status = None
    while True:
        try:
            status = load_json(STATUS_PATH, {'on': False, 'interval_min': 60, 'last_adv_time': 0})
            if last_status != status:
                print(f"[ADV] Scheduler tick. Status: {status}")
                last_status = status.copy()

            if status.get('on', False):
                interval = int(status.get('interval_min', 60)) * 60
                last_adv_time = status.get('last_adv_time', 0)
                current_time = int(time.time())
                time_since_last_adv = current_time - last_adv_time

                if time_since_last_adv >= interval:
                    adv_broadcast(client)
                    print(f"[ADV] Ngủ {interval // 60} phút")
                    time.sleep(interval)
                else:
                    time_to_wait = interval - time_since_last_adv
                    print(f"[ADV] Chờ {time_to_wait // 60} phút nữa để gửi quảng cáo")
                    time.sleep(time_to_wait)
            else:
                if last_status is None or last_status.get('on') != status.get('on'):
                    print("[ADV] Hiện adv đang tắt, ngủ 10s")
                time.sleep(10)
        except Exception as e:
            print(f"[ADV] Scheduler exception: {e}")
            time.sleep(10)

def start_adv_scheduler(client):
    t = threading.Thread(target=adv_scheduler, args=(client,), daemon=True)
    t.start()

def handle_adv_command(message, message_object, thread_id, thread_type, author_id, client):
    parts = message.strip().split()
    
    if not is_admin(author_id):
        name = get_user_name(client, author_id)
        rest_text = "Bạn không có quyền sử dụng lệnh này.Chỉ có admin Latte mới được sử dụng 🚦"
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
        ])
        client.replyMessage(Message(text=msg, style=styles),
                            message_object, thread_id, thread_type, ttl=30000)
        return

    name = get_user_name(client, author_id)

    if len(parts) < 2:
        rest_text = (
            f"Hướng dẫn sử dụng lệnh {PREFIX}adv:\n"
            f"➜ {PREFIX}adv on - Bật quảng cáo tự động\n"
            f"➜ {PREFIX}adv off - Tắt quảng cáo tự động\n"
            f"➜ {PREFIX}adv set <nội dung> - Đặt nội dung quảng cáo\n"
            f"➜ {PREFIX}adv setcard <id user> <phone/text> - Đặt danh thiếp\n"
            f"➜ {PREFIX}adv card - Chuyển đổi trạng thái gửi danh thiếp\n"
            f"➜ {PREFIX}adv interval <phút> - Đặt khoảng thời gian giữa các lần quảng cáo\n"
            f"➜ {PREFIX}adv disable [group_id] - Không gửi quảng cáo vào nhóm\n"
            f"➜ {PREFIX}adv enable [group_id] - Cho phép gửi quảng cáo vào nhóm\n"
            f"➜ {PREFIX}adv info - Xem thông tin cấu hình quảng cáo"
        )
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
        ])
        client.replyMessage(Message(text=msg, style=styles),
                            message_object, thread_id, thread_type, ttl=120000)
        return

    cmd = parts[1].lower()
    config = load_json(CONFIG_PATH, {})
    status = load_json(STATUS_PATH, {'on': False, 'interval_min': 60, 'last_adv_time': 0})
    adv_disable = load_json(DISABLE_PATH, [])
    card_config = load_json(CARD_PATH, {'enabled': False, 'user_id': None, 'phone': None})

    if cmd == 'set' and len(parts) < 3:
        rest_text = (
            f"Lệnh {PREFIX}adv set cần nội dung quảng cáo.\n"
            f"📋 Cách dùng: {PREFIX}adv set <nội dung>\n"
            f"Ví dụ: {PREFIX}adv set Chào mừng đến với nhóm của chúng tôi!"
        )
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
        ])
        client.replyMessage(Message(text=msg, style=styles),
                            message_object, thread_id, thread_type, ttl=30000)
        return
    elif cmd == 'set' and len(parts) >= 3:
        content = message.split(' ', 2)[2]
        config['content'] = content
        save_json(CONFIG_PATH, config)
        
        rest_text = "đã cập nhật nội dung quảng cáo! 📝"
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
        ])
        client.replyMessage(Message(text=msg, style=styles),
                            message_object, thread_id, thread_type, ttl=30000)
        return

    if cmd == 'setcard' and len(parts) < 4:
        rest_text = (
            f"Lệnh {PREFIX}adv setcard cần ID người dùng và nội dung danh thiếp.\n"
            f"📋 Cách dùng: {PREFIX}adv setcard <id user> <phone/text>\n"
            f"Ví dụ: {PREFIX}adv setcard 1234567890 SĐT: 0123 456 789"
        )
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
        ])
        client.replyMessage(Message(text=msg, style=styles),
                            message_object, thread_id, thread_type, ttl=30000)
        return
    elif cmd == 'setcard' and len(parts) >= 4:
        user_id = parts[2]
        phone_content = ' '.join(parts[3:])
        try:
            user_info = client.fetchUserInfo(user_id).changed_profiles.get(user_id)
            if not user_info or not user_info.avatar:
                rest_text = "Người dùng không tồn tại hoặc không có ảnh đại diện. 🚦"
                msg = f"{name}\n➜{rest_text}"
                styles = MultiMsgStyle([
                    MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                    MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
                ])
                client.replyMessage(Message(text=msg, style=styles),
                                    message_object, thread_id, thread_type, ttl=30000)
                return
            card_config['user_id'] = user_id
            card_config['phone'] = phone_content
            save_json(CARD_PATH, card_config)
            
            rest_text = f"đã cập nhật danh thiếp cho user {user_id}! 📇"
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            ])
            client.replyMessage(Message(text=msg, style=styles),
                                message_object, thread_id, thread_type, ttl=30000)
        except Exception as e:
            rest_text = f"Lỗi khi đặt danh thiếp: {str(e)} 🚦"
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            ])
            client.replyMessage(Message(text=msg, style=styles),
                                message_object, thread_id, thread_type, ttl=30000)
        return

    if cmd == 'card':
        if len(parts) > 2:
            rest_text = (
                f"Lệnh {PREFIX}adv card không cần tham số bổ sung.\n"
                f"📋 Cách dùng: {PREFIX}adv card\n"
                f"Chức năng: Chuyển đổi trạng thái gửi danh thiếp (bật ↔ tắt)."
            )
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            ])
            client.replyMessage(Message(text=msg, style=styles),
                                message_object, thread_id, thread_type, ttl=30000)
            return
        card_config['enabled'] = not card_config.get('enabled', False)
        save_json(CARD_PATH, card_config)
        
        rest_text = f"đã {'bật' if card_config['enabled'] else 'tắt'} gửi danh thiếp sau quảng cáo! {'📇' if card_config['enabled'] else '🚫'}"
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
        ])
        client.replyMessage(Message(text=msg, style=styles),
                            message_object, thread_id, thread_type, ttl=30000)
        return

    if cmd == 'interval' and len(parts) < 3:
        rest_text = (
            f"Lệnh {PREFIX}adv interval cần số phút.\n"
            f"📋 Cách dùng: {PREFIX}adv interval <phút>\n"
            f"Ví dụ: {PREFIX}adv interval 60"
        )
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
        ])
        client.replyMessage(Message(text=msg, style=styles),
                            message_object, thread_id, thread_type, ttl=30000)
        return
    elif cmd == 'interval' and len(parts) == 3:
        try:
            interval = int(parts[2])
            if interval <= 0:
                rest_text = "Khoảng thời gian phải là số nguyên dương. 🚦"
                msg = f"{name}\n➜{rest_text}"
                styles = MultiMsgStyle([
                    MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                    MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
                ])
                client.replyMessage(Message(text=msg, style=styles),
                                    message_object, thread_id, thread_type, ttl=30000)
                return
            status['interval_min'] = interval
            save_json(STATUS_PATH, status)
            
            rest_text = f"đã đặt khoảng thời gian quảng cáo là {interval} phút! ⏰"
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            ])
            client.replyMessage(Message(text=msg, style=styles),
                                message_object, thread_id, thread_type, ttl=30000)
        except ValueError:
            rest_text = "Vui lòng nhập một số nguyên hợp lệ cho khoảng thời gian. 🚦"
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            ])
            client.replyMessage(Message(text=msg, style=styles),
                                message_object, thread_id, thread_type, ttl=30000)
        return

    if cmd == 'disable':
        group_id = parts[2] if len(parts) >= 3 else thread_id
        if group_id not in adv_disable:
            adv_disable.append(group_id)
            save_json(DISABLE_PATH, adv_disable)
            rest_text = f"đã tắt quảng cáo cho nhóm {group_id}! 🚫"
        else:
            rest_text = f"Nhóm {group_id} đã được tắt quảng cáo trước đó. 🚦"
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
        ])
        client.replyMessage(Message(text=msg, style=styles),
                            message_object, thread_id, thread_type, ttl=30000)
        return

    if cmd == 'enable':
        group_id = parts[2] if len(parts) >= 3 else thread_id
        if group_id in adv_disable:
            adv_disable.remove(group_id)
            save_json(DISABLE_PATH, adv_disable)
            rest_text = f"đã bật lại quảng cáo cho nhóm {group_id}! ✅"
        else:
            rest_text = f"Nhóm {group_id} chưa từng bị tắt quảng cáo. 🚦"
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
        ])
        client.replyMessage(Message(text=msg, style=styles),
                            message_object, thread_id, thread_type, ttl=30000)
        return

    if cmd == 'on':
        current_state = status.get('on', False)
        if current_state:
            rest_text = "Quảng cáo tự động đã được bật sẵn rồi! 🚦"
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            ])
            client.replyMessage(Message(text=msg, style=styles),
                                message_object, thread_id, thread_type, ttl=30000)
        else:
            status['on'] = True
            save_json(STATUS_PATH, status)
            
            rest_text = "Đã bật quảng cáo tự động! 🚀"
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            ])
            client.replyMessage(Message(text=msg, style=styles),
                                message_object, thread_id, thread_type=thread_type, ttl=60000)
        return

    elif cmd == 'off':
        current_state = status.get('on', False)
        if not current_state:
            rest_text = "Quảng cáo tự động đã được tắt rồi! 🚦"
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            ])
            client.replyMessage(Message(text=msg, style=styles),
                                message_object, thread_id, thread_type=thread_type,)
        else:
            status['on'] = False
            save_json(STATUS_PATH, status)
            
            rest_text = "Đã tắt quảng cáo tự động! 💤"
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            ])
            client.replyMessage(Message(text=msg, style=styles),
                                message_object, thread_id, thread_type=thread_type, ttl=60000)
        return

    if cmd == 'info':
        try:
            groups = list(client.fetchAllGroups().gridVerMap.keys())
        except Exception as e:
            groups = []
            print(f"[ADV] Lỗi lấy danh sách nhóm khi xem info: {e}")

        last_adv_time = status.get('last_adv_time', 0)
        last_adv_str = (
            datetime.fromtimestamp(last_adv_time).strftime("%H:%M:%S, %A, ngày %d tháng %m năm %Y")
            if last_adv_time > 0
            else 'Chưa có'
        )
        day_map = {
            'Monday': 'Thứ Hai',
            'Tuesday': 'Thứ Ba',
            'Wednesday': 'Thứ Tư',
            'Thursday': 'Thứ Năm',
            'Friday': 'Thứ Sáu',
            'Saturday': 'Thứ Bảy',
            'Sunday': 'Chủ Nhật'
        }
        if last_adv_time > 0:
            day_name = datetime.fromtimestamp(last_adv_time).strftime("%A")
            last_adv_str = last_adv_str.replace(day_name, day_map.get(day_name, day_name))

        rest_text = (
            f"Cấu hình quảng cáo:\n"
            f"➜ Trạng thái: {'✅ Bật' if status.get('on', False) else '❌ Tắt'}\n"
            f"➜ Khoảng thời gian: {status.get('interval_min', 60)} phút\n"
            f"➜ Nội dung: {config.get('content', '[Chưa đặt]')}\n"
            f"➜ Gửi danh thiếp: {'✅' if card_config.get('enabled', False) else '❌'}\n"
            f"➜ User danh thiếp: {card_config.get('user_id', '[Chưa đặt]')}\n"
            f"➜ Nội dung danh thiếp: {card_config.get('phone', '[Chưa đặt]')}\n"
            f"➜ Số nhóm hiện tại: {len(groups)}\n"
            f"➜ Số nhóm bị tắt quảng cáo: {len(adv_disable)}\n"
            f"➜ Lần quảng cáo cuối: {last_adv_str}"
        )
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
        ])
        client.replyMessage(Message(text=msg, style=styles),
                            message_object, thread_id, thread_type=thread_type, ttl=120000)
        return

    rest_text = (
        f"Lệnh không hợp lệ: {cmd}\n"
        f"📋 Hướng dẫn sử dụng lệnh {PREFIX}adv:\n"
        f"➜ {PREFIX}adv on - Bật quảng cáo tự động\n"
        f"➜ {PREFIX}adv off - Tắt quảng cáo tự động\n"
        f"➜ {PREFIX}adv set <nội dung> - Đặt nội dung quảng cáo\n"
        f"➜ {PREFIX}adv setcard <id user> <phone/text> - Đặt danh thiếp\n"
        f"➜ {PREFIX}adv card - Chuyển đổi trạng thái gửi danh thiếp\n"
        f"➜ {PREFIX}adv interval <phút> - Đặt khoảng thời gian giữa các lần quảng cáo\n"
        f"➜ {PREFIX}adv disable [group_id] - Không gửi quảng cáo vào nhóm\n"
        f"➜ {PREFIX}adv enable [group_id] - Cho phép gửi quảng cáo vào nhóm\n"
        f"➜ {PREFIX}adv info - Xem thông tin cấu hình"
    )
    msg = f"{name}\n➜{rest_text}"
    styles = MultiMsgStyle([
        MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
        MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
    ])
    client.replyMessage(Message(text=msg, style=styles),
                        message_object, thread_id, thread_type=thread_type, ttl=120000)

def TQD():
    return {
        'adv': handle_adv_command,
    }
    
