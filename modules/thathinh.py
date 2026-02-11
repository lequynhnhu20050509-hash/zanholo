import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import requests
import base64
import emoji
import concurrent.futures
import logging
from zlapi.models import Message
from datetime import datetime
import pytz

# --------------------- Module metadata ---------------------
des = {
    'version': "2.0.2",
    'credits': "Latte",
    'description': "Thả thính bằng avatar",
    'power': "Thành viên"
}

# --------------------- Config ---------------------
from config import GEMINI_API_KEY  # Lấy API key từ file config


FONT_PATH = "modules/cache/font/NotoSans-Bold.ttf"
EMOJI_FONT_PATH = "modules/cache/font/NotoEmoji-Bold.ttf"

# --------------------- Font helpers ---------------------
def get_font(size):
    return ImageFont.truetype(FONT_PATH, size)

def get_emoji_font(size):
    return ImageFont.truetype(EMOJI_FONT_PATH, size)

def calculate_text_width(text, font, emoji_font):
    return sum(emoji_font.getlength(c) if emoji.emoji_count(c) else font.getlength(c) for c in text)

def split_text_into_lines(text, font, emoji_font, max_width):
    lines, current_line = [], []
    for word in text.split():
        temp_line = " ".join(current_line + [word])
        if calculate_text_width(temp_line, font, emoji_font) <= max_width:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
    return lines + [" ".join(current_line)]

def draw_text(draw, text, position, font, emoji_font, image_width, text_color=(255, 255, 255), author_font=None):
    x, y = position
    line_height = int((font.getbbox("Ay")[3] - font.getbbox("Ay")[1]) * 1.4)
    max_width = image_width * 0.9
    all_lines = []
    for line in text.splitlines():
        all_lines.extend(split_text_into_lines(line, font, emoji_font, max_width))
    start_y = y - len(all_lines) * line_height // 2
    for i, line in enumerate(all_lines):
        current_x = x - calculate_text_width(line, author_font if i == 0 and author_font else font,
                                             emoji_font) // 2
        for char in line:
            f = emoji_font if emoji.emoji_count(char) else (author_font if i == 0 and author_font else font)
            draw.text((current_x, start_y), char, fill=text_color, font=f)
            current_x += f.getlength(char)
        start_y += line_height

# --------------------- Avatar helpers ---------------------
def make_circle_mask(size):
    mask = Image.new('L', size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size[0], size[1]), fill=255)
    return mask

def draw_circular_avatar(image, avatar_image, position, size):
    if avatar_image:
        image.paste(avatar_image.resize(size), position, mask=make_circle_mask(size))

def calculate_text_height(content, font, emoji_font, image_width):
    dummy_image = Image.new("RGB", (image_width, 1))
    line_height = int(
        (ImageDraw.Draw(dummy_image).textbbox((0, 0), "A", font=font)[3] - ImageDraw.Draw(dummy_image).textbbox((0, 0),
                                                                                                             "A",
                                                                                                             font=font)[
            1]) * 1.4)
    max_width = image_width * 0.9
    all_lines = []
    for line in content.splitlines():
        all_lines.extend(split_text_into_lines(line, font, emoji_font, max_width))
    return len(all_lines) * line_height

def fetch_image(url):
    if not url:
        return None
    try:
        if url.startswith('data:image'):
            return Image.open(BytesIO(base64.b64decode(url.split(',', 1)[1]))).convert("RGB")
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGB")
    except:
        return None

# --------------------- Gemini thính ---------------------
def get_gemini_response_thathinh(name):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    prompt = f"Hãy tạo 1 bài thơ có 4 câu thơ liên tiếp không đánh số thứ tự cho câu thơ thả thính ngọt ngào, lãng mạn và văn vở với tên {name}. Không cần giải thích, chỉ cần câu thả thính. Gieo vần đỉnh của chóp thì thính mới hay, sáng tạo lên, có thể là thơ: lục bát hoặc các loại thơ khác, nói chung là như thơ của Nhà thơ Mạnh Quỳnh Việt Nam!"
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        if 'candidates' in result and result['candidates']:
            for candidate in result['candidates']:
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        if 'text' in part:
                            return part['text']
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Request Exception: {e}, Response: {response.text if 'response' in locals() else 'N/A'}")
        return None
    except Exception as e:
        logging.error(f"General Exception: {e}")
        return None

