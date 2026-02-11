import json
from zlapi.models import Message, MultiMsgStyle, MessageStyle, ThreadType
from config import PREFIX


class AntiAllHandler:
    def __init__(self, client):
        self.client = client
        self.settings_file = "data/antiall_settings.json"
        self.enabled = self.load_antiall_settings()
        self.mention_kick_threshold = 5

    def load_antiall_settings(self):
        try:
            with open(self.settings_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_antiall_settings(self):
        with open("data/antiall_settings.json", "w") as f:
            json.dump(self.enabled, f, indent=4)

    def handle_antiall_command(
            self,
            message_text,
            message_object,
            thread_id,
            thread_type,
            author_id):
        if not self.client.is_allowed_author(author_id):
            self.client.replyMessage(
                Message(text="➜ ⚠️ Bạn không có quyền sử dụng lệnh này. Chỉ admin Latte mới được sử dụng"),
                message_object, thread_id, thread_type, ttl=60000
            )
            return

        parts = message_text.split()
        if len(parts) < 2 or parts[1].lower() not in ["on", "off"]:
            current_status = "Bật ✅" if self.is_antiall_enabled(
                thread_id) else "Tắt ❌"
            self.client.replyMessage(
                Message(
                    text=f"➜ Hướng dẫn: {PREFIX}antiall <on/off>\n➜ Trạng thái hiện tại: {current_status}\n➜ Chống các hành vi tag all ẩn.\n➜ Latte"),
                message_object,
                thread_id,
                thread_type,
                ttl=60000)
            return

        action = parts[1].lower()

        if action == "on":
            if self.is_antiall_enabled(thread_id):
                msg_text = "➜ Chế độ anti-all đã được bật trước đó. 🔄"
            else:
                self.enabled[str(thread_id)] = True
                self.save_antiall_settings()
                msg_text = "➜ Đã bật chế độ anti-all, tự động chặn người dùng all ẩn! 🚦"
            self.client.replyMessage(
                Message(
                    text=msg_text),
                message_object,
                thread_id,
                thread_type,
                ttl=30000)

        elif action == "off":
            if not self.is_antiall_enabled(thread_id):
                msg_text = "➜ Chế độ anti-all đã được tắt trước đó. 🔄"
            else:
                if str(thread_id) in self.enabled:
                    del self.enabled[str(thread_id)]
                self.save_antiall_settings()
                msg_text = "➜ Đã tắt chế độ anti-all. 🎉"
            self.client.replyMessage(
                Message(
                    text=msg_text),
                message_object,
                thread_id,
                thread_type,
                ttl=30000)

    def is_antiall_enabled(self, thread_id):
        return self.enabled.get(str(thread_id), False)

    def get_username(self, user_id):
        try:
            info = self.client.fetchUserInfo(user_id)
            if info and hasattr(info, 'changed_profiles'):
                return info.changed_profiles.get(
                    str(user_id), {}).get(
                    'zaloName', str(user_id))
            return str(user_id)
        except Exception:
            return str(user_id)

    def _ban_user_and_notify(
            self,
            reason,
            author_id,
            thread_id,
            message_object):
        if self.client.is_admin(author_id, thread_id):
            return

        try:
            self.client.blockUsersInGroup(author_id, thread_id)
        except Exception as e:
            self.client.logger.error(
                f"[Anti-All] Lỗi khi ban user {author_id}: {e}")
            return

        name = self.get_username(author_id)
        msg_text = f"➜ [ANTI-ALL]\n{name} đã bị chặn khỏi nhóm do {reason}! ❌"
        styles = MultiMsgStyle(
            [
                MessageStyle(
                    offset=len("➜ "),
                    length=len("[ANTI-ALL]"),
                    style="color",
                    color="#db342e",
                    auto_format=False),
                MessageStyle(
                    offset=len("➜ "),
                    length=len("[ANTI-ALL]"),
                    style="bold",
                    auto_format=False),
            ])
        self.client.replyMessage(
            Message(text=msg_text),
            message_object, thread_id, ThreadType.GROUP, ttl=60000
        )

    def check_and_ban_if_all_hidden(
            self,
            message_object,
            thread_id,
            author_id):
        if not self.is_antiall_enabled(thread_id):
            return

        params = message_object.get('params')
        if not params and isinstance(message_object.get('content'), dict):
            params = message_object.get('content', {}).get('params')

        if isinstance(params, str):
            try:
                data = json.loads(params)
                styles = data.get("styles", [])
                if (len(styles) == 1 and
                    styles[0].get("start") == -1 and
                    styles[0].get("len", 0) > 0 and
                        styles[0].get("st") == "b"):
                    self._ban_user_and_notify(
                        "sử dụng all ẩn", author_id, thread_id, message_object)
                    return
            except (json.JSONDecodeError, TypeError):
                pass

        mentions = message_object.get('mentions')
        if isinstance(mentions, list) and len(
                mentions) >= self.mention_kick_threshold:
            self._ban_user_and_notify(
                f"tag cùng lúc {
                    len(mentions)} người",
                author_id,
                thread_id,
                message_object)
            return
