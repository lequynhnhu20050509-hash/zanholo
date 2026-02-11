import json
import os
import time
from zlapi.models import Message, ThreadType, MultiMsgStyle, MessageStyle, Mention
from config import PREFIX


class AntiVideoHandler:
    def __init__(self, client):
        self.client = client
        self.settings_file = "data/antivideo_settings.json"
        self.enabled_groups = self.load_settings()
        self.video_violations = {}
        self.violation_window = 10
        self.kick_threshold = 5
        self.warn_threshold = 3

    def load_settings(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        try:
            with open(self.settings_file, "r", encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_settings(self):
        with open(self.settings_file, "w", encoding='utf-8') as f:
            json.dump(self.enabled_groups, f, indent=4, ensure_ascii=False)

    def is_enabled(self, thread_id):
        return self.enabled_groups.get(str(thread_id), False)

    def get_user_name(self, uid):
        try:
            user_info = self.client.fetchUserInfo(uid)
            return user_info.changed_profiles.get(
                str(uid), {}).get(
                'zaloName', str(uid))
        except Exception:
            return str(uid)

    def handle_antivideo_command(
            self,
            message_text,
            message_object,
            thread_id,
            thread_type,
            author_id):
        name = self.get_user_name(author_id)

        if str(author_id) not in self.client.ADMIN:
            rest_text = "⚠️ Chỉ admin Latte hoặc QTV nhóm mới có quyền sử dụng lệnh này."
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle(
                [
                    MessageStyle(
                        offset=0,
                        length=len(name),
                        style="color",
                        color="#db342e",
                        auto_format=False),
                    MessageStyle(
                        offset=0,
                        length=len(name),
                        style="bold",
                        auto_format=False)])
            self.client.replyMessage(
                Message(
                    text=msg,
                    style=styles),
                message_object,
                thread_id,
                thread_type,
                ttl=60000)
            for r_icon in ["❌", "🚫", "🔐"]:
                self.client.sendReaction(
                    message_object,
                    r_icon,
                    thread_id,
                    thread_type,
                    reactionType=75)
            return

        parts = message_text.lower().split()
        if len(parts) < 2 or parts[1] not in ["on", "off"]:
            current_status = "Bật ✅" if self.is_enabled(thread_id) else "Tắt ❌"
            rest_text = f"🚦Hướng dẫn: {PREFIX}antivideo <on/off>\n➜Trạng thái hiện tại: {current_status}"
            msg = f"{name}\n➜{rest_text}"
            styles = MultiMsgStyle(
                [
                    MessageStyle(
                        offset=0,
                        length=len(name),
                        style="color",
                        color="#db342e",
                        auto_format=False),
                    MessageStyle(
                        offset=0,
                        length=len(name),
                        style="bold",
                        auto_format=False)])
            self.client.replyMessage(
                Message(
                    text=msg,
                    style=styles),
                message_object,
                thread_id,
                thread_type,
                ttl=60000)
            for r_icon in ["👉", "📜", "ℹ️"]:
                self.client.sendReaction(
                    message_object,
                    r_icon,
                    thread_id,
                    thread_type,
                    reactionType=75)
            return

        action = parts[1]
        thread_id_str = str(thread_id)

        if action == "on":
            if self.is_enabled(thread_id_str):
                rest_text = "Chế độ Anti-Video đã được bật trước đó. 🔄"
                reactions = ["⚠️", "🛡️", "📹"]
            else:
                self.enabled_groups[thread_id_str] = True
                self.save_settings()
                rest_text = f"Đã bật Anti-Video. Vi phạm {
                    self.kick_threshold} lần/10s sẽ bị chặn. 🛡️"
                reactions = ["✅", "🛡️", "📹"]
        else:
            if not self.is_enabled(thread_id_str):
                rest_text = "Chế độ Anti-Video đã được tắt trước đó. 🔄"
                reactions = ["⚠️", "📹", "🔓"]
            else:
                if thread_id_str in self.enabled_groups:
                    del self.enabled_groups[thread_id_str]
                self.save_settings()
                rest_text = "Đã tắt chế độ Anti-Video. 🔓"
                reactions = ["🚫", "📹", "🔓"]

        msg = f"{name}\n➜{rest_text}"
        styles = MultiMsgStyle([MessageStyle(offset=0,
                                             length=len(name),
                                             style="color",
                                             color="#db342e",
                                             auto_format=False),
                                MessageStyle(offset=0,
                                             length=len(name),
                                             style="bold",
                                             auto_format=False)])
        self.client.replyMessage(
            Message(
                text=msg,
                style=styles),
            message_object,
            thread_id,
            thread_type,
            ttl=60000)
        for r_icon in reactions:
            self.client.sendReaction(
                message_object,
                r_icon,
                thread_id,
                thread_type,
                reactionType=75)

    def check_antivideo(
            self,
            message_object,
            thread_id,
            thread_type,
            author_id):
        if not self.is_enabled(thread_id) or not message_object.get(
            'msgType', '').startswith('chat.video.msg') or self.client.is_group_admin(
            thread_id, author_id) or (
            str(thread_id) in self.client.whitelist and str(author_id) in self.client.whitelist.get(
                str(thread_id), [])):
            return False

        try:
            msg_id, cli_msg_id = message_object.get(
                'msgId'), message_object.get('cliMsgId')
            if msg_id:
                self.client.deleteGroupMsg(
                    msg_id, author_id, cli_msg_id, thread_id)
        except Exception as e:
            self.client.logger.error(f"[AntiVideo] Lỗi khi xóa video: {e}")
            return False

        now = time.time()
        self.video_violations.setdefault(thread_id, {})
        user_violations = self.video_violations[thread_id].get(
            author_id, {'count': 0, 'first_violation_time': now})

        if now - \
                user_violations['first_violation_time'] > self.violation_window:
            user_violations = {'count': 1, 'first_violation_time': now}
        else:
            user_violations['count'] += 1

        self.video_violations[thread_id][author_id] = user_violations
        count = user_violations['count']

        name = self.get_user_name(author_id)
        tag_author = f"{name}"
        msg = ""

        if count >= self.kick_threshold:
            try:
                self.client.blockUsersInGroup(author_id, thread_id)
                rest_text = f"📣 {tag_author} đã bị chặn khỏi nhóm do spam video liên tục ({count}/{
                    self.kick_threshold} video)."
                self.video_violations[thread_id].pop(author_id, None)
            except Exception as e:
                rest_text = f"Đã cố gắng chặn {tag_author} nhưng thất bại. Lỗi: {e}"
            msg = f"[ANTI-VIDEO]\n{tag_author}\n{rest_text}"
        elif count == self.warn_threshold:
            rest_text = f"😡 CẢNH BÁO CUỐI CÙNG! bạn đã vi phạm {count} lần. Thêm {
                self.kick_threshold - count} lần nữa sẽ bị chặn."
            msg = f"[ANTI-VIDEO]\n{tag_author}\n{rest_text}"
        elif count == 1:
            rest_text = f"🚦 Nhóm chúng tôi có quy định không được gửi video vào nhóm, vui lòng không gửi video vào nhóm. Đây là lần nhắc nhở đầu tiên."
            msg = f"[ANTI-VIDEO]\n{tag_author}\n{rest_text}"

        if msg:
            styles = MultiMsgStyle(
                [
                    MessageStyle(
                        offset=0,
                        length=len("[ANTI-VIDEO]"),
                        style="color",
                        color="#db342e",
                        auto_format=False),
                    MessageStyle(
                        offset=0,
                        length=len("[ANTI-VIDEO]"),
                        style="bold",
                        auto_format=False),
                    MessageStyle(
                        offset=len("[ANTI-VIDEO]\n"),
                        length=len(tag_author),
                        style="bold",
                        auto_format=False)])
            self.client.replyMessage(
                Message(
                    text=msg,
                    mention=Mention(
                        uid=author_id,
                        offset=msg.find(tag_author),
                        length=len(tag_author)),
                    style=styles),
                message_object,
                thread_id,
                thread_type,
                ttl=120000)
        return True
