import os
import requests
import io
import tempfile
import random
import regex
from zlapi.models import Message, ThreadType
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import PREFIX

FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
EMOJI_FONT_PATH = "modules/cache/font/NotoEmoji-Bold.ttf"
CACHE_DIR = "modules/cache/menu_temp"
BG_DIR = "background/"
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(BG_DIR, exist_ok=True)

BG_FALLBACK_COLOR = (240, 245, 255)
CARD_COLOR = (255, 255, 255, 60)
TEXT_COLOR = (10, 20, 40)
HEADER_COLOR = (0, 0, 0)
CMD_COLOR = (0, 100, 220)
FOOTER_COLOR = (180, 190, 210)


def get_font(size, is_emoji=False):
    try:
        font_file = EMOJI_FONT_PATH if is_emoji else FONT_PATH
        if not os.path.exists(font_file):
            raise IOError
        return ImageFont.truetype(font_file, size)
    except (IOError, TypeError):
        return ImageFont.load_default(size=size)


def wrap_text(text, font, max_width):
    lines = []
    if not text:
        return lines
    for line in text.split('\n'):
        words = line.split(' ')
        current_line = ""
        for word in words:
            if font.getlength(current_line + word + " ") <= max_width:
                current_line += word + " "
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word + " "
        if current_line:
            lines.append(current_line.strip())
    return lines


def get_random_background(width, height):
    try:
        image_files = [
            f for f in os.listdir(BG_DIR) if f.lower().endswith(
                ('.png', '.jpg', '.jpeg'))]
        if not image_files:
            raise FileNotFoundError("No images in background directory")

        random_bg_path = os.path.join(BG_DIR, random.choice(image_files))
        bg = Image.open(random_bg_path).convert("RGBA")

        img_w, img_h = bg.size
        ratio = max(width / img_w, height / img_h)
        bg = bg.resize((int(img_w * ratio), int(img_h * ratio)), Image.LANCZOS)
        left, top = (bg.width - width) / 2, (bg.height - height) / 2
        return bg.crop((left, top, left + width, top + height))
    except Exception as e:
        print(f"Error getting background: {e}. Using fallback.")
        return Image.new("RGBA", (width, height), BG_FALLBACK_COLOR)


def draw_menu_image(commands_list, page=1):
    WIDTH, HEIGHT = 1080, 1440
    COLS, PADDING = 2, 50
    HEADER_HEIGHT, FOOTER_HEIGHT, CARD_PADDING = 220, 100, 30
    COL_SPACING, CARD_SPACING, ICON_SIZE = 40, 30, 42
    CARD_WIDTH = (WIDTH - PADDING * 2 - COL_SPACING) // COLS

    font_header, font_cmd, font_desc, font_footer, emoji_font = get_font(
        70), get_font(30), get_font(24), get_font(22), get_font(42, is_emoji=True)

    all_card_heights = [CARD_PADDING *
                        2 +
                        50 +
                        15 +
                        (len(wrap_text(desc, font_desc, CARD_WIDTH -
                                       CARD_PADDING *
                                       2)) *
                         28) for _, _, desc in commands_list]
    available_height = HEIGHT - HEADER_HEIGHT - FOOTER_HEIGHT
    items_per_page = 0
    temp_col_heights = [0] * COLS

    for i, card_h in enumerate(all_card_heights):
        min_col_idx = temp_col_heights.index(min(temp_col_heights))
        if temp_col_heights[min_col_idx] + card_h <= available_height:
            temp_col_heights[min_col_idx] += card_h + CARD_SPACING
            items_per_page += 1
        else:
            break

    if items_per_page == 0 and commands_list:
        items_per_page = 1

    total_pages = (len(commands_list) + items_per_page -
                   1) // items_per_page if items_per_page > 0 else 1
    start_index = (page - 1) * items_per_page
    paginated_list_indices = range(start_index, min(
        len(commands_list), start_index + items_per_page))

    if not paginated_list_indices:
        return None

    bg_image = get_random_background(WIDTH, HEIGHT)
    image = bg_image.filter(ImageFilter.GaussianBlur(30))
    draw = ImageDraw.Draw(image, "RGBA")

    header_text = "Menu Lệnh"
    bbox = draw.textbbox((0, 0), header_text, font=font_header)
    draw.text(((WIDTH - (bbox[2]-bbox[0])) / 2,
               80),
              header_text,
              font=font_header,
              fill=(255,
                    255,
                    255),
              stroke_width=2,
              stroke_fill=(0,
                           0,
                           0,
                           100))

    col_heights_render, col_cards_render = [
        0] * COLS, [[] for _ in range(COLS)]
    for i in paginated_list_indices:
        card_h = all_card_heights[i]
        min_col_idx = col_heights_render.index(min(col_heights_render))
        col_cards_render[min_col_idx].append(i)
        col_heights_render[min_col_idx] += card_h + CARD_SPACING

    for col_idx, card_indices in enumerate(col_cards_render):
        current_y = HEADER_HEIGHT
        for card_idx in card_indices:
            icon, cmd, desc = commands_list[card_idx]
            card_h, card_x = all_card_heights[card_idx], PADDING + \
                col_idx * (CARD_WIDTH + COL_SPACING)

            glass_area = bg_image.crop(
                (card_x,
                 current_y,
                 card_x +
                 CARD_WIDTH,
                 current_y +
                 card_h)).filter(
                ImageFilter.GaussianBlur(20))
            image.paste(glass_area, (card_x, current_y))
            draw.rounded_rectangle(
                (card_x,
                 current_y,
                 card_x+CARD_WIDTH,
                 current_y+card_h),
                radius=20,
                fill=CARD_COLOR,
                outline=(
                    255,
                    255,
                    255,
                    80),
                width=2)

            draw.text(
                (card_x +
                 CARD_PADDING,
                 current_y +
                 CARD_PADDING -
                 5),
                icon,
                font=emoji_font,
                fill=TEXT_COLOR)
            draw.text(
                (card_x +
                 CARD_PADDING +
                 ICON_SIZE +
                 15,
                 current_y +
                 CARD_PADDING +
                 2),
                cmd,
                font=font_cmd,
                fill=CMD_COLOR)
            desc_y = current_y + CARD_PADDING + 50 + 15
            for line in wrap_text(
                    desc,
                    font_desc,
                    CARD_WIDTH -
                    CARD_PADDING *
                    2):
                draw.text((card_x + CARD_PADDING, desc_y),
                          line, font=font_desc, fill=TEXT_COLOR)
                desc_y += 28
            current_y += card_h + CARD_SPACING

    footer_text = f"Trang {page}/{total_pages} • Latte by T K D"
    bbox = draw.textbbox((0, 0), footer_text, font=font_footer)
    draw.text(((WIDTH - (bbox[2]-bbox[0])) / 2,
               HEIGHT - FOOTER_HEIGHT + 30),
              footer_text,
              font=font_footer,
              fill=FOOTER_COLOR)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        final_img = image.convert("RGB")
        final_img.save(
            tf.name,
            "JPEG",
            quality=95,
            optimize=True,
            subsampling=0,
            dpi=(
                150,
                150))
        return tf.name, final_img.width, final_img.height


