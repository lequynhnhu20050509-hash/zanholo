import os
import random
import time
from zlapi.models import Message, ThreadType
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from logging_utils import Logging
from config import PREFIX

logger = Logging()

FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
CACHE_DIR = "modules/cache/whitelist_temp"
os.makedirs(CACHE_DIR, exist_ok=True)


def get_font(size):
    return ImageFont.truetype(FONT_PATH, size)


def fetch_avatar(client, user_id, size=96):
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
    img = Image.new("RGBA", (size, size), (40, 120, 255, 255))
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


def draw_whitelist_image(client, thread_id, whitelist):
    base_height = 390
    per_user_height = 112
    min_height = base_height
    total_user_height = len(whitelist) * per_user_height
    HEIGHT = max(min_height, 200 + total_user_height + 120)
    WIDTH = 900
    bg = Image.new("RGBA", (WIDTH, HEIGHT), (24, 27, 37, 255))
    draw = ImageDraw.Draw(bg)
    font_title = get_font(44)
    font_item = get_font(28)
    font_id = get_font(21)
    font_info = get_font(24)
    card_x, card_y = 38, 48
    card_w, card_h = WIDTH-2*card_x, HEIGHT-2*card_y
    draw.rounded_rectangle([card_x,
                            card_y,
                            card_x+card_w,
                            card_y+card_h],
                           radius=32,
                           fill=(31,
                                 37,
                                 52,
                                 245),
                           outline=(70,
                                    185,
                                    255),
                           width=4)

    title = "WHITELIST"
    draw.text((WIDTH//2 - font_title.getlength(title)//2, card_y+22),
              title, font=font_title, fill=(240, 255, 255))

    y = card_y + 90
    if not whitelist:
        draw.text((card_x+48, y+10), "WHITELIST đang TRỐNG!",
                  font=font_item, fill=(200, 210, 230))
        y += 50
    else:
        for user_id in whitelist:
            av = fetch_avatar(client, user_id, 96)
            bg.alpha_composite(av, (card_x+32, y))
            try:
                info = client.fetchUserInfo(user_id)
                name = info.changed_profiles.get(
                    str(user_id), {}).get(
                    'zaloName', 'Không xác định')
            except Exception:
                name = "Không xác định"
            name_show = name if len(name) <= 22 else name[:20] + "…"
            draw.text((card_x+150, y+10), name_show,
                      font=font_item, fill=(255, 255, 255))
            draw.text(
                (card_x+150,
                 y+46),
                f"ID: {user_id}",
                font=font_id,
                fill=(
                    175,
                    210,
                    255))
            y += per_user_height

    footer_texts = [
        "Thao tác: add, remove, list",
        "Chỉ admin Latte mới sử dụng được các lệnh này",
        "Latte by T K D"
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
            70,
            185,
            255),
        width=2)

    fy = first_footer_line_y
    for line in lines1:
        draw.text((card_x+40, fy), line, font=font_info, fill=(180, 220, 250))
        fy += footer_line_height
    for line in lines2:
        draw.text((card_x+40, fy), line, font=font_info, fill=(255, 180, 180))
        fy += footer_line_height
    for line in lines3:
        draw.text((card_x+40, fy), line, font=font_info, fill=(220, 255, 255))
        fy += footer_line_height

    outpath = os.path.join(
        CACHE_DIR,
        f"whitelist_{
            os.getpid()}_{
            int.from_bytes(
                os.urandom(3),
                'big')}.jpg")
    bg = bg.convert("RGB")
    bg.save(outpath, "JPEG", quality=97, optimize=True)
    return outpath


