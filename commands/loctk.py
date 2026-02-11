from zlapi.models import Message, MultiMsgStyle, MessageStyle
from logging_utils import Logging
from config import PREFIX
logger = Logging()


class LocTKHandler:
    def __init__(self, client):
        self.client = client

    def handle_loctk_command(
            self,
            message,
            message_object,
            thread_id,
            thread_type,
            author_id):
        command = message.lower().split()
        user_info = self.client.fetchUserInfo(author_id)
        author_info = user_info.changed_profiles.get(
            str(author_id), {}) if user_info and user_info.changed_profiles else {}
        name = author_info.get('zaloName', 'Không xác định')

        if len(command) < 2:
            rest_text = f"❌ Ủa zalo? Dùng lệnh {PREFIX}cam on/off/add/remove/list nha bro! 😉"
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
                        auto_format=False),
                ])
            self.client.replyMessage(
                Message(text=msg, style=styles),
                message_object, thread_id, thread_type, ttl=30000
            )
            self.client.sendReaction(
                message_object,
                "👍",
                thread_id,
                thread_type,
                reactionType=75)
            return

        if str(author_id) not in self.client.ADMIN:
            rest_text = "Ê ê! Quyền lực này không thuộc về bạn rồi? Chỉ có admin Latte mới được sử dụng 🤨"
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
                        auto_format=False),
                ])
            self.client.replyMessage(
                Message(text=msg, style=styles),
                message_object, thread_id, thread_type, ttl=30000
            )
            self.client.sendReaction(
                message_object,
                "🚫",
                thread_id,
                thread_type,
                reactionType=75)
            return

        action = command[1]
        current_state = self.client.loctk_enabled.get(thread_id, False)

        if action == 'on':
            if current_state:
                rest_text = "Chế độ lọc từ cấm đã bật sẵn rồi mà! 🛡️"
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
                            auto_format=False),
                    ])
                self.client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=30000
                )
                self.client.sendReaction(
                    message_object,
                    "🔄",
                    thread_id,
                    thread_type,
                    reactionType=75)
            else:
                self.client.loctk_enabled[thread_id] = True
                rest_text = "Đã bật chế độ lọc từ cấm rồi đó! 🛡️"
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
                            auto_format=False),
                    ])
                self.client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=30000
                )
                self.client.sendReaction(
                    message_object,
                    "✅",
                    thread_id,
                    thread_type,
                    reactionType=75)
        elif action == 'off':
            if not current_state:
                rest_text = "Chế độ lọc từ cấm đã tắt sẵn rồi! 🚨"
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
                            auto_format=False),
                    ])
                self.client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=30000
                )
                self.client.sendReaction(
                    message_object,
                    "🔄",
                    thread_id,
                    thread_type,
                    reactionType=75)
            else:
                self.client.loctk_enabled[thread_id] = False
                rest_text = " đã tắt lọc từ cấm rồi nha! 🚨"
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
                            auto_format=False),
                    ])
                self.client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=30000
                )
                self.client.sendReaction(
                    message_object,
                    "❌",
                    thread_id,
                    thread_type,
                    reactionType=75)
        elif action == 'add':
            if len(command) < 3:
                rest_text = f"🚨 Thêm từ kiểu gì? Dùng {PREFIX}cam add <từ cần thêm> chứ! 🙄"
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
                            auto_format=False),
                    ])
                self.client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=30000
                )
                self.client.sendReaction(
                    message_object,
                    "👉",
                    thread_id,
                    thread_type,
                    reactionType=75)
                return
            word_to_add = " ".join(command[2:])

            if word_to_add in self.client.banned_words:
                rest_text = f" từ '{word_to_add}' đã có trong danh sách cấm rồi! 🔄"
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
                            auto_format=False),
                    ])
                self.client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=30000
                )
                self.client.sendReaction(
                    message_object,
                    "🔄",
                    thread_id,
                    thread_type,
                    reactionType=75)
            else:
                self.client.banned_words.append(word_to_add)
                self.client.save_banned_words()
                rest_text = f" đã thêm từ cấm: '{word_to_add}' rồi nha! 👍"
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
                            auto_format=False),
                    ])
                self.client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=30000
                )
                self.client.sendReaction(
                    message_object,
                    "✅",
                    thread_id,
                    thread_type,
                    reactionType=75)
        elif action == 'remove':
            if len(command) < 3:
                rest_text = f"🚨 Xóa từ kiểu gì? Dùng {PREFIX}cam remove <từ cần xóa> mới đúng! 🙄"
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
                            auto_format=False),
                    ])
                self.client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=30000
                )
                self.client.sendReaction(
                    message_object,
                    "👉",
                    thread_id,
                    thread_type,
                    reactionType=75)
                return
            word_to_remove = " ".join(command[2:])
            if word_to_remove in self.client.banned_words:
                self.client.banned_words.remove(word_to_remove)
                self.client.save_banned_words()
                rest_text = f" đã xóa từ cấm: '{word_to_remove}' rồi nè! 👌"
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
                            auto_format=False),
                    ])
                self.client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=30000
                )
                self.client.sendReaction(
                    message_object,
                    "✅",
                    thread_id,
                    thread_type,
                    reactionType=75)
            else:
                rest_text = "🚨 Tìm mỏi mắt không thấy từ này trong danh sách cấm luôn á! 🤷‍♂️"
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
                            auto_format=False),
                    ])
                self.client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=30000
                )
                self.client.sendReaction(
                    message_object,
                    "❓",
                    thread_id,
                    thread_type,
                    reactionType=75)
        elif action == 'list':
            if not self.client.banned_words:
                rest_text = "🚨 Danh sách từ cấm đang trắng tinh luôn! ✨"
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
                            auto_format=False),
                    ])
                self.client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=30000
                )
                self.client.sendReaction(
                    message_object,
                    "✅",
                    thread_id,
                    thread_type,
                    reactionType=75)
            else:
                banned_words_list = "\n".join(
                    f"• {word}" for word in self.client.banned_words)
                rest_text = f"🚦 Đây là sương sương list từ cấm nè:\n{banned_words_list}"
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
                            auto_format=False),
                    ])
                self.client.replyMessage(
                    Message(text=msg, style=styles),
                    message_object, thread_id, thread_type, ttl=60000
                )
                self.client.sendReaction(
                    message_object,
                    "📜",
                    thread_id,
                    thread_type,
                    reactionType=75)
        else:
            rest_text = f"❌ Sai lệnh rồi cha ơi! Dùng {PREFIX}cam on/off/add/remove/list kìa! 🙄"
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
                        auto_format=False),
                ])
            self.client.replyMessage(
                Message(text=msg, style=styles),
                message_object, thread_id, thread_type, ttl=30000
            )
            self.client.sendReaction(
                message_object,
                "🤦‍♂️",
                thread_id,
                thread_type,
                reactionType=75)

        self.client.save_loctk_settings()
