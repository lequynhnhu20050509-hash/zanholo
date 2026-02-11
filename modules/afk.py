from zlapi.models import Message, ThreadType, Mention

from config import PREFIX, ADMIN

from datetime import datetime

import json

import os

import logging



logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)



des = {

    'version': "2.0.1",

    'credits': "Latte",

    'description': "Quản lý trạng thái AFK cho người dùng, chỉ hoạt động trong nhóm.",

    'power': "Người dùng và Admin"

}



def is_admin(author_id):

    return str(author_id) in ADMIN



class AFKHandler:

    def __init__(self, client):

        self.client = client

        self.afk_file = "data/afk_data.json"

        self.afk_data = self.load_afk_data()



    def load_afk_data(self):

        try:

            if os.path.exists(self.afk_file):

                with open(self.afk_file, "r", encoding="utf-8") as f:

                    return json.load(f)

            return {}

        except Exception as e:

            logger.error(f"[AFK] Lỗi khi tải dữ liệu AFK: {e}")

            return {}



    def save_afk_data(self):

        try:

            with open(self.afk_file, "w", encoding="utf-8") as f:

                json.dump(self.afk_data, f, indent=4, ensure_ascii=False)

        except Exception as e:

            logger.error(f"[AFK] Lỗi khi lưu dữ liệu AFK: {e}")



    def handle_afk_command(self, message_text, message_object, thread_id, thread_type, author_id):

        try:

            if thread_type != ThreadType.GROUP:

                self.client.replyMessage(

                    Message(text="🚦 Lệnh AFK chỉ hoạt động trong nhóm!"),

                    message_object, thread_id, thread_type, ttl=60000

                )

                self.client.sendReaction(message_object, "🔒", thread_id, thread_type, reactionType=75)

                return



            parts = message_text.lower().split(maxsplit=2)

            command = parts[0].lstrip(PREFIX)



            if command != "afk":

                return



            if len(parts) < 2:

                self.client.replyMessage(

                    Message(text=f"🚦 Cách dùng: {PREFIX}afk <lý do>"),

                    message_object, thread_id, thread_type, ttl=60000

                )

                self.client.sendReaction(message_object, "👉", thread_id, thread_type, reactionType=75)

                return



            is_admin_user = is_admin(author_id)



            if parts[1] == "adm" and len(parts) >= 2 and parts[2].lower().strip() == "off":

                if not is_admin_user:

                    self.client.replyMessage(

                        Message(text="🚫 Lệnh AFK admin chỉ dành cho admin! Chỉ có admin Latte mới được sử dụng"),

                        message_object, thread_id, thread_type, ttl=60000

                    )

                    self.client.sendReaction(message_object, "🚫", thread_id, thread_type, reactionType=75)

                    return



                if thread_id in self.afk_data and author_id in self.afk_data[thread_id]:

                    afk_info = self.afk_data[thread_id][author_id]

                    username = afk_info['username']

                    start_time = datetime.fromisoformat(afk_info['start_time'])

                    duration = datetime.now() - start_time

                    duration_str = self.format_duration(duration)



                    del self.afk_data[thread_id][author_id]

                    if not self.afk_data[thread_id]:

                        del self.afk_data[thread_id]

                    self.save_afk_data()



                    tag = f" {username}"

                    message_content = f"🎉 Chúc mừng đại ca {tag} trở lại! Đại ca đã offline được {duration_str}."

                    offset = message_content.index(tag)

                    length = len(tag)



                    self.client.replyMessage(

                        Message(

                            text=message_content,

                            mention=Mention(author_id, length=length, offset=offset)

                        ),

                        message_object, thread_id, thread_type, ttl=60000

                    )

                    self.client.sendReaction(message_object, "🎉", thread_id, thread_type, reactionType=75)

                else:

                    self.client.replyMessage(

                        Message(text="🚦 Bạn chưa bật AFK admin!"),

                        message_object, thread_id, thread_type, ttl=60000

                    )

                    self.client.sendReaction(message_object, "❓", thread_id, thread_type, reactionType=75)

                return



            if parts[1] == "adm":

                if not is_admin_user:

                    self.client.replyMessage(

                        Message(text="🚫 Lệnh AFK admin chỉ dành cho admin! Chỉ có admin Latte mới được sử dụng"),

                        message_object, thread_id, thread_type, ttl=60000

                    )

                    self.client.sendReaction(message_object, "🚫", thread_id, thread_type, reactionType=75)

                    return



                if len(parts) < 3:

                    self.client.replyMessage(

                        Message(text=f"🚦 Cách dùng: {PREFIX}afk adm <lý do>"),

                        message_object, thread_id, thread_type, ttl=60000

                    )

                    self.client.sendReaction(message_object, "👉", thread_id, thread_type, reactionType=75)

                    return



                reason = message_text.split(maxsplit=2)[2]

                if reason.lower().strip() == "off":

                    self.client.replyMessage(

                        Message(text=f"🚦 Lý do không được là 'off'. Vui lòng dùng {PREFIX}afk adm off để tắt AFK!"),

                        message_object, thread_id, thread_type, ttl=60000

                    )

                    self.client.sendReaction(message_object, "❌", thread_id, thread_type, reactionType=75)

                    return

                afk_type = "admin"

            else:

                reason = message_text.split(maxsplit=1)[1] if len(parts) > 1 else ""

                if reason.lower().strip() == "off":

                    self.client.replyMessage(

                        Message(text=f"🚦 Lý do không được là 'off'. Vui lòng nhập lý do hợp lệ!"),

                        message_object, thread_id, thread_type, ttl=60000

                    )

                    self.client.sendReaction(message_object, "❌", thread_id, thread_type, reactionType=75)

                    return

                afk_type = "user"



            author_info = self.client.fetchUserInfo(author_id)

            author_name = author_info.changed_profiles.get(author_id, {}).get('zaloName', 'không xác định')



            if thread_id not in self.afk_data:

                self.afk_data[thread_id] = {}



            self.afk_data[thread_id][author_id] = {

                'reason': reason,

                'start_time': datetime.now().isoformat(),

                'username': author_name,

                'type': afk_type

            }

            self.save_afk_data()



            tag = f"{author_name}"

            message_content = f"✅ {tag} đã bật AFK {'admin' if afk_type == 'admin' else ''}với lý do \n➜ {reason}"

            offset = message_content.index(tag)

            length = len(tag)



            self.client.replyMessage(

                Message(text=message_content, mention=Mention(author_id, length=length, offset=offset)),

                message_object, thread_id, thread_type, ttl=60000

            )

            self.client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

        except Exception as e:

            logger.error(f"[AFK] Lỗi khi xử lý lệnh afk: {e}")

            self.client.replyMessage(

                Message(text=f"❌ Lỗi khi bật AFK: {e}"),

                message_object, thread_id, thread_type, ttl=60000

            )

            self.client.sendReaction(message_object, "⚠️", thread_id, thread_type, reactionType=75)



    def check_afk_mention(self, message_object, thread_id, thread_type):

        try:

            if thread_type != ThreadType.GROUP or not message_object.mentions:

                return



            for mention in message_object.mentions:

                user_id = mention.uid

                if thread_id in self.afk_data and user_id in self.afk_data[thread_id]:

                    afk_info = self.afk_data[thread_id][user_id]

                    start_time = datetime.fromisoformat(afk_info['start_time'])

                    duration = datetime.now() - start_time

                    duration_str = self.format_duration(duration)

                    username = afk_info['username']

                    reason = afk_info['reason']

                    afk_type = afk_info.get('type', 'user')



                    tag = f"{username}"

                    prefix = "Admin " if afk_type == "admin" else ""

                    message_content = f"🚦Hiện tại {prefix}{tag} đang offline \nLý do là:\n➜{reason}\n➜ và đã offline được\n ⏰️ {duration_str}."

                    offset = message_content.index(tag)

                    length = len(tag)



                    self.client.sendMessage(

                        Message(

                            text=message_content,

                            mention=Mention(user_id, length=length, offset=offset)

                        ),

                        thread_id, thread_type, ttl=60000

                    )

                    self.client.sendReaction(message_object, "ℹ️", thread_id, thread_type, reactionType=75)

        except Exception as e:

            logger.error(f"[AFK] Lỗi khi kiểm tra mention AFK: {e}")



    def check_afk_return(self, author_id, thread_id, thread_type, message_object):

        try:

            if thread_type != ThreadType.GROUP:

                logger.debug(f"[AFK] Không xử lý AFK return vì không phải nhóm: thread_type={thread_type}")

                return False



            if thread_id not in self.afk_data or author_id not in self.afk_data[thread_id]:

                logger.debug(f"[AFK] Không tìm thấy AFK data: thread_id={thread_id}, author_id={author_id}")

                return False



            afk_info = self.afk_data[thread_id][author_id]

            afk_type = afk_info.get('type', 'user')

            logger.debug(f"[AFK] Kiểm tra AFK return: author_id={author_id}, afk_type={afk_type}")



            if afk_type == "admin":

                logger.debug(f"[AFK] Bỏ qua AFK return vì là admin: author_id={author_id}")

                return False



            username = afk_info['username']

            start_time = datetime.fromisoformat(afk_info['start_time'])

            duration = datetime.now() - start_time

            duration_str = self.format_duration(duration)

            logger.info(f"[AFK] Người dùng thường trở lại: author_id={author_id}, username={username}, offline={duration_str}")



            del self.afk_data[thread_id][author_id]

            if not self.afk_data[thread_id]:

                del self.afk_data[thread_id]

            self.save_afk_data()



            tag = f"{username} "

            message_content = f"🎉 Chúc mừng  {tag}trở lại! Bạn đã offline được\n➜{duration_str}."

            offset = message_content.index(tag)

            length = len(tag)



            self.client.replyMessage(

                Message(

                    text=message_content,

                    mention=Mention(author_id, length=length, offset=offset)

                ),

                message_object, thread_id, thread_type, ttl=60000

            )

            self.client.sendReaction(message_object, "🎉", thread_id, thread_type, reactionType=75)

            logger.info(f"[AFK] Đã gửi thông báo chúc mừng cho {username}")

            return True

        except Exception as e:

            logger.error(f"[AFK] Lỗi khi kiểm tra người dùng trở lại: {e}")

            return False



    def format_duration(self, duration):

        total_seconds = int(duration.total_seconds())

        days = total_seconds // (24 * 3600)

        hours = (total_seconds % (24 * 3600)) // 3600

        minutes = (total_seconds % 3600) // 60

        seconds = total_seconds % 60



        parts = []

        if days > 0:

            parts.append(f"{days} ngày")

        if hours > 0:

            parts.append(f"{hours} giờ")

        if minutes > 0:

            parts.append(f"{minutes} phút")

        if seconds > 0 or not parts:

            parts.append(f"{seconds} giây")

        return " ".join(parts)



def TQD():

    return {

        'afk': AFKHandler

    }