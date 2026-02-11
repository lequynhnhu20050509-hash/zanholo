import json
import os
import random
import time
from zlapi.models import Message, Mention
from threading import Lock
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from config import PREFIX

FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
CACHE_DIR = "modules/cache/bcmd_temp"
os.makedirs(CACHE_DIR, exist_ok=True)


def get_font(size):
    return ImageFont.truetype(FONT_PATH, size)


def fetch_avatar(client, user_id, size=90):
    try:
        info = client.fetchUserInfo(user_id)
        url = info.changed_profiles.get(str(user_id), {}).get('avatar', None)
        if url:
            resp = requests.get(url, timeout=5)
            img = Image.open(
                BytesIO(
                    resp.content)).convert("RGBA").resize(
                (size, size))
            mask = Image.new("L", (size, size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, size, size), fill=255)
            img.putalpha(mask)
            return img
    except Exception:
        pass
    img = Image.new("RGBA", (size, size), (220, 80, 90, 255))
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return img


def wrap_text_with_newlines(text, font, max_width):
    lines = []
    for paragraph in text.split('\n'):
        words = paragraph.split()
        line = ""
        for word in words:
            test_line = line + (" " if line else "") + word
            if font.getlength(test_line) > max_width and line:
                lines.append(line)
                line = word
            else:
                line = test_line
        if line:
            lines.append(line)
    return lines


