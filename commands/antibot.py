import json
import os
import time
from zlapi.models import Message, ThreadType, MultiMsgStyle, MessageStyle, Mention
from config import PREFIX, ADMIN, ADM


class AntiBotHandler:
    def __init__(self, client):
        self.client = client
        self.settings_file = "data/antibot_settings.json"
        self.whitelist_file = "data/whitelist.json"

        self.enabled_groups = self.load_settings()
        self.whitelist = self.load_whitelist()

        self.violations = {}          # Lưu người vi phạm
        self.kick_threshold = 3       # Số lần cảnh báo trước khi kick
        self.detect_window = 60       # Reset đếm sau 60 giây

    # ===============================
    # TTL PARSER (s/m/h)
    # ===============================
    def convert_ttl(self, ttl_value: str) -> int:
        if isinstance(ttl_value, (int, float)):
            return int(ttl_value)

        ttl_value = str(ttl_value).strip().lower()

        if ttl_value.isdigit():
            return int(ttl_value)

        unit = ttl_value[-1]
        number = ttl_value[:-1]

        if not number.isdigit():
            raise ValueError("TTL không hợp lệ!")

        number = int(number)

        if unit == "s":
            return number * 1000
        elif unit == "m":
            return number * 60 * 1000
        elif unit == "h":
            return number * 60 * 60 * 1000
        else:
            raise ValueError("TTL phải kết thúc bằng s, m hoặc h")

    def format_ttl(self, ttl_ms):
        ttl_sec = int(ttl_ms / 1000)
        if ttl_sec < 60:
            return f"{ttl_sec}s"
        ttl_min = ttl_sec // 60
        if ttl_min < 60:
            return f"{ttl_min}m"
        ttl_hour = ttl_min // 60
        return f"{ttl_hour}h"

    # ===============================
    # SETTINGS
    # ===============================
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

    # ===============================
    # WHITELIST
    # ===============================
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

    # ===============================
    # TRẠNG THÁI BẬT/TẮT
    # ===============================
    def is_enabled(self, thread_id):
        return self.enabled_groups.get(str(thread_id), False)

    def get_user_name(self, uid):
        try:
            info = self.client.fetchUserInfo(uid)
            return info.changed_profiles.get(str(uid), {}).get("zaloName", str(uid))
        except:
            return str(uid)

    # ===============================
    # COMMAND: ON / OFF
    # ===============================
    def handle_antibot_command(self, message_text, message_object, thread_id, thread_type, author_id):
        name = self.get_user_name(author_id)

        if str(author_id) not in self.client.ADMIN and str(author_id) not in getattr(self.client, "ADM", []):
            msg = f"{name}\n➜⚠️ Bạn không có quyền dùng lệnh này. Chỉ có admin Latte mới được sử dụng"
            styles = MultiMsgStyle([
               MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
               MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False)
            ])
            self.client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=60000)
            return

        parts = message_text.lower().split()
        action = parts[1] if len(parts) > 1 else ""
        thread_str = str(thread_id)

        if action not in ["on", "off"]:
            status = "Bật ✅" if self.is_enabled(thread_id) else "Tắt ❌"
            msg = (
                f"{name}\n"
                f"➜⚙️ Dùng: {PREFIX}antibot <on/off>\n"
                f"➜ Trạng thái hiện tại: {status}"
            )
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(name), style="color", color="#db342e"),
                MessageStyle(offset=0, length=len(name), style="bold")
            ])
            self.client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=60000)
            return

        if action == "on":
            if self.is_enabled(thread_str):
                msg = f"{name}\n➜⚠️ AntiBot đã bật từ trước."
            else:
                self.enabled_groups[thread_str] = True
                self.save_settings()
                msg = f"{name}\n➜🛡️ AntiBot đã bật.\nHệ thống sẽ auto cảnh báo/kick bot."
        else:
            if not self.is_enabled(thread_str):
                msg = f"{name}\n➜⚠️ AntiBot đã tắt từ trước."
            else:
                del self.enabled_groups[thread_str]
                self.save_settings()
                msg = f"{name}\n➜❌ AntiBot đã tắt."

        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
            MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False)
        ])
        self.client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=60000)

    # ===============================
    # CHECK MESSAGE & XỬ LÝ VI PHẠM
    # ===============================
    def check_and_handle_message(self, message_object, thread_id, thread_type, author_id):
        if not self.is_enabled(thread_id) or thread_type != ThreadType.GROUP:
            return False

        if str(author_id) in self.client.ADMIN or str(author_id) in getattr(self.client, "ADM", []):
            return False

        # Bỏ qua whitelist
        if self.is_whitelisted(thread_id, author_id):
            return False

        ttl = getattr(message_object, "ttl", 0)
        try:
            ttl = self.convert_ttl(ttl)
        except:
            pass

        if ttl == 0:
            return False

        ttl_text = self.format_ttl(ttl)

        # XÓA TIN NHẮN
        try:
            msg_id = getattr(message_object, "msgId", None) or message_object.get("msgId")
            cli_msg_id = getattr(message_object, "cliMsgId", None) or message_object.get("cliMsgId")
            if msg_id:
                self.client.deleteGroupMsg(msg_id, author_id, cli_msg_id if cli_msg_id else None, thread_id)
        except Exception as e:
            self.client.logger.error(f"[AntiBot] Lỗi xóa tin nhắn: {e}")

        # XỬ LÝ VI PHẠM
        now = time.time()
        thread_str = str(thread_id)
        if thread_str not in self.violations:
            self.violations[thread_str] = {}

        data = self.violations[thread_str].get(author_id, {"count": 0, "time": now})
        if now - data["time"] > self.detect_window:
            data = {"count": 1, "time": now}
        else:
            data["count"] += 1
        self.violations[thread_str][author_id] = data

        name = self.get_user_name(author_id)
        count = data["count"]
        tag_author = f"{name}"
        msg = ""

        if count >= self.kick_threshold:
            try:
                self.client.blockUsersInGroup(author_id, thread_id)
                msg = (
                    f"➜ [ANTI-BOT]\n"
                    f"➜ {tag_author} gửi tin có TTL – nghi bot.\n"
                    f"📌 TTL: {ttl_text}\n"
                    f"🚫 Đã kick khỏi nhóm."
                )
                del self.violations[thread_str][author_id]
            except Exception as e:
                msg = (
                    f"➜ [ANTI-BOT]\n"
                    f"➜ {tag_author} gửi tin có TTL – nghi bot.\n"
                    f"📌 TTL: {ttl_text}\n"
                    f"⚙️ Bot không có quyền kick. Lỗi: {e}"
                )
        else:
            msg = (
                f"➜ [ANTI-BOT]\n"
                f"➜ {tag_author} cảnh báo ({count}/{self.kick_threshold}).\n"
                f"📌 TTL phát hiện: {ttl_text}\n"
            )

        if msg:
            tag_offset = msg.find(tag_author)

            styles = MultiMsgStyle([
                MessageStyle(offset=len("➜ "), length=len("[ANTI-BOT]"), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=len("➜ "), length=len("[ANTI-BOT]"), style="bold", auto_format=False)
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