# --------------------- Image generator ---------------------
def process_thathinh_image(avatar_url, name, thinh_text):
    base_font_size = 88
    normal_font = get_font(base_font_size)
    emoji_font = get_emoji_font(base_font_size)
    author_font = get_font(base_font_size + 30)
    combined_text = f"{name}\n\n{thinh_text}"
    text_height = calculate_text_height(combined_text, normal_font, emoji_font, 1600)
    image_width = 2000
    image_height = max(2000, text_height + 200)
    image = Image.new("RGB", (image_width, image_height), color=(50, 50, 50))
    avatar_image = fetch_image(avatar_url)
    if avatar_image:
        image.paste(avatar_image.resize((image_width, image_height)), (0, 0))
        image = ImageEnhance.Brightness(image).enhance(0.3)
    draw = ImageDraw.Draw(image)
    draw_text(draw, combined_text, (image_width // 2, image_height // 2), normal_font, emoji_font, image_width,
              text_color=(255, 255, 255), author_font=author_font)
    return image

# --------------------- Name helpers ---------------------
def get_user_name_by_id(bot, user_id):
    try:
        info = bot.fetchUserInfo(user_id)
        if hasattr(info, "changed_profiles") and user_id in info.changed_profiles:
            profile = info.changed_profiles[user_id]
            return getattr(profile, "zaloName", None) or getattr(profile, "displayName", "Unknown User")
        return "Unknown User"
    except Exception:
        return "Unknown User"

def get_name_from_message(bot, message_object, message_text):
    """
    Lấy tên từ mention nếu có, nếu không thì lấy từ text.
    """
    # Nếu có mention, lấy tên từ mention đầu tiên
    if message_object.mentions and len(message_object.mentions) > 0:
        mention = message_object.mentions[0]  # lấy mention đầu tiên
        uid = mention['uid'] if isinstance(mention, dict) else mention.uid
        return get_user_name_by_id(bot, uid)
    
    # Nếu không có mention, lấy tên từ text
    name = " ".join(message_text.strip().split()[1:]).strip()
    return name

# --------------------- Command handler ---------------------
def handle_thathinh_command(message, message_object, thread_id, thread_type, author_id, client):
    name = get_name_from_message(client, message_object, message)
    
    if not name:
        client.replyMessage(Message(text="• Nhập tên người cần tạo thính."), message_object, thread_id, thread_type, ttl=12000)
        return
    name_parts = name.split()
    if len(name_parts) > 6:
        client.replyMessage(Message(text="• Tên chỉ được giới hạn 6 chữ."), message_object, thread_id, thread_type, ttl=12000)
        return

    thinh_text = get_gemini_response_thathinh(name)
    if not thinh_text:
        client.replyMessage(Message(text="• Không thể tạo câu thính lúc này."), message_object, thread_id, thread_type, ttl=12000)
        return

    try:
        user_info = client.fetchUserInfo(author_id) or {}
        user_data = user_info.get('changed_profiles', {}).get(str(author_id), {})
        avatar_url = user_data.get("avatar", None)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            image = executor.submit(process_thathinh_image, avatar_url, name, thinh_text).result()
        output_path = "modules/cache/thathinh_temp.png"
        image.save(output_path, quality=70)
        if os.path.exists(output_path):
            client.sendLocalImage(output_path, thread_id=thread_id, thread_type=thread_type, ttl=60000*5,
                                  width=image.width, height=image.height)
            os.remove(output_path)
    except Exception as e:
        client.sendMessage(Message(text=f"• Đã xảy ra lỗi: {str(e)}"), thread_id, thread_type, ttl=60000)

# --------------------- Export ---------------------
def TQD():
    return {
        'thathinh': handle_thathinh_command
    }
