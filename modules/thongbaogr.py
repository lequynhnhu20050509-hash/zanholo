import json
from zlapi.models import *
from config import ADMIN
import os
import time
from zlapi.models import MultiMsgStyle, MessageStyle, Mention, MultiMention, ZaloAPIException, ThreadType
from config import PREFIX
des = {
    'version': '2.0.1',
    'credits': "Latte",
    'description': 'Tự động gửi thông báo tới tất cả nhóm.',
    'power': 'Quản trị viên Bot'
}

def is_admin(author_id):
    return author_id == ADMIN

def load_duyetbox_data():
    file_path = 'modules/cache/duyetboxdata.json'
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r') as f:
        try:
            data = json.load(f)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

def load_threadtb_status():
    file_path = 'modules/cache/threadtb_status.json'
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_threadtb_status(status):
    file_path = 'modules/cache/threadtb_status.json'
    with open(file_path, 'w') as f:
        json.dump(status, f, indent=4)

def handle_tba_command(message, message_object, thread_id, thread_type, author_id, client):
    styles = MultiMsgStyle([
        MessageStyle(offset=0, length=10000, style="font", size="10", auto_format=False),
    ])

    if not is_admin(author_id):
        response_message = "🚦Bạn không có quyền sử dụng lệnh này."
        client.replyMessage(Message(text=response_message, style=styles), message_object, thread_id, thread_type)
        return
        
    parts = message.split()
    if len(parts) < 3:
        response_message = f"🚦Cú pháp không hợp lệ. Vui lòng sử dụng: {PREFIX}tba <nội dung> <all/no>"
        client.replyMessage(Message(text=response_message, style=styles), message_object, thread_id, thread_type, ttl=30000)
        return

    tag_option = parts[-1].strip().lower()
    content = " ".join(parts[1:-1]).strip()

    if not content:
        response_message = f"🚦Nội dung không được để trống. Vui lòng sử dụng: {PREFIX}tba <nội dung> <all/no>"
        client.replyMessage(Message(text=response_message, style=styles), message_object, thread_id, thread_type, ttl=30000)
        return

    if tag_option not in ['all', 'no']:
        response_message = "🚦Tùy chọn tag không hợp lệ. Vui lòng chọn 'all' hoặc 'no'."
        client.replyMessage(Message(text=response_message, style=styles), message_object, thread_id, thread_type, ttl=30000)
        return

    data = load_duyetbox_data()
    threadtb_status = load_threadtb_status()
    excluded_group_id = "1042923427327215035"
    all_groups = client.fetchAllGroups().gridVerMap.keys()
    success_groups = []
    failed_groups = []
    disabled_groups = []

    for group_id in all_groups:
        if group_id == excluded_group_id:
            continue

        if threadtb_status.get(group_id, True) is False:
            group_info = client.fetchGroupInfo(group_id).gridInfoMap.get(group_id, {})
            group_name = group_info.get('name', 'Không xác định')
            disabled_groups.append(group_name)
            continue

        try:
            group_info = client.fetchGroupInfo(group_id).gridInfoMap.get(group_id, {})
            group_name = group_info.get('name', 'Không xác định')

            if tag_option == 'all':
                members = group_info.get('memVerList', [])
                if members:
                    text = f"<b>{content}</b>"
                    mentions = []
                    offset = len(text)

                    for member in members:
                        member_parts = member.split('_', 1)
                        if len(member_parts) != 2:
                            continue
                        user_id, user_name = member_parts
                        mention = Mention(uid=user_id, offset=offset, length=len(user_name) + 1, auto_format=False)
                        mentions.append(mention)
                        offset += len(user_name) + 2

                    multi_mention = MultiMention(mentions)
                    client.send(
                        Message(text=text, mention=multi_mention, parse_mode="HTML"),
                        thread_id=group_id,
                        thread_type=ThreadType.GROUP
                    )
                    success_groups.append(group_name)
                else:
                    failed_groups.append(f"{group_name} (Không có thành viên)")
            else:
                client.send(
                    Message(text=content, parse_mode="HTML"),
                    thread_id=group_id,
                    thread_type=ThreadType.GROUP
                )
                success_groups.append(group_name)

        except ZaloAPIException as e:
            failed_groups.append(f"{group_name} (Lỗi API: {e})")
        except Exception as e:
            failed_groups.append(f"{group_name} (Lỗi: {e})")

        time.sleep(0.5)

    total_groups = len(success_groups) + len(failed_groups) + len(disabled_groups)
    report = f"[ 🚦BÁO CÁO GỬI THÔNG BÁO ]\n\n"
    report += f"Tổng số nhóm: {total_groups}\n"
    report += f"Thành công: {len(success_groups)}\n"
    report += f"Thất bại: {len(failed_groups)}\n"
    report += f"Bị tắt (threadtb off): {len(disabled_groups)}\n\n"

    if success_groups:
        report += "Nhóm gửi thành công:\n" + "\n".join(f"- {group}" for group in success_groups) + "\n\n"
    if failed_groups:
        report += "Nhóm gửi thất bại:\n" + "\n".join(f"- {group}" for group in failed_groups) + "\n\n"
    if disabled_groups:
        report += "Nhóm bị tắt thông báo:\n" + "\n".join(f"- {group}" for group in disabled_groups)

    max_message_length = 3000
    if len(report) <= max_message_length:
        client.replyMessage(Message(text=report, style=styles), message_object, thread_id, thread_type, ttl=30000)
    else:
        parts = [report[i:i+max_message_length] for i in range(0, len(report), max_message_length)]
        for part in parts:
            client.replyMessage(Message(text=part, style=styles), message_object, thread_id, thread_type, ttl=30000)

