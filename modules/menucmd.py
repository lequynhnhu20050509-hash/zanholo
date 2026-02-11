from zlapi.models import Message
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import emoji
import os, time, random
from config import PREFIX

des = {
    "version": "2.0.1",
    'credits': "Latte",
    "description": "Hiển thị danh sách các lệnh quản lý bot.",
    "power": True
}

FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
EMOJI_FONT_PATH = "modules/cache/font/NotoEmoji-Bold.ttf"
CACHE_DIR = "modules/cache/listcmd_temp"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_font(size):
    return ImageFont.truetype(FONT_PATH, size)

def get_emoji_font(size):
    return ImageFont.truetype(EMOJI_FONT_PATH, size)

def text_wrap(text, font, emoji_font, max_width):
    lines = []
    line = ""
    for word in text.split():
        test_line = f"{line} {word}".strip()
        w = sum(emoji_font.getlength(ch) if emoji.emoji_count(ch) else font.getlength(ch) for ch in test_line)
        if w > max_width and line:
            lines.append(line)
            line = word
        else:
            line = test_line
    if line:
        lines.append(line)
    return lines

def draw_center_text(draw, text, y, font, emoji_font, img_w, color, shadow=False, x_offset=0):
    lines = text_wrap(text, font, emoji_font, img_w - 60)
    line_height = font.getbbox("Ay")[3] - font.getbbox("Ay")[1]
    for i, line in enumerate(lines):
        width = sum(emoji_font.getlength(c) if emoji.emoji_count(c) else font.getlength(c) for c in line)
        x = (img_w - width) // 2 + x_offset
        if shadow:
            draw.text((x+2, y+2), line, font=font, fill=(0,0,0,180))
        draw.text((x, y), line, font=font, fill=color)
        y += line_height + 6

def draw_card_box(draw, x, y, w, h, radius, fill, outline, outline_width, shadow=True):
    if shadow:
        shadow_offset = 7
        shadow_fill = (10, 12, 22, 120)
        draw.rounded_rectangle(
            [x + shadow_offset, y + shadow_offset, x + w + shadow_offset, y + h + shadow_offset],
            radius=radius+2,
            fill=shadow_fill
        )
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill, outline=outline, width=outline_width)

def calc_card_height(desc, usage, font, emoji_font, tw):
    title_h = 29 + 15
    desc_lines = text_wrap(desc, font, emoji_font, tw)
    usage_lines = text_wrap(usage, font, emoji_font, tw)
    line_h = font.getbbox("Ay")[3] - font.getbbox("Ay")[1] + 2
    content_h = len(desc_lines)*line_h + len(usage_lines)*line_h
    y_desc = 56
    y_bot = 20
    return y_desc + content_h + y_bot

def draw_cmd_card(draw, x, y, w, h, title, desc, usage, font, emoji_font, prefix_color):
    glass_fill = (35, 38, 55, 215)
    draw_card_box(draw, x, y, w, h, 26, glass_fill, prefix_color, 4, shadow=True)

    icon, name = title.split(' ', 1)
    draw.text((x + 22, y + 16), icon, font=emoji_font, fill=(200, 220, 255))
    tx = x + 70
    tw = w - 80
    draw.text((tx, y + 15), name, font=get_font(29), fill=(220, 240, 255))
    desc_lines = text_wrap(desc, font, emoji_font, tw)
    y_desc = y + 56
    line_h = font.getbbox("Ay")[3] - font.getbbox("Ay")[1] + 2
    for line in desc_lines:
        draw.text((tx, y_desc), line, font=font, fill=(170, 200, 230))
        y_desc += line_h
    usage_lines = text_wrap(usage, font, emoji_font, tw)
    for line in usage_lines:
        draw.text((tx, y_desc), line, font=font, fill=(110, 180, 200))
        y_desc += line_h
    draw.line((x + 20, y + h - 14, x + w - 20, y + h - 14), fill=(90, 180, 255), width=2)

