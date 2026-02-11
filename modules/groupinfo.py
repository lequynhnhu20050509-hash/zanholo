import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import requests
import base64
import emoji
from datetime import datetime
from zlapi.models import *

des = {'version': "2.0.1", 'credits': "Latte", 'description': "thông tin nhóm - phiên bản cải tiến", 'power': "Thành viên"}

def draw_text_line(draw, text, x, y, font, emoji_font, text_color, shadow=False):
    if shadow:
        draw.text((x + 2, y + 2), text, fill=(0, 0, 0, 100), font=font)
    
    for char in text:
        f = emoji_font if emoji.emoji_count(char) else font
        draw.text((x, y), char, fill=text_color, font=f)
        x += f.getlength(char)
    return x

def truncate_text_to_fit(text, font, emoji_font, max_width):
    if not text:
        return text
    
    current_width = sum(emoji_font.getlength(c) if emoji.emoji_count(c) else font.getlength(c) for c in text)
    
    if current_width <= max_width:
        return text
    
    ellipsis = "..."
    ellipsis_width = font.getlength(ellipsis)
    available_width = max_width - ellipsis_width
    
    truncated = ""
    for char in text:
        char_width = emoji_font.getlength(char) if emoji.emoji_count(char) else font.getlength(char)
        if sum(emoji_font.getlength(c) if emoji.emoji_count(c) else font.getlength(c) for c in truncated + char) <= available_width:
            truncated += char
        else:
            break
    
    return truncated + ellipsis if truncated else text

def split_text_into_lines(text, font, emoji_font, max_width):
    lines = []
    for paragraph in text.splitlines():
        words = paragraph.split()
        line = ""
        for word in words:
            temp_line = line + word + " "
            width = sum(emoji_font.getlength(c) if emoji.emoji_count(c) else font.getlength(c) for c in temp_line)
            if width <= max_width:
                line = temp_line
            else:
                if line:
                    lines.append(line.strip())
                line = word + " "
        if line:
            lines.append(line.strip())
    return lines

def draw_modern_card(draw, x, y, width, height, corner_radius=20):
    for i in range(height):
        alpha = int(200 - (i * 50 / height))
        color = (30, 30, 30, alpha)
        draw.rectangle([x, y + i, x + width, y + i + 1], fill=color)
        
    draw.rectangle([x, y, x + width, y + height], outline=(100, 100, 100, 150), width=2)

def draw_info_section(draw, title, content, x, y, title_font, content_font, emoji_font, max_width):

    draw_text_line(draw, title, x, y, title_font, emoji_font, (255, 215, 0), shadow=True)
    
    content_y = y + title_font.size + 25
    lines = split_text_into_lines(content, content_font, emoji_font, max_width)
    
    for line in lines:
        draw_text_line(draw, line, x + 20, content_y, content_font, emoji_font, (255, 255, 255))
        content_y += int(content_font.size * 1.3)
    
    return content_y + 25

def get_font_size(size=50, bold=False):
    font_path = "modules/cache/font/BeVietnamPro-Bold.ttf" if bold else "modules/cache/font/BeVietnamPro-SemiBold.ttf"
    return ImageFont.truetype(font_path, size)

def make_circle_mask(size, border_width=0):
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((border_width, border_width, size[0] - border_width, size[1] - border_width), fill=255)
    return mask

def draw_premium_avatar(image, avatar_image, position, size, border_color=(255, 215, 0), border_thickness=8):
    scale = 4
    scaled_size = (size[0] * scale, size[1] * scale)
    scaled_border_thickness = border_thickness * scale
    inner_scaled_size = (scaled_size[0] - 2 * scaled_border_thickness, scaled_size[1] - 2 * scaled_border_thickness)
    
    avatar_scaled = avatar_image.resize(inner_scaled_size, resample=Image.LANCZOS)
    
    avatar_scaled = avatar_scaled.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
    
    mask_scaled = make_circle_mask(inner_scaled_size)
    
    border_img = Image.new("RGBA", scaled_size, (0, 0, 0, 0))
    draw_obj = ImageDraw.Draw(border_img)
    
    for i in range(scaled_border_thickness):
        alpha = int(255 * (1 - i / scaled_border_thickness))
        color = border_color + (alpha,)
        draw_obj.ellipse((i, i, scaled_size[0] - i - 1, scaled_size[1] - i - 1), 
                        outline=color, width=2)
    
    border_img.paste(avatar_scaled, (scaled_border_thickness, scaled_border_thickness), mask=mask_scaled)
    border_img = border_img.resize(size, resample=Image.LANCZOS)
    
    shadow = Image.new("RGBA", (size[0] + 20, size[1] + 20), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.ellipse((10, 10, size[0] + 10, size[1] + 10), fill=(0, 0, 0, 100))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=8))
    
    image.paste(shadow, (position[0] - 10, position[1] - 10), mask=shadow)
    image.paste(border_img, position, mask=border_img)

def create_modern_background(width, height, cover_image=None):
    if cover_image:
        bg = cover_image.resize((width, height), Image.LANCZOS)
        
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        for y in range(height):
            alpha = int(180 * (y / height))
            overlay_draw.rectangle([0, y, width, y + 1], fill=(0, 0, 0, alpha))
        
        bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    else:
        bg = Image.new("RGB", (width, height), (20, 20, 30))
        draw = ImageDraw.Draw(bg)
        
        for y in range(height):
            r = int(20 + (40 * y / height))
            g = int(20 + (30 * y / height))
            b = int(30 + (50 * y / height))
            draw.rectangle([0, y, width, y + 1], fill=(r, g, b))
    
    return bg