def draw_bcmd_list_image(client, thread_id, bcmd_data):
    user_cmd = bcmd_data.get(thread_id, {})
    num_users = len(user_cmd)
    base_height = 420
    per_user_height = 112
    min_height = base_height
    total_user_height = num_users * per_user_height
    HEIGHT = max(min_height, 210 + total_user_height + 120)
    WIDTH = 920
    bg = Image.new("RGBA", (WIDTH, HEIGHT), (30, 27, 37, 255))
    draw = ImageDraw.Draw(bg)
    font_title = get_font(42)
    font_item = get_font(27)
    font_id = get_font(20)
    font_cmd = get_font(23)
    font_info = get_font(22)
    card_x, card_y = 40, 48
    card_w, card_h = WIDTH-2*card_x, HEIGHT-2*card_y
    draw.rounded_rectangle([card_x,
                            card_y,
                            card_x+card_w,
                            card_y+card_h],
                           radius=32,
                           fill=(42,
                                 37,
                                 52,
                                 245),
                           outline=(220,
                                    80,
                                    90),
                           width=4)

    title = "DANH SÁCH CẤM LỆNH"
    draw.text((WIDTH//2 - font_title.getlength(title)//2, card_y+24),
              title, font=font_title, fill=(255, 230, 230))

    y = card_y + 92
    if not user_cmd:
        draw.text(
            (card_x+50,
             y+10),
            "Nhóm này sạch sẽ, không ai bị cấm lệnh cả! ✨",
            font=font_item,
            fill=(
                255,
                200,
                200))
        y += 52
    else:
        for user_id, cmds in user_cmd.items():
            av = fetch_avatar(client, user_id, 90)
            bg.alpha_composite(av, (card_x+33, y))
            try:
                info = client.fetchUserInfo(user_id)
                name = info.changed_profiles.get(
                    str(user_id), {}).get(
                    'zaloName', 'Không xác định')
            except Exception:
                name = "Không xác định"
            name_show = name if len(name) <= 22 else name[:20] + "…"
            draw.text((card_x+145, y+12), name_show,
                      font=font_item, fill=(255, 255, 255))
            draw.text(
                (card_x+145,
                 y+45),
                f"ID: {user_id}",
                font=font_id,
                fill=(
                    255,
                    180,
                    180))
            draw.text((card_x+145, y+68), "Lệnh cấm:",
                      font=font_cmd, fill=(255, 120, 120))
            cmd_str = ", ".join(cmds) if cmds else "-"
            cmd_lines = wrap_text_with_newlines(cmd_str, font_cmd, card_w-180)
            cy = y+94
            for line in cmd_lines:
                draw.text((card_x+145, cy), line,
                          font=font_cmd, fill=(255, 210, 210))
                cy += font_cmd.size + 2
            y += per_user_height

    footer_texts = [
        f"cách dùng: {PREFIX}bcmd <lệnh> @user\nunbcmd <lệnh> @user",
        "Chỉ admin Latte và đệ anh Dương mới dùng được các lệnh này",
        "bot by Dương-Latte"
    ]
    lines1 = wrap_text_with_newlines(footer_texts[0], font_info, card_w-60)
    lines2 = wrap_text_with_newlines(footer_texts[1], font_info, card_w-60)
    lines3 = wrap_text_with_newlines(footer_texts[2], font_info, card_w-60)
    footer_total_lines = len(lines1) + len(lines2) + len(lines3)
    footer_line_height = font_info.size + 2
    footer_textblock_height = footer_total_lines * footer_line_height
    bottom_margin = 18
    last_footer_line_y = card_y+card_h-bottom_margin
    first_footer_line_y = last_footer_line_y - footer_textblock_height + 2
    line_y = first_footer_line_y - 10
    draw.line(
        (card_x+30,
         line_y,
         card_x+card_w-30,
         line_y),
        fill=(
            220,
            80,
            90),
        width=2)
    fy = first_footer_line_y
    for line in lines1:
        draw.text((card_x+40, fy), line, font=font_info, fill=(255, 210, 210))
        fy += footer_line_height
    for line in lines2:
        draw.text((card_x+40, fy), line, font=font_info, fill=(255, 180, 180))
        fy += footer_line_height
    for line in lines3:
        draw.text((card_x+40, fy), line, font=font_info, fill=(255, 230, 230))
        fy += footer_line_height

    outpath = os.path.join(
        CACHE_DIR,
        f"bcmdlist_{
            os.getpid()}_{
            int.from_bytes(
                os.urandom(3),
                'big')}.jpg")
    bg = bg.convert("RGB")
    bg.save(outpath, "JPEG", quality=100, optimize=True)
    return outpath


def draw_error_image(message, title="LỖI"):
    WIDTH, HEIGHT = 840, 490
    bg = Image.new("RGBA", (WIDTH, HEIGHT), (35, 32, 40, 255))
    draw = ImageDraw.Draw(bg)
    font_title = get_font(40)
    font_item = get_font(25)
    font_info = get_font(21)
    card_x, card_y = 34, 30
    card_w, card_h = WIDTH-2*card_x, HEIGHT-2*card_y
    draw.rounded_rectangle([card_x,
                            card_y,
                            card_x+card_w,
                            card_y+card_h],
                           radius=34,
                           fill=(60,
                                 40,
                                 57,
                                 238),
                           outline=(220,
                                    80,
                                    90),
                           width=4)
    draw.text((WIDTH//2-font_title.getlength(title)//2, card_y+20),
              title, font=font_title, fill=(255, 220, 220))

    lines = wrap_text_with_newlines(message, font_item, card_w-60)
    y = card_y+82
    for line in lines:
        draw.text((card_x+38, y), line, font=font_item, fill=(255, 220, 220))
        y += 38

    notice_text = "Vui lòng kiểm tra lại cú pháp hoặc quyền hạn!"
    wrap_notice = wrap_text_with_newlines(notice_text, font_info, card_w-40)
    botby_text = "bot by Dương-Latte"
    wrap_botby = wrap_text_with_newlines(botby_text, font_info, card_w-40)
    total_footer_lines = len(wrap_notice) + len(wrap_botby)
    y_footer = card_y+card_h-68 - (total_footer_lines-1)*font_info.size
    draw.line(
        (card_x+30,
         y_footer,
         card_x+card_w-30,
         y_footer),
        fill=(
            220,
            80,
            90),
        width=2)
    fy = y_footer + 10
    for line in wrap_notice:
        draw.text((card_x+40, fy), line, font=font_info, fill=(255, 180, 180))
        fy += font_info.size + 2
    for line in wrap_botby:
        draw.text((card_x+40, fy), line, font=font_info, fill=(255, 220, 220))
        fy += font_info.size + 2

    outpath = os.path.join(
        CACHE_DIR,
        f"error_{
            os.getpid()}_{
            int.from_bytes(
                os.urandom(3),
                'big')}.jpg")
    bg = bg.convert("RGB")
    bg.save(outpath, "JPEG", quality=100, optimize=True)
    return outpath


def draw_success_image(message, title="THÀNH CÔNG"):
    WIDTH, HEIGHT = 840, 490
    bg = Image.new("RGBA", (WIDTH, HEIGHT), (35, 32, 40, 255))
    draw = ImageDraw.Draw(bg)
    font_title = get_font(40)
    font_item = get_font(25)
    font_info = get_font(21)
    card_x, card_y = 34, 30
    card_w, card_h = WIDTH-2*card_x, HEIGHT-2*card_y
    draw.rounded_rectangle([card_x,
                            card_y,
                            card_x+card_w,
                            card_y+card_h],
                           radius=34,
                           fill=(60,
                                 40,
                                 57,
                                 238),
                           outline=(220,
                                    80,
                                    90),
                           width=4)
    draw.text((WIDTH//2-font_title.getlength(title)//2, card_y+20),
              title, font=font_title, fill=(255, 220, 220))

    lines = wrap_text_with_newlines(message, font_item, card_w-60)
    y = card_y+82
    for line in lines:
        draw.text((card_x+38, y), line, font=font_item, fill=(255, 220, 220))
        y += 38

    notice_text = "Thao tác đã được thực hiện thành công!"
    wrap_notice = wrap_text_with_newlines(notice_text, font_info, card_w-40)
    botby_text = "bot by Dương-Latte"
    wrap_botby = wrap_text_with_newlines(botby_text, font_info, card_w-40)
    total_footer_lines = len(wrap_notice) + len(wrap_botby)
    y_footer = card_y+card_h-68 - (total_footer_lines-1)*font_info.size
    draw.line(
        (card_x+30,
         y_footer,
         card_x+card_w-30,
         y_footer),
        fill=(
            220,
            80,
            90),
        width=2)
    fy = y_footer + 10
    for line in wrap_notice:
        draw.text((card_x+40, fy), line, font=font_info, fill=(255, 180, 180))
        fy += font_info.size + 2
    for line in wrap_botby:
        draw.text((card_x+40, fy), line, font=font_info, fill=(255, 220, 220))
        fy += font_info.size + 2

    outpath = os.path.join(
        CACHE_DIR,
        f"success_{
            os.getpid()}_{
            int.from_bytes(
                os.urandom(3),
                'big')}.jpg")
    bg = bg.convert("RGB")
    bg.save(outpath, "JPEG", quality=100, optimize=True)
    return outpath


class BcmdHandler:
    def __init__(self, client):
        self.client = client
        self.bcmd_file = "data/bcmd.json"
        self.bcmd_lock = Lock()
        self.bcmd_data = self.load_bcmd_data()
        self.reaction_icons = {
            'bcmd': ['🚫', '🔒', '⛔', '🛑'],
            'unbcmd': ['✅', '🔓', '✔️', '🎉'],
            'listbcmd': ['📋', '🔍', '📜', '📑'],
            'error': ['⚠️', '❗', '😓', '🚨'],
            'success': ['✅', '🎉', '✔️', '🌟']
        }

    def _send_multiple_reactions(
            self,
            message_object,
            command_type,
            thread_id,
            thread_type):
        icons = random.sample(
            self.reaction_icons.get(
                command_type, ['⚠️']), min(
                3, len(
                    self.reaction_icons.get(
                        command_type, ['⚠️']))))
        for icon in icons:
            try:
                self.client.sendReaction(
                    messageObject=message_object,
                    reactionIcon=icon,
                    thread_id=thread_id,
                    thread_type=thread_type)
                time.sleep(0.1)
            except Exception as e:
                self.client.logger.error(f"Lỗi khi gửi reaction '{icon}': {e}")

    def load_bcmd_data(self):
        try:
            if not os.path.exists(self.bcmd_file):
                with open(self.bcmd_file, "w") as f:
                    json.dump({}, f)
                return {}
            with open(self.bcmd_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.client.logger.error(f"Lỗi khi đọc file bcmd.json: {e}")
            return {}

    def save_bcmd_data(self):
        with self.bcmd_lock:
            try:
                with open(self.bcmd_file, "w") as f:
                    json.dump(self.bcmd_data, f, indent=4)
            except Exception as e:
                self.client.logger.error(f"Lỗi khi lưu file bcmd.json: {e}")

    def handle_bcmd_command(
            self,
            message_text,
            message_object,
            thread_id,
            thread_type,
            author_id):
        self._send_multiple_reactions(
            message_object, 'bcmd', thread_id, thread_type)

        # Kiểm tra quyền admin
        if str(author_id) != self.client.ADMIN and str(
                author_id) not in self.client.ADM:
            self._send_multiple_reactions(
                message_object, 'error', thread_id, thread_type)
            img = draw_error_image("Bạn không có quyền sử dụng lệnh này! Chỉ có admin Latte mới được sử dụng")
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)
            return

        # Kiểm tra cú pháp
        parts = message_text.split()
        if len(parts) < 3:
            self._send_multiple_reactions(
                message_object, 'error', thread_id, thread_type)
            img = draw_error_image(f"Cú pháp: {PREFIX}bcmd <lệnh> @user")
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)
            return

        # Kiểm tra lệnh hợp lệ
        command_name = parts[1].lower()
        if command_name not in self.client.command_handler.TQuan:
            self._send_multiple_reactions(
                message_object, 'error', thread_id, thread_type)
            img = draw_error_image(f"Lệnh '{command_name}' không tồn tại!")
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)
            return

        # Kiểm tra tag user
        tagged_users = [
            mention.uid for mention in message_object.mentions] if message_object.mentions else []
        if not tagged_users:
            self._send_multiple_reactions(
                message_object, 'error', thread_id, thread_type)
            img = draw_error_image("Vui lòng tag người dùng cần cấm lệnh!")
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)
            return

        # Kiểm tra quyền cấm admin
        if str(author_id) in self.client.ADM and str(
                self.client.ADMIN) in tagged_users:
            self._send_multiple_reactions(
                message_object, 'error', thread_id, thread_type)
            img = draw_error_image("Bạn không thể cấm lệnh của admin chính!")
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)
            return

        # Khởi tạo dữ liệu nếu chưa có
        if thread_id not in self.bcmd_data:
            self.bcmd_data[thread_id] = {}

        success_users = []
        already_banned = []

        # Thực hiện cấm lệnh
        for user_id in tagged_users:
            if user_id not in self.bcmd_data[thread_id]:
                self.bcmd_data[thread_id][user_id] = []
            if command_name not in self.bcmd_data[thread_id][user_id]:
                self.bcmd_data[thread_id][user_id].append(command_name)
                success_users.append(user_id)
            else:
                already_banned.append(user_id)

        self.save_bcmd_data()

        # Xử lý kết quả
        if success_users:
            self._send_multiple_reactions(
                message_object, 'success', thread_id, thread_type)
            img = draw_bcmd_list_image(self.client, thread_id, self.bcmd_data)
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)

            if already_banned:
                message = f"Đã cấm lệnh thành công cho {
                    len(success_users)} user.\n"
                message += f"Các user {
                    ', '.join(already_banned)} đã bị cấm lệnh này trước đó!"
                img = draw_success_image(message)
                with Image.open(img) as im:
                    width, height = im.size
                self.client.sendLocalImage(
                    img,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=width,
                    height=height,
                    ttl=120000)
                if os.path.exists(img):
                    os.remove(img)
        else:
            self._send_multiple_reactions(
                message_object, 'error', thread_id, thread_type)
            img = draw_error_image(
                f"Tất cả user đã bị cấm lệnh '{command_name}' trước đó!")
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)

    def handle_unbcmd_command(
            self,
            message_text,
            message_object,
            thread_id,
            thread_type,
            author_id):
        self._send_multiple_reactions(
            message_object, 'unbcmd', thread_id, thread_type)

        # Kiểm tra quyền admin
        if str(author_id) != self.client.ADMIN and str(
                author_id) not in self.client.ADM:
            self._send_multiple_reactions(
                message_object, 'error', thread_id, thread_type)
            img = draw_error_image("Bạn không có quyền sử dụng lệnh này! Chỉ có admin Latte mới được sử dụng")
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)
            return

        # Kiểm tra cú pháp
        parts = message_text.split()
        if len(parts) < 3:
            self._send_multiple_reactions(
                message_object, 'error', thread_id, thread_type)
            img = draw_error_image(f"Cú pháp: {PREFIX}unbcmd <lệnh> @user")
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)
            return

        # Kiểm tra lệnh hợp lệ
        command_name = parts[1].lower()
        if command_name not in self.client.command_handler.TQuan:
            self._send_multiple_reactions(
                message_object, 'error', thread_id, thread_type)
            img = draw_error_image(f"Lệnh '{command_name}' không tồn tại!")
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)
            return

        # Kiểm tra tag user
        tagged_users = [
            mention.uid for mention in message_object.mentions] if message_object.mentions else []
        if not tagged_users:
            self._send_multiple_reactions(
                message_object, 'error', thread_id, thread_type)
            img = draw_error_image("Vui lòng tag người dùng cần gỡ cấm!")
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)
            return

        # Kiểm tra quyền gỡ cấm admin
        if str(author_id) in self.client.ADM and str(
                self.client.ADMIN) in tagged_users:
            self._send_multiple_reactions(
                message_object, 'error', thread_id, thread_type)
            img = draw_error_image(
                "Bạn không thể gỡ cấm lệnh của admin chính!")
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)
            return

        # Kiểm tra dữ liệu nhóm
        if thread_id not in self.bcmd_data or not self.bcmd_data[thread_id]:
            self._send_multiple_reactions(
                message_object, 'error', thread_id, thread_type)
            img = draw_error_image("Nhóm này không có ai bị cấm lệnh!")
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)
            return

        success_users = []
        not_banned = []

        # Thực hiện gỡ cấm
        for user_id in tagged_users:
            if user_id in self.bcmd_data[thread_id] and command_name in self.bcmd_data[thread_id][user_id]:
                self.bcmd_data[thread_id][user_id].remove(command_name)
                success_users.append(user_id)
                if not self.bcmd_data[thread_id][user_id]:
                    del self.bcmd_data[thread_id][user_id]
                if not self.bcmd_data[thread_id]:
                    del self.bcmd_data[thread_id]
            else:
                not_banned.append(user_id)

        self.save_bcmd_data()

        # Xử lý kết quả
        if success_users:
            self._send_multiple_reactions(
                message_object, 'success', thread_id, thread_type)
            img = draw_bcmd_list_image(self.client, thread_id, self.bcmd_data)
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)

            if not_banned:
                message = f"Đã gỡ cấm lệnh thành công cho {
                    len(success_users)} user.\n"
                message += f"Các user {
                    ', '.join(not_banned)} không bị cấm lệnh này!"
                img = draw_success_image(message)
                with Image.open(img) as im:
                    width, height = im.size
                self.client.sendLocalImage(
                    img,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=width,
                    height=height,
                    ttl=120000)
                if os.path.exists(img):
                    os.remove(img)
        else:
            self._send_multiple_reactions(
                message_object, 'error', thread_id, thread_type)
            img = draw_error_image(
                f"Không có user nào trong danh sách được gỡ cấm lệnh '{command_name}'!")
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)

    def handle_listbcmd_command(
            self,
            message_text,
            message_object,
            thread_id,
            thread_type,
            author_id):
        self._send_multiple_reactions(
            message_object, 'listbcmd', thread_id, thread_type)

        # Kiểm tra quyền admin
        if str(author_id) != self.client.ADMIN and str(
                author_id) not in self.client.ADM:
            self._send_multiple_reactions(
                message_object, 'error', thread_id, thread_type)
            img = draw_error_image("Bạn không có quyền sử dụng lệnh này! Chỉ có admin Latte mới được sử dụng")
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)
            return

        # Kiểm tra dữ liệu nhóm
        if thread_id not in self.bcmd_data or not self.bcmd_data[thread_id]:
            self._send_multiple_reactions(
                message_object, 'success', thread_id, thread_type)
            img = draw_bcmd_list_image(self.client, thread_id, self.bcmd_data)
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000)
            if os.path.exists(img):
                os.remove(img)
            return

        self._send_multiple_reactions(
            message_object, 'success', thread_id, thread_type)
        img = draw_bcmd_list_image(self.client, thread_id, self.bcmd_data)
        with Image.open(img) as im:
            width, height = im.size
        self.client.sendLocalImage(
            img,
            thread_id=thread_id,
            thread_type=thread_type,
            width=width,
            height=height,
            ttl=120000)
        if os.path.exists(img):
            os.remove(img)

    def draw_menu_image(self):
        WIDTH, HEIGHT = 840, 490
        bg = Image.new("RGBA", (WIDTH, HEIGHT), (35, 32, 40, 255))
        draw = ImageDraw.Draw(bg)
        font_title = get_font(40)
        font_item = get_font(25)
        font_info = get_font(21)
        card_x, card_y = 34, 30
        card_w, card_h = WIDTH-2*card_x, HEIGHT-2*card_y
        draw.rounded_rectangle([card_x,
                                card_y,
                                card_x+card_w,
                                card_y+card_h],
                               radius=34,
                               fill=(60,
                                     40,
                                     57,
                                     238),
                               outline=(220,
                                        80,
                                        90),
                               width=4)
        draw.text(
            (WIDTH //
             2 -
             font_title.getlength("CẤM LỆNH NHÓM") //
             2,
             card_y +
             20),
            "CẤM LỆNH NHÓM",
            font=font_title,
            fill=(
                255,
                220,
                220))
        item_lines = [
            f"• {PREFIX}bcmd <lệnh> @user: Cấm user dùng lệnh trong nhóm",
            f"• {PREFIX}unbcmd <lệnh> @user: Gỡ cấm lệnh cho user",
            f"• {PREFIX}listbcmd: Xem toàn bộ danh sách bị cấm lệnh"
        ]
        y = card_y+82
        for s in item_lines:
            lines = wrap_text_with_newlines(s, font_item, card_w-60)
            for line in lines:
                draw.text((card_x+38, y), line,
                          font=font_item, fill=(255, 220, 220))
                y += 38
        notice_text = "Chỉ admin Latte và đệ của Dương mới dùng được các lệnh này"
        wrap_notice = wrap_text_with_newlines(
            notice_text, font_info, card_w-40)
        botby_text = "bot by Dương-Latte"
        wrap_botby = wrap_text_with_newlines(botby_text, font_info, card_w-40)
        total_footer_lines = len(wrap_notice) + len(wrap_botby)
        y_footer = card_y+card_h-68 - (total_footer_lines-1)*font_info.size
        draw.line(
            (card_x+30,
             y_footer,
             card_x+card_w-30,
             y_footer),
            fill=(
                220,
                80,
                90),
            width=2)
        fy = y_footer + 10
        for line in wrap_notice:
            draw.text((card_x+40, fy), line,
                      font=font_info, fill=(255, 180, 180))
            fy += font_info.size + 2
        for line in wrap_botby:
            draw.text((card_x+40, fy), line,
                      font=font_info, fill=(255, 220, 220))
            fy += font_info.size + 2
        outpath = os.path.join(
            CACHE_DIR, f"bcmdmenu_{
                os.getpid()}_{
                int.from_bytes(
                    os.urandom(3), 'big')}.jpg")
        bg = bg.convert("RGB")
        bg.save(outpath, "JPEG", quality=100, optimize=True)
        return outpath

    def is_command_blocked(self, command_name, user_id, thread_id):
        return (
            thread_id in self.bcmd_data and
            user_id in self.bcmd_data[thread_id] and
            command_name in self.bcmd_data[thread_id][user_id]
        )
