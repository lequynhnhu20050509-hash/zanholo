from zlapi.models import Message, ZaloAPIException, ThreadType, Mention, MultiMention, MultiMsgStyle, MessageStyle
from config import ADMIN, PREFIX
import json
import os
import re
import logging
import time
import requests
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Tự động tham gia nhóm Zalo",
    'power': "Quản trị viên Bot"
}

def get_user_name(client, uid):
    try:
        user_info = client.fetchUserInfo(uid)
        author_info = user_info.changed_profiles.get(str(uid), {}) if user_info and user_info.changed_profiles else {}
        name = author_info.get('zaloName', 'Không xác định')
        return name
    except Exception as e:
        logger.error(f"[get_user_name] Failed to fetch name for user {uid}: {e}")
        return 'Không xác định'

class AutoJoinHandler:
    def __init__(self, client):
        self.client = client
        self.settings_file = "data/autojoin_settings.json"
        self.autojoin_enabled = self.load_autojoin_settings()
        self.cleanup_invalid_groups()
        self.start_periodic_check()

    def load_autojoin_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"[AUTOJOIN] Lỗi khi tải cài đặt autojoin: {e}")
            return {}

    def save_autojoin_settings(self):
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.autojoin_enabled, f, indent=4)
        except Exception as e:
            logger.error(f"[AUTOJOIN] Lỗi khi lưu cài đặt autojoin: {e}")

    def cleanup_invalid_groups(self):
        try:
            all_groups = set(str(group_id) for group_id in self.client.fetchAllGroups().gridVerMap.keys())
            current_settings = self.autojoin_enabled.copy()
            removed_groups = []

            for group_id in current_settings:
                if group_id not in all_groups:
                    removed_groups.append(group_id)
                    del self.autojoin_enabled[group_id]

            if removed_groups:
                logger.info(f"[AUTOJOIN] Đã xóa {len(removed_groups)} nhóm không tồn tại khỏi cài đặt: {removed_groups}")
                self.save_autojoin_settings()
        except Exception as e:
            logger.error(f"[AUTOJOIN] Lỗi khi dọn dẹp ID nhóm không tồn tại: {e}")

    def check_new_groups(self):
        try:
            all_groups = self.client.fetchAllGroups().gridVerMap.keys()
            for group_id in all_groups:
                group_id = str(group_id)
                if group_id not in self.autojoin_enabled:
                    self.on_group_joined(group_id)
        except Exception as e:
            logger.error(f"[AUTOJOIN] Lỗi khi kiểm tra nhóm mới: {e}")

    def start_periodic_check(self):
        try:
            self.check_new_groups()
            threading.Timer(300, self.start_periodic_check).start()
        except Exception as e:
            logger.error(f"[AUTOJOIN] Lỗi khi chạy kiểm tra định kỳ: {e}")

    def on_group_joined(self, group_id):
        logger.info(f"[AUTOJOIN] Đang xử lý nhóm mới với group_id: {group_id}")
        try:
            group_id = str(group_id)
            if group_id not in self.autojoin_enabled:
                all_off = all(not status for status in self.autojoin_enabled.values()) if self.autojoin_enabled else True
                self.autojoin_enabled[group_id] = not all_off
                self.save_autojoin_settings()
                status_text = "bật" if not all_off else "tắt"
                logger.info(f"[AUTOJOIN] Đã thêm nhóm mới {group_id} vào autojoin_settings.json và {status_text} autojoin.")
            else:
                logger.info(f"[AUTOJOIN] Nhóm {group_id} đã có trong autojoin_settings.json.")
        except Exception as e:
            logger.error(f"[AUTOJOIN] Lỗi khi xử lý nhóm mới {group_id}: {e}")

    def handle_autojoin_command(self, message_text, message_object, thread_id, thread_type, author_id):
        name = get_user_name(self.client, author_id)

        if author_id not in ADMIN:
            rest_text = "❌ Bạn không có quyền sử dụng lệnh này. Chỉ có admin Latte mới được sử dụng lệnh này"
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            ])
            self.client.replyMessage(
                Message(text=msg, style=styles),
                message_object, thread_id, thread_type, ttl=60000
            )
            self.client.sendReaction(message_object, "🚫", thread_id, thread_type, reactionType=75)
            return

        parts = message_text.split()
        if len(parts) < 2:
            rest_text = f"🚦 Cách dùng: {PREFIX}autojoin <on/off>"
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            ])
            self.client.replyMessage(
                Message(text=msg, style=styles),
                message_object, thread_id, thread_type, ttl=60000
            )
            self.client.sendReaction(message_object, "👉", thread_id, thread_type, reactionType=75)
            return

        action = parts[1].lower()
        if action == "on":
            try:
                all_groups = self.client.fetchAllGroups().gridVerMap.keys()
                for group_id in all_groups:
                    self.autojoin_enabled[str(group_id)] = True
                self.save_autojoin_settings()
                rest_text = f"🚦 Đã bật tự động tham gia nhóm cho tất cả {len(all_groups)} nhóm."
                msg = f"{name}\n➜{rest_text}"
                styles = MultiMsgStyle([
                    MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                    MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
                ])
                self.client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=60000
                )
                self.client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)
            except Exception as e:
                logger.error(f"[AUTOJOIN] Lỗi khi lấy danh sách nhóm: {e}")
                rest_text = f"🚦 Lỗi khi bật autojoin: {e}"
                msg = f"{name}\n➜{rest_text}"
                styles = MultiMsgStyle([
                    MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                    MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
                ])
                self.client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=60000
                )
                self.client.sendReaction(message_object, "❌", thread_id, thread_type, reactionType=75)
        elif action == "off":
            try:
                all_groups = self.client.fetchAllGroups().gridVerMap.keys()
                for group_id in all_groups:
                    self.autojoin_enabled[str(group_id)] = False
                self.save_autojoin_settings()
                rest_text = f"🚦 Đã tắt tự động tham gia nhóm cho tất cả {len(all_groups)} nhóm."
                msg = f"{name}\n➜{rest_text}"
                styles = MultiMsgStyle([
                    MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                    MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
                ])
                self.client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=60000
                )
                self.client.sendReaction(message_object, "💨", thread_id, thread_type, reactionType=75)
            except Exception as e:
                logger.error(f"[AUTOJOIN] Lỗi khi lấy danh sách nhóm: {e}")
                rest_text = f"🚦 Lỗi khi tắt autojoin: {e}"
                msg = f"{name}\n➜{rest_text}"
                styles = MultiMsgStyle([
                    MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                    MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
                ])
                self.client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=60000
                )
                self.client.sendReaction(message_object, "❌", thread_id, thread_type, reactionType=75)
        else:
            rest_text = "🤦‍♂️ Lệnh không hợp lệ. Sử dụng 'on' hoặc 'off'."
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            ])
            self.client.replyMessage(
                Message(text=msg, style=styles),
                message_object, thread_id, thread_type, ttl=60000
            )
            self.client.sendReaction(message_object, "🤦‍♂️", thread_id, thread_type, reactionType=75)

    def validate_group_link(self, group_link):
        zalo_link_pattern = r"https://zalo\.me/(g/)?([^\s]+)"
        match = re.search(zalo_link_pattern, group_link)
        if not match:
            return None
        group_code = match.group(2).strip()
        return group_code, f"https://zalo.me/g/{group_code}"

    def check_group_status(self, group_link):
        try:
            response = requests.get(group_link, timeout=5)
            if response.status_code == 200:
                return True
            logger.warning(f"[AUTOJOIN] Link nhóm trả về mã HTTP: {response.status_code}")
            return False
        except requests.RequestException as e:
            logger.error(f"[AUTOJOIN] Lỗi khi kiểm tra link nhóm: {e}")
            return False

    def check_and_join_group(self, message_text, message_object, thread_id, thread_type, author_id):
        if str(thread_id) not in self.autojoin_enabled or not self.autojoin_enabled[str(thread_id)]:
            return

        zalo_link_pattern = r"https://zalo\.me/[^\s]+"
        match = re.search(zalo_link_pattern, message_text)
        if not match:
            return

        group_link = match.group(0).strip()
        logger.info(f"[AUTOJOIN] Raw message_text: {message_text}")
        logger.info(f"[AUTOJOIN] Phát hiện link nhóm: {group_link}")

        result = self.validate_group_link(group_link)
        if not result:
            logger.warning(f"[AUTOJOIN] Link nhóm không hợp lệ: {group_link}")
            return
        group_code, standardized_link = result

        if not self.check_group_status(standardized_link):
            logger.warning(f"[AUTOJOIN] Link nhóm có thể không tồn tại hoặc không truy cập được: {standardized_link}")
            return

        max_retries = 1
        retry_delay = 2
        for attempt in range(max_retries):
            logger.info(f"[AUTOJOIN] Thử tham gia nhóm, lần {attempt + 1}/{max_retries}...")
            try:
                data_join = self.client.joinGroup(standardized_link)
                logger.info(f"[AUTOJOIN] Phản hồi từ joinGroup: {data_join}")

                if data_join and 'error_code' in data_join:
                    error_code = data_join['error_code']
                    msg_err = {
                        0: "Đã tham gia nhóm thành công!",
                        240: "Đã gửi yêu cầu tham gia, chờ duyệt.",
                        178: "Bot đã là thành viên của nhóm này.",
                        227: "Link nhóm không tồn tại.",
                        175: "Bot bị chặn trong nhóm này.",
                        1003: "Nhóm đã đầy thành viên.",
                        1004: "Giới hạn thành viên nhóm.",
                        1022: "Yêu cầu tham gia đã được gửi trước đó."
                    }
                    result_msg = msg_err.get(error_code, f"Lỗi không xác định: {data_join}")
                    logger.info(f"[AUTOJOIN] Kết quả: {result_msg}")

                    if error_code == 227:
                        logger.warning("[AUTOJOIN] Link nhóm bị báo không hợp lệ, thử mã nhóm...")
                        data_join = self.client.joinGroup(group_code)
                        if data_join.get('error_code') == 0:
                            result_msg = "Đã tham gia nhóm thành công (dùng mã nhóm)!"
                            logger.info(f"[AUTOJOIN] Kết quả: {result_msg}")
                        else:
                            logger.warning(f"[AUTOJOIN] Thử mã nhóm thất bại: {data_join}")
                            return

                    if error_code not in [0, 240, 178, 1022]:
                        return

                    if error_code == 0:
                        group_info_response = self.client.getIDsGroup(standardized_link)
                        if group_info_response and 'groupId' in group_info_response:
                            self.on_group_joined(group_info_response['groupId'])
                        else:
                            logger.error("[AUTOJOIN] Không lấy được groupId từ group_info_response.")
                        break

                else:
                    logger.error("[AUTOJOIN] Phản hồi API không hợp lệ")
                    return

            except ZaloAPIException as e:
                logger.error(f"[AUTOJOIN] Zalo API Exception (lần {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"[AUTOJOIN] Thử lại sau {retry_delay} giây...")
                    time.sleep(retry_delay)
                continue
            except Exception as e:
                logger.error(f"[AUTOJOIN] Lỗi không xác định: {e}")
                return

        if data_join.get('error_code') == 0:
            try:
                group_info_response = self.client.getIDsGroup(standardized_link)
                if not group_info_response or not isinstance(group_info_response, dict):
                    logger.error("[AUTOJOIN] Không lấy được thông tin nhóm.")
                    return

                group_id = group_info_response.get('groupId')
                if not group_id:
                    logger.error(f"[AUTOJOIN] Không tìm thấy groupId: {group_info_response}")
                    return

                admins = group_info_response.get('adminIds', [])
                creator_id = group_info_response.get('creatorId')
                if creator_id and creator_id not in admins:
                    admins.append(creator_id)
                admins = list(set(admins))

                if not admins:
                    logger.warning("[AUTOJOIN] Không tìm thấy admin nào trong nhóm.")
                    self.client.send(
                        Message(text="em là bot xin chào các admin ạ"),
                        thread_id=group_id,
                        thread_type=ThreadType.GROUP
                    )
                    logger.info(f"[AUTOJOIN] Đã gửi tin nhắn chào cơ bản tới nhóm {group_id}.")
                    return

                text = "xin chào các admin ạ"
                mentions = []
                offset = len(text)
                for admin_id in admins:
                    mention = Mention(uid=admin_id, offset=offset, length=1, auto_format=False)
                    mentions.append(mention)
                    text += "@ "
                    offset += 2

                self.client.send(
                    Message(text=text, mention=MultiMention(mentions)),
                    thread_id=group_id,
                    thread_type=ThreadType.GROUP
                )
                logger.info(f"[AUTOJOIN] Đã gửi tin nhắn chào tới nhóm {group_id}.")
            except Exception as e:
                logger.error(f"[AUTOJOIN] Lỗi khi gửi tin nhắn chào: {e}")

def TQD():
    return {
        'autojoin': AutoJoinHandler
    }