def process_modern_group_info(avatar_url, cover_path, group_name, group_data):
    canvas_width, canvas_height = 1200, 800
    
    cover_image = None
    try:
        cover_image = Image.open(cover_path).convert("RGB")
    except:
        pass
    
    image = create_modern_background(canvas_width, canvas_height, cover_image)
    draw = ImageDraw.Draw(image)
    
    avatar_image = fetch_image(avatar_url)
    
    avatar_size = 180
    avatar_x = 60
    avatar_y = 80
    
    if avatar_image:
        draw_premium_avatar(image, avatar_image, (avatar_x, avatar_y), (avatar_size, avatar_size))
    
    title_font = get_font_size(45, bold=True)
    emoji_font = ImageFont.truetype("modules/cache/font/NotoEmoji-Bold.ttf", 45)
    
    title_x = avatar_x + avatar_size + 40
    title_y = avatar_y + 50
    
    title_width = min(canvas_width - title_x - 40, 600)
    title_card_height = 80
    draw_modern_card(draw, title_x - 20, title_y - 15, title_width, title_card_height, 15)
    
    max_title_width = title_width - 60
    icon_text = "🏷️"
    icon_width = emoji_font.getlength(icon_text)
    available_width = max_title_width - icon_width
    
    truncated_name = truncate_text_to_fit(group_name, title_font, emoji_font, available_width)
    full_title = f"{icon_text}{truncated_name}"
    
    draw_text_line(draw, full_title, title_x, title_y, title_font, emoji_font, (255, 255, 255), shadow=True)
    
    info_y = avatar_y + avatar_size + 60
    info_x = 60
    
    info_card_width = canvas_width - 120
    info_card_height = canvas_height - info_y - 60
    draw_modern_card(draw, info_x - 20, info_y - 20, info_card_width, info_card_height, 20)
    
    section_font = get_font_size(28, bold=True)
    content_font = get_font_size(24)
    current_y = info_y + 10
    max_width = info_card_width - 80
    
    sections = [
        ("👥 THÔNG TIN CHUNG", f"Tổng số thành viên: {group_data['total_members']}\nLoại nhóm: {group_data['group_type']}"),
        ("👑 QUẢN TRỊ", f"Trưởng nhóm: {group_data['creator']}\nPhó nhóm: {', '.join(group_data['admins']) or 'Không có'}\n"),
        ("📅 THỜI GIAN", f"Ngày tạo: {group_data['created_time']}")
    ]
    
    for section_title, section_content in sections:
        current_y = draw_info_section(draw, section_title, section_content, 
                                    info_x, current_y, section_font, content_font, 
                                    emoji_font, max_width)
        current_y += 15
    watermark_font = get_font_size(16)
    watermark_text = "✨ Powered by ZaloBot v2.1"
    draw.text((canvas_width - 250, canvas_height - 30), watermark_text, 
             fill=(150, 150, 150), font=watermark_font)
    
    return image

def fetch_image(url):
    if not url:
        return None
    try:
        if url.startswith('data:image'):
            h, e = url.split(',', 1)
            try:
                i = base64.b64decode(e)
            except:
                return None
            return Image.open(BytesIO(i)).convert("RGB")
        r = requests.get(url, stream=True, timeout=10)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except:
        return None

def truncate_text(text, max_length=100):
    if isinstance(text, str) and len(text) > max_length:
        return text[:max_length] + "..."
    return text

def prepare_group_data(group, get_name):
    creator_name = truncate_text(get_name(group.creatorId))
    group_type = "Cộng Đồng" if group.type == 2 else "Nhóm Chat"
    created_time = datetime.fromtimestamp(group.createdTime / 1000).strftime('%d/%m/%Y lúc %H:%M')
    
    admin_names = [truncate_text(get_name(aid)) for aid in getattr(group, "adminIds", [])]
    
    return {
        'creator': creator_name,
        'group_type': group_type,
        'total_members': group.totalMember,
        'created_time': created_time,
        'admins': admin_names
    }

def handle_groupinfo_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        def get_name(id):
            try:
                return client.fetchUserInfo(id).changed_profiles[id].zaloName
            except:
                return "Người dùng ẩn danh"

        group = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        group_data = prepare_group_data(group, get_name)
        
        avatar_url = group.fullAvt
        cover_path = "modules/cache/TQuan.jpg"
        group_name = group.name
        
        image = process_modern_group_info(avatar_url, cover_path, group_name, group_data)
        
        output_path = "modules/cache/ZALOBOT_v2.1.jpg"
        image.save(output_path, quality=95, optimize=True)
        
        try:
            if os.path.exists(output_path):
                client.sendLocalImage(output_path, thread_id=thread_id, thread_type=thread_type, ttl=60000*2,
                                    width=image.width, height=image.height)
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)
                
    except Exception as e:
        print(f"❌ Lỗi khi xử lý lệnh groupinfo: {e}")
        client.sendMessage("❌ Có lỗi xảy ra khi tạo thông tin nhóm. Vui lòng thử lại sau!", 
                          thread_id=thread_id, thread_type=thread_type)

def TQD():
    return {
        'grinfo': handle_groupinfo_command
    }