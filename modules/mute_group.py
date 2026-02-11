import json
import os
import threading
import time
import logging
from datetime import datetime, timedelta
from zlapi.models import Message, ThreadType, MultiMsgStyle, MessageStyle
from config import ADMIN, PREFIX

logger = logging.getLogger(__name__)

des = {
    'version': "2.0.2",
    'credits': "Latte",
    'description': "Tắt thông báo tất cả các nhóm hoặc tự động tắt thông báo các nhóm mới.",
    'power': "Quản trị viên Bot"
}

BASE_DIR = "modules/cache/mutegroup_configs"
STATUS_PATH = os.path.join(BASE_DIR, "automute_status.json")
DATA_PATH = os.path.join(BASE_DIR, "automute_data.json")

os.makedirs(BASE_DIR, exist_ok=True)
json_lock_mute = threading.Lock()


def load_json_mute(key):
    path = STATUS_PATH if key == "status" else DATA_PATH
    with json_lock_mute:
        if not os.path.exists(path):
            return {"enabled": False} if key == "status" else []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"enabled": False} if key == "status" else []


def save_json_mute(key, data):
    path = STATUS_PATH if key == "status" else DATA_PATH
    with json_lock_mute:
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[AutoMute] Lỗi ghi JSON {path}: {e}")


def get_user_name(client, user_id):
    try:
        user_info = client.fetchUserInfo(str(user_id))
        return user_info.changed_profiles.get(str(user_id), {}).get('zaloName', str(user_id))
    except Exception:
        return str(user_id)


def schedule_unmute_all(client, group_ids, seconds):
    def unmute_task():
        for gid in group_ids:
            try:
                client.setMute(gid, ThreadType.GROUP, is_mute=False)
            except Exception as e:
                logger.error(f"[ScheduledUnmute] Lỗi mở nhóm {gid}: {e}")

        # Xóa khỏi danh sách muted
        muted_groups = load_json_mute("data")
        updated_muted_list = [g for g in muted_groups if g not in group_ids]
        save_json_mute("data", updated_muted_list)

    t = threading.Timer(seconds, unmute_task)
    t.daemon = True
    t.start()


def auto_mute_task(client):
    status = load_json_mute("status")
    if not status.get("enabled", False):
        return

    try:
        muted_groups = load_json_mute("data")
        all_groups = client.fetchAllGroups()
        if not hasattr(all_groups, 'gridVerMap'):
            logger.info("[AutoMute] Không tìm thấy nhóm nào.")
            return

        current_group_ids = [str(gid) for gid in all_groups.gridVerMap.keys()]
        new_groups_to_mute = [gid for gid in current_group_ids if gid not in muted_groups]

        if new_groups_to_mute:
            for group_id in new_groups_to_mute:
                try:
                    client.setMute(group_id, ThreadType.GROUP, duration=-1, is_mute=True)
                    muted_groups.append(group_id)
                    time.sleep(0)
                except Exception as e:
                    logger.error(f"[AutoMute] Lỗi khi tắt thông báo nhóm {group_id}: {e}")
            save_json_mute("data", muted_groups)
        else:
            logger.info("[AutoMute] Không có nhóm mới nào để tắt thông báo.")

    except Exception as e:
        logger.error(f"[AutoMute] Lỗi trong luồng tự động: {e}")
    finally:
        reschedule_mute_task(client)


def reschedule_mute_task(client):
    status = load_json_mute("status")
    if status.get("enabled", False):
        interval = int(status.get("interval", 120))
        if hasattr(client, '_mutegroup_timer') and client._mutegroup_timer.is_alive():
            client._mutegroup_timer.cancel()
        client._mutegroup_timer = threading.Timer(interval, auto_mute_task, args=(client,))
        client._mutegroup_timer.daemon = True
        client._mutegroup_timer.start()


def start_mutegroup_scheduler(client):
    if not hasattr(client, '_mutegroup_scheduler_started') or not client._mutegroup_scheduler_started:
        reschedule_mute_task(client)
        client._mutegroup_scheduler_started = True


def handle_auto_mute(parts, client, message_object, thread_id, thread_type, author_id):
    name = get_user_name(client, author_id)
    if len(parts) < 3 or parts[2].lower() not in ['on', 'off']:
        rest_text = f"📖 Sai cú pháp. Dùng: {PREFIX}mtgroup auto on/off"
    else:
        action = parts[2].lower()
        status = load_json_mute("status")
        if action == 'on':
            if status.get("enabled", False):
                rest_text = "✨ Chế độ tự động tắt thông báo đã được bật từ trước."
            else:
                status['enabled'] = True
                save_json_mute("status", status)
                reschedule_mute_task(client)
                rest_text = "✅ Đã bật chế độ tự động tắt thông báo cho các nhóm mới."
        else:
            if not status.get("enabled", False):
                rest_text = "✨ Chế độ tự động tắt thông báo đã được tắt từ trước."
            else:
                status['enabled'] = False
                save_json_mute("status", status)
                if hasattr(client, '_mutegroup_timer') and client._mutegroup_timer.is_alive():
                    client._mutegroup_timer.cancel()
                rest_text = "❌ Đã tắt chế độ tự động tắt thông báo."

    msg = f"{name}\n➜{rest_text}"
    styles = MultiMsgStyle([
        MessageStyle(offset=0, length=len(name), style="color",
                     color="#db342e", auto_format=False),
        MessageStyle(offset=0, length=len(name),
                     style="bold", auto_format=False)
    ])
    client.replyMessage(Message(text=msg, style=styles),
                        message_object, thread_id, thread_type, ttl=60000)