def create_listcmd_image(prefix):
    image_width, image_height = 1000, 900
    margin_x = 54
    bg = Image.new("RGBA", (image_width, image_height), (28, 32, 42, 255))
    grad = Image.new("RGBA", (image_width, image_height), (0, 0, 0, 0))
    for y in range(image_height):
        color = (
            int(28 + y * (10 / image_height)),
            int(32 + y * (18 / image_height)),
            int(42 + y * (30 / image_height)),
            255
        )
        ImageDraw.Draw(grad).line([(0, y), (image_width, y)], fill=color)
    bg = Image.alpha_composite(bg, grad)
    blur = bg.filter(ImageFilter.GaussianBlur(radius=9))
    bg = Image.alpha_composite(bg, blur)
    draw = ImageDraw.Draw(bg)

    header_box = [margin_x, 24, image_width - margin_x, 100]
    header_fill = (38, 45, 65, 180)
    draw.rounded_rectangle(header_box, radius=32, fill=header_fill, outline=(90, 180, 255), width=3)

    header_text = "🛡️ BOT ADMIN COMMANDS 🛡️"
    draw_center_text(draw, header_text, 42, get_font(38), get_emoji_font(38), image_width, (220, 230, 255), True, x_offset=20)

    commands = [
        {
            "name": "lenh",
            "icon": "📝",
            "description": "Quản lý lệnh re search (thêm, xóa, liệt kê). Chỉ admin sử dụng.",
            "usage": f"{PREFIX}lenh <add|rmv|list> <command>"
        },
        {
            "name": "alias",
            "icon": "💡",
            "description": "Quản lý alias cho lệnh (thêm, xóa, liệt kê). Chỉ admin sử dụng.",
            "usage": f"{PREFIX}alias <add|rm|list> <command> <alias>"
        },
        {
            "name": "credit",
            "icon": "🔮",
            "description": "Thay đổi tên admin bot v.v thành tên mới.",
            "usage": f"{PREFIX}credit <chuỗi cũ> - <chuỗi mới>"
        },
        {
            "name": "stw",
            "icon": "⚙️",
            "description": "Cho phép lệnh cụ thể không cần bắt buộc prefix ở đầu.",
            "usage": f"{PREFIX}stw add/del/help <command>"
        },
        {
            "name": "cooldown",
            "icon": "⏱️",
            "description": "Quản lý thời gian chờ của lệnh (đặt, xóa, liệt kê). Chỉ admin sử dụng.",
            "usage": f"{PREFIX}cooldown <set|remove|list> <command> <time>"
        }
    ]

    y = 120
    margin_card = 22
    prefix_color = (90, 180, 255)
    font = get_font(22)
    emoji_font = get_emoji_font(28)
    card_w = image_width - 2 * margin_x - 6
    for i, cmd in enumerate(commands):
        card_h = calc_card_height(f"Mô tả: {cmd['description']}", f"Cách dùng:  {cmd['usage']}", font, emoji_font, card_w - 80)
        draw_cmd_card(
            draw,
            margin_x + 3,
            y,
            card_w,
            card_h,
            f"{cmd['icon']} {cmd['name'].upper()}",
            f"Mô tả: {cmd['description']}",
            f"Cách dùng:  {cmd['usage']}",
            font,
            emoji_font,
            prefix_color
        )
        y += card_h + margin_card

    footer_text = f"⚠️ Chỉ dành cho admin/quản trị viên | Gõ {PREFIX}menu để xem thêm"
    draw_center_text(draw, footer_text, image_height - 48, get_font(25), get_emoji_font(25), image_width, (180, 200, 220), True)

    outname = os.path.join(CACHE_DIR, f"listcmd_{time.time()}_{random.randint(1000,9999)}.jpg")
    bg = bg.convert("RGB")
    bg.save(outname, "JPEG", quality=100, optimize=True)
    return outname

def TQD():
    def listcmd(message_text, message_object, thread_id, thread_type, author_id, client):
        prefix = client.command_handler.current_prefix
        img_path = create_listcmd_image(prefix)
        with Image.open(img_path) as img:
            width, height = img.size
        client.sendLocalImage(
            img_path,
            thread_id=thread_id,
            thread_type=thread_type,
            width=width,
            height=height,
            ttl=120000
        )
        if os.path.exists(img_path):
            os.remove(img_path)
    return {"listcmd": listcmd}