def draw_action_image(client, name, user_id, action="add", result="success"):
    base_width = 730
    font_item = get_font(28)
    font_title = get_font(38)
    font_id = get_font(21)
    font_info = get_font(22)
    act_text = "THÊM VÀO" if action == "add" else "XOÁ"
    title = f"{act_text} WHITELIST"
    title_width = font_title.getlength(title)
    name_width = font_item.getlength(f"Tên: {name}")
    id_width = font_id.getlength(f"ID: {user_id}")
    needed_width = max(title_width+200, name_width+200, id_width+180, 480)
    WIDTH = max(base_width, int(needed_width))
    HEIGHT = 280
    bg = Image.new("RGBA", (WIDTH, HEIGHT), (24, 27, 37, 255))
    draw = ImageDraw.Draw(bg)
    card_x, card_y = 24, 28
    card_w, card_h = WIDTH-2*card_x, HEIGHT-2*card_y
    draw.rounded_rectangle([card_x,
                            card_y,
                            card_x+card_w,
                            card_y+card_h],
                           radius=32,
                           fill=(31,
                                 37,
                                 52,
                                 245),
                           outline=(70,
                                    185,
                                    255),
                           width=4)

    av = fetch_avatar(client, user_id, 96)
    bg.alpha_composite(av, (card_x+30, card_y+30))
    act_color = (100, 255, 120) if result == "success" else (255, 120, 120)
    draw.text((card_x+160, card_y+35), title, font=font_title, fill=act_color)
    name_text = f"Tên: {name}"
    name_lines = wrap_text_with_newlines(name_text, font_item, card_w-200)
    fy = card_y+95
    for line in name_lines:
        draw.text((card_x+160, fy), line, font=font_item, fill=(255, 255, 255))
        fy += font_item.size + 2
    draw.text(
        (card_x+160,
         fy),
        f"ID: {user_id}",
        font=font_id,
        fill=(
            175,
            210,
            255))
    fy += font_id.size + 8
    if result == "success":
        draw.text(
            (card_x+40,
             card_y+card_h-52),
            "Thành công! Chỉ admin nhóm mới thao tác được.",
            font=font_info,
            fill=(
                170,
                255,
                180))
    else:
        draw.text(
            (card_x+40,
             card_y+card_h-52),
            "Không thành công! Có thể user đã/bị thêm trước.",
            font=font_info,
            fill=(
                255,
                170,
                170))
    outpath = os.path.join(
        CACHE_DIR,
        f"whitelistact_{
            os.getpid()}_{
            int.from_bytes(
                os.urandom(3),
                'big')}.jpg")
    bg = bg.convert("RGB")
    bg.save(outpath, "JPEG", quality=97, optimize=True)
    return outpath