class CmdHandler:
    def __init__(self, client):
        self.client = client

    def handle_menu_command(
            self,
            message_text,
            message_object,
            thread_id,
            thread_type,
            author_id):
        if not self.client.is_admin(author_id, thread_id):
            self.client.replyMessage(
                Message(
                    text="Bạn không có quyền sử dụng lệnh này. Chỉ có admin Latte mới được sử dụng"),
                message_object,
                thread_id,
                thread_type)
            return

        parts = message_text.split()
        page = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1

        commands_list = [
            ("🤖", f"{PREFIX}bot", "Quản lý trạng thái bot (on/off/list/all)."),            
            ("🛡️", f"{PREFIX}antisp", "Chống spam tin nhắn nhanh trong nhóm."),
            ("🎭", f"{PREFIX}antiricon", "Chống spam thả icon (reaction)."),
            ("📢", f"{PREFIX}antiall", "Chống tag @all hoặc spam tag nhiều người."),
            ("🔗", f"{PREFIX}antilink", "Chống gửi các loại link lạ."),
            ("📸", f"{PREFIX}antiphoto", "Chống gửi ảnh vào nhóm."),
            ("📹", f"{PREFIX}antivideo", "Chống gửi video vào nhóm."),
            ("📁", f"{PREFIX}antifile", "Chống gửi file vào nhóm."),
            ("🎨", f"{PREFIX}antistk", "Chống gửi sticker vào nhóm."),
            ("🎟️", f"{PREFIX}anticard", "Chông gửi danh thiếp vào nhóm."),
            ("🤬", f"{PREFIX}cam", "Kích hoạt bộ lọc từ ngữ thô tục."),
            ("✉️", f"{PREFIX}antiundo", "Chống thu hồi tin nhắn."),
            ("📝", f"{PREFIX}whitelist", "Quản lý danh sách miễn trừ các tính năng anti."),
            ("✅", f"{PREFIX}autoapprv", "Tự động duyệt thành viên đang chờ."),
            ("🔒", f"{PREFIX}lbot", "Khóa bot, chỉ admin mới có thể ra lệnh."),
            ("🔓", f"{PREFIX}unlbot", "Mở khóa bot cho tất cả mọi người."),
            ("⛔", f"{PREFIX}bcmd", "Quản lý danh sách các lệnh bị cấm."),
            ("⛔", f"{PREFIX}svc, luuvc,\ndelvc, listvoice", "\nQuản lý voice và gửi voice."),
        ]

        output_path = None
        try:
            self.client.sendReaction(
                message_object,
                "⏳",
                thread_id,
                thread_type,
                reactionType=75)
            image_result = draw_menu_image(commands_list, page)
            if image_result:
                output_path, width, height = image_result
                self.client.sendLocalImage(
                    output_path,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=width,
                    height=height,
                    ttl=120000)
                self.client.sendReaction(
                    message_object,
                    "✅",
                    thread_id,
                    thread_type,
                    reactionType=75)
            else:
                self.client.replyMessage(
                    Message(
                        text=f"❌ Không có dữ liệu ở trang {page}."),
                    message_object,
                    thread_id,
                    thread_type,
                    ttl=60000)
        except Exception as e:
            print(f"Error generating or sending menu image: {e}")
            self.client.replyMessage(
                Message(
                    text="Đã có lỗi xảy ra khi tạo menu."),
                message_object,
                thread_id,
                thread_type)
            self.client.sendReaction(
                message_object,
                "⚠️",
                thread_id,
                thread_type,
                reactionType=75)
        finally:
            if output_path and os.path.exists(output_path):
                os.remove(output_path)


def TQD():
    return {'cmd': handle_menu_command}