def handle_mute_all(client, message_object, thread_id, thread_type, author_id, duration_arg="-1"):
    name = get_user_name(client, author_id)
    try:
        all_groups = client.fetchAllGroups()
        if not hasattr(all_groups, 'gridVerMap'):
            rest_text = "🚫 Không có nhóm nào."
        else:
            group_ids = [str(gid) for gid in all_groups.gridVerMap.keys()]
            success, fail = 0, 0
            # Tính duration
            if duration_arg == "until8am":
                now = datetime.now()
                next_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
                if now >= next_8am:
                    next_8am += timedelta(days=1)
                mute_seconds = int((next_8am - now).total_seconds())
            else:
                try:
                    mute_seconds = int(duration_arg)
                except:
                    mute_seconds = -1

            for gid in group_ids:
                try:
                    client.setMute(gid, ThreadType.GROUP, duration=mute_seconds, is_mute=True)
                    success += 1
                except Exception as e:
                    fail += 1
                    logger.error(f"[MuteAll] Lỗi nhóm {gid}: {e}")
                time.sleep(0)

            # Lưu danh sách muted
            muted_groups = load_json_mute("data")
            updated_muted_list = list(set(muted_groups + group_ids))
            save_json_mute("data", updated_muted_list)

            # Nếu duration là until8am thì schedule mở tự động
            if duration_arg == "until8am":
                schedule_unmute_all(client, group_ids, mute_seconds)

            rest_text = f"✅ Hoàn tất!\n➜ Đã mute: {success} nhóm\n➜ Thất bại: {fail}\n⏰ Chế độ: {duration_arg}"
    except Exception as e:
        rest_text = f"❌ Lỗi: {e}"

    msg = f"{name}\n➜{rest_text}"
    styles = MultiMsgStyle([
        MessageStyle(offset=0, length=len(name), style="color",
                     color="#db342e", auto_format=False),
        MessageStyle(offset=0, length=len(name), style="bold", auto_format=False)
    ])
    client.replyMessage(Message(text=msg, style=styles),
                        message_object, thread_id, thread_type, ttl=60000)


def handle_unmute_all(client, message_object, thread_id, thread_type, author_id):
    name = get_user_name(client, author_id)
    try:
        all_groups = client.fetchAllGroups()
        if not hasattr(all_groups, 'gridVerMap'):
            rest_text = "🚫 Không có nhóm nào."
        else:
            group_ids = [str(gid) for gid in all_groups.gridVerMap.keys()]
            success, fail = 0, 0
            for gid in group_ids:
                try:
                    client.setMute(gid, ThreadType.GROUP, is_mute=False)
                    success += 1
                except Exception as e:
                    fail += 1
                    logger.error(f"[UnmuteAll] Lỗi mở nhóm {gid}: {e}")
                time.sleep(0)

            muted_groups = load_json_mute("data")
            updated_muted_list = [g for g in muted_groups if g not in group_ids]
            save_json_mute("data", updated_muted_list)

            rest_text = f"🔔 Đã mở lại tất cả nhóm.\n✔ Thành công: {success}\n❌ Thất bại: {fail}"

    except Exception as e:
        logger.error(f"[UnmuteAll] Lỗi: {e}")
        rest_text = f"❌ Lỗi: {e}"

    msg = f"{name}\n➜{rest_text}"
    styles = MultiMsgStyle([
        MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
        MessageStyle(offset=0, length=len(name), style="bold", auto_format=False)
    ])
    client.replyMessage(Message(text=msg, style=styles),
                        message_object, thread_id, thread_type, ttl=60000)


def handle_mutegroup_command(message_text, message_object, thread_id, thread_type, author_id, client):
    name = get_user_name(client, author_id)

    if str(author_id) not in ADMIN:
        rest_text = "🚫 Chỉ admin bot mới có quyền sử dụng lệnh này. Chỉ có admin Latte mới được sử dụng lệnh này"
        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(name), style="color",
                         color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(name),
                         style="bold", auto_format=False)
        ])
        client.replyMessage(Message(text=msg, style=styles),
                            message_object, thread_id, thread_type, ttl=60000)
        return

    parts = message_text.lower().split()
    if len(parts) < 2:
        rest_text = f"📖 Cú pháp: {PREFIX}mtgroup all/off/auto ..."
        msg = f"{name}\n➜{rest_text}"
        client.replyMessage(Message(text=msg), message_object, thread_id, thread_type, ttl=60000)
        return

    sub_command = parts[1]

    if sub_command == "off":
        handle_unmute_all(client, message_object, thread_id, thread_type, author_id)
    elif sub_command == "all":
        duration_arg = "-1"
        if len(parts) > 2:
            duration_arg = parts[2]
        handle_mute_all(client, message_object, thread_id, thread_type, author_id, duration_arg)
    elif sub_command == "auto":
        handle_auto_mute(parts, client, message_object, thread_id, thread_type, author_id)
    else:
        rest_text = f"📖 Cú pháp: {PREFIX}mtgroup all/off/auto ..."
        msg = f"{name}\n➜{rest_text}"
        client.replyMessage(Message(text=msg), message_object, thread_id, thread_type, ttl=60000)


def TQD():
    return {
        'mtgroup': handle_mutegroup_command
    }