class WhitelistHandler:
    def __init__(self, client):
        self.client = client
        self.reaction_icons = {
            'add': ['✅', '➕', '🎉', '✔️'],
            'remove': ['❌', '🗑️', '➖', '🛑'],
            'list': ['📋', '🔍', '📜', '📑'],
            'error': ['⚠️', '🚫', '😓', '❗']
        }

    def _send_multiple_reactions(
            self,
            message_object,
            command_type,
            thread_id,
            thread_type):
        icons = random.sample(
            self.reaction_icons.get(
                command_type, ['✅']), min(
                3, len(
                    self.reaction_icons.get(
                        command_type, ['✅']))))
        for icon in icons:
            try:
                self.client.sendReaction(
                    messageObject=message_object,
                    reactionIcon=icon,
                    thread_id=thread_id,
                    thread_type=thread_type)
            except Exception as e:
                logger.error(f"Lỗi khi gửi reaction '{icon}': {e}")

    def _send_error_image(self, message_object, thread_id, thread_type):
        self._send_multiple_reactions(message_object, 'error', thread_id, thread_type)
        img = self.draw_menu_image()
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

    def handle_whitelist_command(
            self,
            message_text,
            message_object,
            thread_id,
            thread_type,
            author_id):
        if not self.client.is_group_admin(thread_id, author_id) and str(
                author_id) not in self.client.ADMIN:
            self._send_error_image(message_object, thread_id, thread_type)
            return

        parts = message_text.split()
        action = None
        tagged_user_id = None

        # Lấy user ID từ mentions nếu có
        if message_object.mentions:
            tagged_user_id = message_object.mentions[0].uid

        # Tìm action add/remove/list trong message
        for word in parts:
            if word.lower() in ["add", "remove", "list"]:
                action = word.lower()
                break

        # Nếu không có action hợp lệ
        if not action:
            self._send_error_image(message_object, thread_id, thread_type)
            return

        # Nếu action là add/remove nhưng không có user ID
        if action in ["add", "remove"] and not tagged_user_id:
            # Thử lấy user ID từ text (nếu cú pháp whitelist add 123456789)
            for part in parts:
                if part.isdigit():
                    tagged_user_id = part
                    break
            if not tagged_user_id:
                self._send_error_image(message_object, thread_id, thread_type)
                return

        if action == "list":
            self._send_multiple_reactions(message_object, 'list', thread_id, thread_type)
            whitelist = self.client.whitelist.get(thread_id, [])
            img = draw_whitelist_image(self.client, thread_id, whitelist)
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=140000)
            if os.path.exists(img):
                os.remove(img)
            return

        if thread_id not in self.client.whitelist:
            self.client.whitelist[thread_id] = []

        try:
            user_info = self.client.fetchUserInfo(tagged_user_id)
            user_name = user_info.changed_profiles.get(
                str(tagged_user_id), {}).get(
                'zaloName', 'Không xác định')
        except Exception:
            user_name = "Không xác định"

        if action == "add":
            self._send_multiple_reactions(
                message_object, 'add', thread_id, thread_type)
            if str(tagged_user_id) in self.client.whitelist[thread_id]:
                img = draw_action_image(
                    self.client,
                    user_name,
                    tagged_user_id,
                    action="add",
                    result="fail")
                with Image.open(img) as im:
                    width, height = im.size
                self.client.sendLocalImage(
                    img,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=width,
                    height=height,
                    ttl=140000)
                if os.path.exists(img):
                    os.remove(img)
                return
            self.client.whitelist[thread_id].append(str(tagged_user_id))
            self.client.save_whitelist()
            self.client.whitelist = self.client.load_whitelist()
            img = draw_whitelist_image(
                self.client, thread_id, self.client.whitelist[thread_id])
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=140000)
            if os.path.exists(img):
                os.remove(img)
            logger.info(
                f"Added {user_name} ({tagged_user_id}) to whitelist for thread {thread_id}")

        elif action == "remove":
            self._send_multiple_reactions(
                message_object, 'remove', thread_id, thread_type)
            if str(tagged_user_id) not in self.client.whitelist[thread_id]:
                img = draw_action_image(
                    self.client,
                    user_name,
                    tagged_user_id,
                    action="remove",
                    result="fail")
                with Image.open(img) as im:
                    width, height = im.size
                self.client.sendLocalImage(
                    img,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=width,
                    height=height,
                    ttl=140000)
                if os.path.exists(img):
                    os.remove(img)
                return
            self.client.whitelist[thread_id].remove(str(tagged_user_id))
            if not self.client.whitelist[thread_id]:
                del self.client.whitelist[thread_id]
            self.client.save_whitelist()
            self.client.whitelist = self.client.load_whitelist()
            img = draw_whitelist_image(
                self.client,
                thread_id,
                self.client.whitelist.get(
                    thread_id,
                    []))
            with Image.open(img) as im:
                width, height = im.size
            self.client.sendLocalImage(
                img,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=140000)
            if os.path.exists(img):
                os.remove(img)
            logger.info(
                f"Removed {user_name} ({tagged_user_id}) from whitelist for thread {thread_id}")

        if hasattr(self.client, 'save_whitelist_settings'):
            self.client.save_whitelist_settings()
            self.client.whitelist = self.client.load_whitelist()

    def draw_menu_image(self):
        WIDTH, HEIGHT = 820, 470
        bg = Image.new("RGBA", (WIDTH, HEIGHT), (27, 30, 38, 255))
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
                               fill=(36,
                                     40,
                                     57,
                                     238),
                               outline=(70,
                                        185,
                                        255),
                               width=4)
        draw.text(
            (WIDTH //
             2 -
             font_title.getlength("WHITELIST") //
             2,
             card_y +
             20),
            "WHITELIST",
            font=font_title,
            fill=(
                240,
                255,
                255))
        item_lines = [
            f"• {PREFIX}whitelist add @user: Thêm người vào danh sách trắng",
            f"• {PREFIX}whitelist remove @user: Xóa người khỏi danh sách trắng",
            f"• {PREFIX}whitelist list: Xem toàn bộ danh sách trắng"]
        y = card_y+82
        for s in item_lines:
            lines = wrap_text_with_newlines(s, font_item, card_w-60)
            for line in lines:
                draw.text((card_x+38, y), line,
                          font=font_item, fill=(210, 230, 255))
                y += 38
        notice_text = "Chỉ admin Latte mới sử dụng được các lệnh này"
        wrap_notice = wrap_text_with_newlines(
            notice_text, font_info, card_w-40)
        botby_text = "Latte by T K D"
        wrap_botby = wrap_text_with_newlines(botby_text, font_info, card_w-40)
        total_footer_lines = len(wrap_notice) + len(wrap_botby)
        y_footer = card_y+card_h-68 - (total_footer_lines-1)*font_info.size
        draw.line(
            (card_x+30,
             y_footer,
             card_x+card_w-30,
             y_footer),
            fill=(
                70,
                185,
                255),
            width=2)
        fy = y_footer + 10
        for line in wrap_notice:
            draw.text((card_x+40, fy), line,
                      font=font_info, fill=(255, 180, 180))
            fy += font_info.size + 2
        for line in wrap_botby:
            draw.text((card_x+40, fy), line,
                      font=font_info, fill=(220, 255, 255))
            fy += font_info.size + 2
        return self._save_image(bg, "menu")

    def _save_image(self, image, prefix):
        outpath = os.path.join(
            CACHE_DIR, f"{prefix}_{
                os.getpid()}_{
                int.from_bytes(
                    os.urandom(3), 'big')}.jpg")
        image = image.convert("RGB")
        image.save(outpath, "JPEG", quality=97, optimize=True)
        return outpath
