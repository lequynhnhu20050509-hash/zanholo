import os
import importlib
import tempfile
import json
from zlapi.models import Message
from config import PREFIX
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
EMOJI_FONT_PATH = "modules/cache/font/NotoEmoji-Bold.ttf"
BG_IMAGE_PATH = "modules/cache/TQD.jpg"
CACHE_DIR = "modules/cache/menu_temp"
os.makedirs(CACHE_DIR, exist_ok=True)

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Menu lệnh bot.",
    'power': "Thành viên"
}

def get_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()

def get_emoji_font(size):
    try:
        return ImageFont.truetype(EMOJI_FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()

def get_bg_image(size):
    try:
        bg = Image.open(BG_IMAGE_PATH).convert("RGBA")
        bg = bg.resize(size, Image.LANCZOS)
        blur = bg.filter(ImageFilter.GaussianBlur(radius=16))
        overlay = Image.new("RGBA", size, (10, 5, 30, 160))
        bg = Image.alpha_composite(blur, overlay)
        return bg
    except Exception:
        return Image.new("RGBA", size, (15, 10, 35, 255))

def wrap_text(text, font, max_width, indent=0):
    lines, line = [], ""
    for paragraph in text.split('\n'):
        words = paragraph.split()
        for word in words:
            test_line = line + (" " if line else "") + word
            if font.getlength(test_line) + indent > max_width and line:
                lines.append(line)
                line = word
            else:
                line = test_line
        if line:
            lines.append(line)
        line = ""
    return lines

def autosave(img, quality=97):
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        img.convert("RGB").save(
            tf,
            "JPEG",
            quality=quality,
            dpi=(180,180),
            optimize=True,
            progressive=True,
            subsampling=0
        )
        return tf.name

def _smart_resize(img, target_w, target_h):
    w, h = img.size
    scale = min(target_w / w, target_h / h, 1.0)
    if scale < 1:
        return img.resize((int(w*scale), int(h*scale)), resample=Image.LANCZOS)
    return img

def get_all_TQD_with_info():
    TQD_info = {}
    for module_name in os.listdir('modules'):
        if module_name.endswith('.py') and module_name != '__init__.py':
            module_path = f'modules.{module_name[:-3]}'
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, 'TQD'):
                    commands = module.TQD()
                    command_names = list(commands.keys())
                    if command_names:
                        _des = getattr(module, 'des', {})
                        version = _des.get('version', 'N/A')
                        description = _des.get('description', 'Chưa có thông tin')
                        power = _des.get('power', 'Thành viên')
                        module_key = module_name[:-3]
                        TQD_info[module_key] = {
                            'aliases': command_names,
                            'version': version,
                            'description': description,
                            'power': power
                        }
            except Exception as e:
                print(f"Error loading module {module_name}: {e}")
                continue
    return TQD_info

def paginate_menu(TQD_info, page=1, page_size=8):
    total_pages = (len(TQD_info) + page_size - 1) // page_size
    if page < 1 or page > total_pages:
        return None, total_pages
    start = (page - 1) * page_size
    end = start + page_size
    menu_on_page = list(TQD_info.items())[start:end]
    return menu_on_page, total_pages