def handle_threadtb_command(message, message_object, thread_id, thread_type, author_id, client):
    styles = MultiMsgStyle([
        MessageStyle(offset=0, length=10000, style="font", size="10", auto_format=False),
    ])

    if not is_admin(author_id):
        response_message = "🚦Bạn không có quyền sử dụng lệnh này."
        client.replyMessage(Message(text=response_message, style=styles), message_object, thread_id, thread_type, ttl=30000)
        return

    parts = message.split()
    if len(parts) not in [2, 3]:
        response_message = "🚦Cú pháp không hợp lệ. Vui lòng sử dụng: threadtb <on/off> hoặc threadtb <id nhóm> <on/off>"
        client.replyMessage(Message(text=response_message, style=styles), message_object, thread_id, thread_type, ttl=30000)
        return

    threadtb_status = load_threadtb_status()
    target_group_id = thread_id
    status = None

    if len(parts) == 2:
        status = parts[1].strip().lower()
        if status not in ['on', 'off']:
            response_message = "🚦Tùy chọn không hợp lệ. Vui lòng chọn 'on' hoặc 'off'."
            client.replyMessage(Message(text=response_message, style=styles), message_object, thread_id, thread_type, ttl=30000)
            return
    else:
        target_group_id = parts[1].strip()
        status = parts[2].strip().lower()
        if status not in ['on', 'off']:
            response_message = "🚦Tùy chọn không hợp lệ. Vui lòng chọn 'on' hoặc 'off'."
            client.replyMessage(Message(text=response_message, style=styles), message_object, thread_id, thread_type, ttl=30000)
            return

        try:
            group_info = client.fetchGroupInfo(target_group_id).gridInfoMap.get(target_group_id, None)
            if not group_info:
                response_message = f"Không tìm thấy nhóm với ID: {target_group_id}"
                client.replyMessage(Message(text=response_message, style=styles), message_object, thread_id, thread_type, ttl=30000)
                return
        except ZaloAPIException as e:
            response_message = f"Lỗi khi kiểm tra ID nhóm: {e}"
            client.replyMessage(Message(text=response_message, style=styles), message_object, thread_id, thread_type, ttl=30000)
            return

    group_info = client.fetchGroupInfo(target_group_id).gridInfoMap.get(target_group_id, {})
    group_name = group_info.get('name', 'Không xác định')
    threadtb_status[target_group_id] = status == 'on'
    save_threadtb_status(threadtb_status)

    status_text = "bật" if status == 'on' else "tắt"
    response_message = f"🚦Đã {status_text} thông báo tba cho nhóm: {group_name} (ID: {target_group_id})"
    client.replyMessage(Message(text=response_message, style=styles), message_object, thread_id, thread_type, ttl=30000)

def TQD():
    return {
        'tbao': handle_tba_command,
        'threadtb': handle_threadtb_command
    }