import json
import os
import time
import re
from zlapi.models import Message, ThreadType, MultiMsgStyle, MessageStyle, Mention
from config import PREFIX, ADMIN


class AntiLinkHandler:
    def __init__(self, client):
        self.client = client
        self.settings_file = "data/antilink_settings.json"
        self.whitelist_file = "data/whitelist.json"

        self.enabled_groups = self.load_settings()
        self.whitelist = self.load_whitelist()

        self.link_violations = {}     # Lưu vi phạm từng nhóm
        self.violation_window = 60    # Giây reset
        self.kick_threshold = 3       # Kick nếu quá số này
        self.warn_threshold = 2       # Cảnh báo ở mức này

    # ------------------------------
    # Kiểm tra link trong tin nhắn
    # ------------------------------
    def is_url_in_message(self, message_object):
        """
        Kiểm tra xem tin nhắn có chứa link hay không.
        Hỗ trợ:
        - Tin nhắn text
        - Tin nhắn có content dạng dict (title)
        - Domain tách kiểu: zalo . me
        """
        ignore_types = [
            'chat.sticker',
            'chat.photo',
            'chat.video.msg',
            'chat.voice',
            'chat.audio'
        ]

        if message_object.msgType in ignore_types:
            return False

        content = message_object.content

        if isinstance(content, dict):
            text_to_check = content.get('title', "")
        elif isinstance(content, str):
            text_to_check = content
        else:
            text_to_check = getattr(message_object, 'msg', "") or ""

        if not text_to_check:
            return False

        # Gom các domain kiểu bị tách dấu
        cleaned_text = re.sub(r'(\w)\s*([.,])\s*(\w)', r'\1\2\3', text_to_check)

        # Regex bắt link hợp lệ
        url_regex = re.compile(
            r"(?:https?:\/\/|www\.)\S+"
            r"|"
            r"(?<!\w)[a-zA-Z0-9-]+\s*[.,]\s*"
            r"(?:com|net|org|vn|info|biz|io|xyz|me|tv|online|"
            r"store|club|site|app|blog|dev|tech|cloud|game|"
            r"shop|click|space|asia|fun|tokyo|website)"
            r"(?:\/\S*)?(?!\w)",
            re.IGNORECASE
        )

        return bool(re.search(url_regex, cleaned_text))

    # ------------------------------
    # Load / Save settings
    # ------------------------------
    def load_settings(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        try:
            with open(self.settings_file, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_settings(self):
        with open(self.settings_file, "w") as f:
            json.dump(self.enabled_groups, f, indent=4)

    # ------------------------------
    # Load / Save whitelist
    # ------------------------------
    def load_whitelist(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        try:
            with open(self.whitelist_file, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_whitelist(self):
        with open(self.whitelist_file, "w") as f:
            json.dump(self.whitelist, f, indent=4)

    def is_whitelisted(self, thread_id, user_id):
        return str(thread_id) in self.whitelist and str(user_id) in self.whitelist[str(thread_id)]

    # ------------------------------
    # Kiểm tra trạng thái
    # ------------------------------
    def is_enabled(self, thread_id):
        return self.enabled_groups.get(str(thread_id), False)

    def get_user_name(self, uid):
        try:
            info = self.client.fetchUserInfo(uid)
            return info.changed_profiles.get(str(uid), {}).get('zaloName', str(uid))
        except:
            return str(uid)

    # ------------------------------
    # Xử lý lệnh bật/tắt Anti-Link
    # ------------------------------
    def handle_antilink_command(self, message_text, message_object, thread_id, thread_type, author_id):
        name = self.get_user_name(author_id)

        if str(author_id) not in self.client.ADMIN:
            rest_text = "⚠️ Bạn không có quyền sử dụng lệnh này. Chỉ có admin Latte mới được sử dụng"
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False)
            ])
            self.client.replyMessage(
                Message(text=msg, style=styles),
                message_object, thread_id, thread_type, ttl=60000
            )
            return

        parts = message_text.lower().split()
        action = parts[1] if len(parts) > 1 else ""

        if action not in ["on", "off"]:
            current_status = "Bật ✅" if self.is_enabled(thread_id) else "Tắt ❌"
            rest_text = f"🚦Hướng dẫn: {PREFIX}antilink <on/off>\n➜Trạng thái hiện tại: {current_status}"
            msg = f"{name}\n➜{rest_text}"

            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False)
            ])

            self.client.replyMessage(
                Message(text=msg, style=styles),
                message_object, thread_id, thread_type, ttl=60000
            )
            return

        thread_id_str = str(thread_id)

        if action == "on":
            self.enabled_groups[thread_id_str] = True
            self.save_settings()
            rest_text = f"Đã bật Anti-Link. Vi phạm {self.kick_threshold} lần/phút sẽ bị chặn."
        else:
            if thread_id_str in self.enabled_groups:
                del self.enabled_groups[thread_id_str]
            self.save_settings()
            rest_text = "Đã tắt chế độ Anti-Link."

        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False)
        ])

        self.client.replyMessage(
            Message(text=msg, style=styles),
            message_object, thread_id, thread_type, ttl=60000
        )

    # ------------------------------
    # Kiểm tra link và xử lý
    # ------------------------------
    def check_and_handle_link(self, message_object, thread_id, thread_type, author_id):

        if not self.is_enabled(thread_id):
            return False

        if str(author_id) in self.client.ADMIN:
            return False

        # CHECK WHITELIST
        if self.is_whitelisted(thread_id, author_id):
            return False

        has_violation = (
            self.is_url_in_message(message_object) or
            message_object.msgType == "chat.recommended"
        )

        if not has_violation:
            return False

        # ------------------------------------------
        # XÓA TIN NHẮN
        # ------------------------------------------
        try:
            msg_id = getattr(message_object, 'msgId', None)
            cli_msg_id = getattr(message_object, 'cliMsgId', None)
            if msg_id:
                self.client.deleteGroupMsg(msg_id, author_id, cli_msg_id, thread_id)
        except Exception as e:
            self.client.logger.error(f"[AntiLink] Lỗi xóa tin nhắn: {e}")

        # ------------------------------------------
        # GHI NHẬN VI PHẠM
        # ------------------------------------------
        now = time.time()

        if thread_id not in self.link_violations:
            self.link_violations[thread_id] = {}

        user_violations = self.link_violations[thread_id].get(
            author_id,
            {'count': 0, 'first_violation_time': now}
        )

        if now - user_violations['first_violation_time'] > self.violation_window:
            user_violations = {'count': 1, 'first_violation_time': now}
        else:
            user_violations['count'] += 1

        self.link_violations[thread_id][author_id] = user_violations
        count = user_violations['count']

        name = self.get_user_name(author_id)
        tag_author = f"{name}"
        msg = ""

        if count >= self.kick_threshold:
            try:
                self.client.blockUsersInGroup(author_id, thread_id)
                rest_text = (
                    f"📣 {tag_author} đã bị chặn khỏi nhóm do gửi link quá nhiều lần "
                    f"({count}/{self.kick_threshold})."
                )
                del self.link_violations[thread_id][author_id]
            except Exception as e:
                rest_text = f"Đã cố gắng chặn {tag_author} nhưng thất bại. Lỗi: {e}"

            msg = f"➜ [ANTI-LINK]\n{tag_author}\n➜ {rest_text}"

        elif count >= self.warn_threshold:
            rest_text = (
                f"😡 CẢNH BÁO CUỐI CÙNG! Bạn đã vi phạm {count} lần. "
                f"Thêm {self.kick_threshold - count} lần nữa sẽ bị chặn."
            )
            msg = f"➜ [ANTI-LINK]\n{tag_author}\n➜ {rest_text}"

        elif count == 1:
            rest_text = "🚦 Nhóm có quy định không được gửi link. Đây là lần nhắc nhở đầu tiên."
            msg = f"➜ [ANTI-LINK]\n{tag_author}\n➜ {rest_text}"

        if msg:
            tag_offset = msg.find(tag_author)

            styles = MultiMsgStyle([
                MessageStyle(offset=len("➜ "), length=len("[ANTI-LINK]"), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=len("➜ "), length=len("[ANTI-LINK]"), style="bold", auto_format=False)
            ])

            self.client.replyMessage(
                Message(
                    text=msg,
                    mention=Mention(uid=author_id, offset=tag_offset, length=len(tag_author)),
                    style=styles
                ),
                message_object,
                thread_id,
                thread_type,
                ttl=60000
            )

        return True