def fit_text(text, font, max_width, max_lines=2, ellipsis='...'):
    font_size = font.size
    while font_size >= 10:
        f = get_font(font_size)
        lines = wrap_text(text, f, max_width)
        if len(lines) <= max_lines and all(f.getlength(line) <= max_width for line in lines):
            return lines, font_size
        font_size -= 1
    lines = wrap_text(text, get_font(10), max_width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        if len(lines[-1]) > 3:
            lines[-1] = lines[-1][:-3] + ellipsis
    return lines, 10

def fit_desc_height(text, font, max_width, max_height):
    font_size = font.size
    while font_size >= 15:
        f = get_font(font_size)
        lines = wrap_text(text, f, max_width)
        total_height = len(lines) * (f.size + 3)
        if total_height <= max_height:
            return lines, f
        font_size -= 1
    lines = wrap_text(text, get_font(15), max_width)
    return lines, get_font(15)

def draw_menu_menu_img(menu_on_page, page, total_pages, total_cmds, color_palette, icons):
    WIDTH, HEIGHT = 1360, 1440
    grid_x0 = 40
    grid_x1 = WIDTH - 100
    COLS, ROWS = 4, 2
    card_gap_x = 38
    card_gap_y = 48
    card_w = (grid_x1-grid_x0-(COLS-1)*card_gap_x)//COLS + 16
    card_h = (HEIGHT-250-210-(ROWS-1)*card_gap_y)//ROWS + 32

    bg = get_bg_image((WIDTH, HEIGHT))
    draw = ImageDraw.Draw(bg)
    font_title = get_font(78)
    font_info = get_font(36)
    font_card_title = get_font(48)
    font_card_desc = get_font(27)
    font_card_sub = get_font(28)
    emoji_font = get_emoji_font(50)
    icon_circle_radius = 63
    font_footer = get_font(30)

    # Tiêu đề
    title = "MENU LỆNH BOT LATTE"
    draw.text((WIDTH//2 - font_title.getlength(title)//2, 60), title, font=font_title, fill=(0, 255, 255, 255))
    subtitle = f"Trang {page}/{total_pages}  •  {total_cmds} lệnh"
    draw.text((WIDTH//2 - font_info.getlength(subtitle)//2, 155), subtitle, font=font_info, fill=(200, 220, 255, 240))

    for idx, (module_key, info) in enumerate(menu_on_page):
        row, col = divmod(idx, COLS)
        cx = grid_x0 + col*(card_w+card_gap_x)
        cy = 210 + row*(card_h+card_gap_y)

        # --- Ô TRONG SUỐT BO TRÒN ---
        mask = Image.new("L", (card_w, card_h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0,0,card_w,card_h], radius=46, fill=255)

        card_region = bg.crop((cx, cy, cx + card_w, cy + card_h))
        card_blur = card_region.filter(ImageFilter.GaussianBlur(radius=12))
        overlay = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 70))
        card_glass = Image.alpha_composite(card_blur, overlay)
        bg.paste(card_glass, (cx, cy), mask)

        # --- Viền xanh ---
        draw.rounded_rectangle([cx, cy, cx+card_w, cy+card_h],
                               radius=46,
                               outline=(0, 255, 255, 90),
                               width=3)

        # --- Icon tròn ---
        circ_x = cx + card_w//2
        circ_y = cy + 38 + icon_circle_radius - 5
        draw.ellipse([circ_x-icon_circle_radius, circ_y-icon_circle_radius, circ_x+icon_circle_radius, circ_y+icon_circle_radius],
                     fill=color_palette[idx%len(color_palette)]+(225,), outline=(22, 28, 45), width=5)
        draw.text(
            (circ_x - emoji_font.getlength(icons[idx % len(icons)]) // 2, circ_y - emoji_font.size // 2 + 1),
            icons[idx % len(icons)], 
            font=emoji_font, 
            fill=(255, 255, 255, 255),
            stroke_width=3,
            stroke_fill='black'
        )

        # --- Chữ ---
        y = circ_y + icon_circle_radius + 10
        card_title = module_key.upper()
        title_lines, title_font_size = fit_text(card_title, font_card_title, card_w-40, max_lines=2)
        for line in title_lines:
            draw.text(
                (cx + card_w//2 - get_font(title_font_size).getlength(line)//2, y),
                line,
                font=get_font(title_font_size),
                fill=(255, 255, 255, 250)
            )
            y += get_font(title_font_size).size + 2

        alias_text = ", ".join([f"{PREFIX}{a}" for a in info['aliases'][:2]]) + (" ..." if len(info['aliases'])>2 else "")
        alias_lines = wrap_text(alias_text, font_card_sub, card_w-70)
        for line in alias_lines:
            draw.text(
                (cx + card_w//2 - font_card_sub.getlength(line)//2, y),
                line,
                font=font_card_sub,
                fill=(0, 255, 255, 220)
            )
            y += font_card_sub.size + 3

        # --- Version, Power, Description màu trắng ---
        ver = f"v{info['version']}"
        power = f"Quyền: {info['power']}"
        ver_lines, ver_font_size = fit_text(ver, font_card_sub, card_w-50, max_lines=1)
        power_lines, power_font_size = fit_text(power, font_card_sub, card_w-50, max_lines=2)
        for line in ver_lines:
            draw.text(
                (cx + card_w//2 - get_font(ver_font_size).getlength(line)//2, y),
                line,
                font=get_font(ver_font_size),
                fill=(255, 255, 255, 255)  # màu trắng
            )
            y += get_font(ver_font_size).size + 2
        for line in power_lines:
            draw.text(
                (cx + card_w//2 - get_font(power_font_size).getlength(line)//2, y),
                line,
                font=get_font(power_font_size),
                fill=(255, 255, 255, 255)  # màu trắng
            )
            y += get_font(power_font_size).size + 2

        desc_area_height = cy + card_h - y - 23
        desc_lines, desc_font = fit_desc_height(info['description'], font_card_desc, card_w-35, desc_area_height)
        for line in desc_lines:
            draw.text(
                (cx + card_w//2 - desc_font.getlength(line)//2, y),
                line,
                font=desc_font,
                fill=(255, 255, 255, 255)  # màu trắng
            )
            y += desc_font.size + 3

    # Footer
    footer_text = f"👉 {PREFIX}menu <số trang> để chuyển trang | {PREFIX}menu <tên lệnh> để chi tiết"
    draw.text((WIDTH//2 - font_footer.getlength(footer_text)//2, HEIGHT-80), footer_text, font=font_footer, fill=(0, 255, 255, 245))
    credit = f"🤖 Latte by Dương"
    draw.text((WIDTH//2 - font_footer.getlength(credit)//2, HEIGHT-44), credit, font=font_footer, fill=(200, 220, 255, 220))

    img = _smart_resize(bg, 1280, 1280)
    temp_path = autosave(img, quality=97)
    return temp_path

    
def draw_menu_detail_img(requested_menu, module_key, aliases, version, description, power, color_palette):
    base_height = 420
    max_height = 1200
    card_w = 610
    padding_x = 45

    font_title = get_font(43)
    font_alias = get_font(27)
    font_desc = get_font(30)
    font_info = get_font(28)
    font_footer = get_font(24)
    emoji_font = get_emoji_font(50)

    desc_lines = wrap_text(description, font_desc, card_w-70)
    desc_height = len(desc_lines) * (font_desc.size + 3)
    total_height = base_height + desc_height + 80
    HEIGHT = min(max(total_height, 500), max_height)
    WIDTH = card_w + 2*padding_x

    bg = get_bg_image((WIDTH, HEIGHT))
    draw = ImageDraw.Draw(bg)
    card_x, card_y = padding_x, 90
    card_h = HEIGHT-2*card_y

    card_shadow = Image.new("RGBA", bg.size, (0,0,0,0))
    for i in range(12, 0, -2):
        c = (0,0,0, int(90*i/12))
        ImageDraw.Draw(card_shadow).rounded_rectangle([card_x-i, card_y-i, card_x+card_w+i, card_y+card_h+i], radius=38+i, outline=c, width=8)
    card_shadow = card_shadow.filter(ImageFilter.GaussianBlur(3.9))
    bg.alpha_composite(card_shadow)
    draw.rounded_rectangle([card_x, card_y, card_x+card_w, card_y+card_h], radius=44, fill=(0, 0, 0, 0), outline=(0, 255, 255, 120), width=4)

    icon_center_x = card_x + card_w//2
    icon_center_y = card_y + 58
    draw.ellipse([icon_center_x-53, icon_center_y-53, icon_center_x+53, icon_center_y+53],
                 fill=color_palette[0]+(230,), outline=(22, 28, 45), width=5)
    
    draw.text(
        (icon_center_x-emoji_font.getlength("⚙️")//2, icon_center_y-emoji_font.size//2),
        "⚙️", 
        font=emoji_font, 
        fill=(255,255,255,255),
        stroke_width=3,
        stroke_fill='black'
    )
    
    y = icon_center_y + 53 + 10

    cmd_title = f"{PREFIX}{requested_menu.upper()}"
    title_lines, title_font_size = fit_text(cmd_title, font_title, card_w-40, max_lines=2)
    for line in title_lines:
        draw.text((icon_center_x-get_font(title_font_size).getlength(line)//2, y), line, font=get_font(title_font_size), fill=(255, 255, 255, 255))
        y += get_font(title_font_size).size + 3

    alias_text = ", ".join([f"{PREFIX}{a}" for a in aliases])
    alias_lines = wrap_text(alias_text, font_alias, card_w-70)
    for line in alias_lines:
        draw.text((icon_center_x-font_alias.getlength(line)//2, y), line, font=font_alias, fill=(0, 255, 255, 220))
        y += font_alias.size + 4

    ver_lines, ver_font_size = fit_text(f"Phiên bản: {version}", font_info, card_w-50, max_lines=1)
    power_lines, power_font_size = fit_text(f"Quyền: {power}", font_info, card_w-50, max_lines=2)
    for line in ver_lines:
        draw.text((icon_center_x-get_font(ver_font_size).getlength(line)//2, y), line, font=get_font(ver_font_size), fill=(180, 200, 220, 230))
        y += get_font(ver_font_size).size + 2
    for line in power_lines:
        draw.text((icon_center_x-get_font(power_font_size).getlength(line)//2, y), line, font=get_font(power_font_size), fill=(150, 170, 190, 200))
        y += get_font(power_font_size).size + 4

    desc_area_height = card_y + card_h - y - font_footer.size - 40
    desc_lines, desc_font = fit_desc_height(description, font_desc, card_w-70, desc_area_height)
    for line in desc_lines:
        draw.text((icon_center_x-desc_font.getlength(line)//2, y), line, font=desc_font, fill=(210, 220, 240, 230))
        y += desc_font.size + 3

    footer_y = card_y + card_h - font_footer.size - 30
    footer_text = f"📢 Dùng {PREFIX}menu để xem danh sách lệnh!"
    draw.text((icon_center_x-font_footer.getlength(footer_text)//2, footer_y), footer_text, font=font_footer, fill=(0, 255, 255, 200))

    img = _smart_resize(bg, WIDTH, HEIGHT)
    temp_path = autosave(img, quality=97)
    return temp_path

def search_commands(TQD_info, search_term):
    search_term = search_term.lower()
    matched_commands = {}
    for module_key, info in TQD_info.items():
        if search_term in module_key.lower() or any(search_term in alias.lower() for alias in info['aliases']):
            matched_commands[module_key] = info
    return matched_commands

def handle_menu_menu(message, message_object, thread_id, thread_type, author_id, client):
    menu_parts = message.split()
    TQD_info = get_all_TQD_with_info()
    
    color_palette = [
        (0, 255, 255), (255, 0, 255), (57, 255, 20), (255, 105, 180),
        (70, 100, 255), (255, 222, 59)
    ]
    icons = [
        "⚡️", "⚙️", "📈", "🕹️", "💻", "💾", "🔗", "🔑", "🤖", "📊", "🧩", "🖥️"
    ]

    if len(menu_parts) < 2 or menu_parts[1].lower() == "help":
        menu_on_page, total_pages = paginate_menu(TQD_info, page=1, page_size=8)
        temp_path = draw_menu_menu_img(menu_on_page, page=1, total_pages=total_pages, total_cmds=len(TQD_info), color_palette=color_palette, icons=icons)
        with Image.open(temp_path) as im:
            width, height = im.size
        client.sendLocalImage(temp_path, thread_id=thread_id, thread_type=thread_type, width=width, height=height, ttl=120000)
        os.remove(temp_path)
        client.sendReaction(message_object, "ℹ️", thread_id, thread_type)
        return

    if menu_parts[1].isdigit():
        page = int(menu_parts[1])
        menu_on_page, total_pages = paginate_menu(TQD_info, page=page, page_size=8)
        if menu_on_page is None:
            menu_message = f"⚠️ Trang {page} không hợp lệ! Tổng số trang: {total_pages}"
            client.replyMessage(Message(text=menu_message), message_object, thread_id, thread_type, ttl=12000)
            client.sendReaction(message_object, "❌", thread_id, thread_type)
            return
        temp_path = draw_menu_menu_img(menu_on_page, page=page, total_pages=total_pages, total_cmds=len(TQD_info), color_palette=color_palette, icons=icons)
        with Image.open(temp_path) as im:
            width, height = im.size
        client.sendLocalImage(temp_path, thread_id=thread_id, thread_type=thread_type, width=width, height=height, ttl=120000)
        os.remove(temp_path)
        client.sendReaction(message_object, "📜", thread_id, thread_type)
        return
    else:
        search_term = menu_parts[1].lower()
        matched_commands = search_commands(TQD_info, search_term)
        
        if not matched_commands:
            error_message = f"❌ Không tìm thấy lệnh nào khớp với '{search_term}'!"
            client.replyMessage(Message(text=error_message), message_object, thread_id, thread_type, ttl=12000)
            client.sendReaction(message_object, "❌", thread_id, thread_type)
            return
        
        if len(matched_commands) == 1:
            module_key = list(matched_commands.keys())[0]
            info = matched_commands[module_key]
            temp_path = draw_menu_detail_img(
                search_term, module_key, info['aliases'], 
                info['version'], info['description'], info['power'], 
                color_palette
            )
            with Image.open(temp_path) as im:
                width, height = im.size
            client.sendLocalImage(temp_path, thread_id=thread_id, thread_type=thread_type, width=width, height=height, ttl=120000)
            os.remove(temp_path)
            client.sendReaction(message_object, "🔍", thread_id, thread_type)
            return
        
        menu_on_page, total_pages = paginate_menu(matched_commands, page=1, page_size=8)
        temp_path = draw_menu_menu_img(menu_on_page, page=1, total_pages=total_pages, total_cmds=len(matched_commands), color_palette=color_palette, icons=icons)
        with Image.open(temp_path) as im:
            width, height = im.size
        client.sendLocalImage(temp_path, thread_id=thread_id, thread_type=thread_type, width=width, height=height, ttl=120000)
        os.remove(temp_path)
        client.sendReaction(message_object, "🔍", thread_id, thread_type)
        return

def TQD():
    return {
        'menu': handle_menu_menu
    }