import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import requests
import base64
import emoji
import concurrent.futures
import time
import pytz
from zlapi.models import Message

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Xem dự báo thời tiết",
    'power': "Thành viên"
}

FONT_PATH = "modules/cache/font/NotoSans-Bold.ttf"
EMOJI_FONT_PATH = "modules/cache/font/NotoEmoji-Bold.ttf"
vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')


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
        (ImageDraw.Draw(dummy_image).textbbox((0, 0), "A", font=font)[3] - ImageDraw.Draw(dummy_image).textbbox((0, 0), "A", font=font)[1]) * 1.4
    )
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


def get_location_details(location_name):
    """Lấy tọa độ và địa chỉ từ OpenStreetMap"""
    geocode_url = f"https://nominatim.openstreetmap.org/search?q={location_name}&format=json&limit=1"
    headers = {"User-Agent": "weather-fetch-script/1.0 (contact@example.com)"}
    try:
        response = requests.get(geocode_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                latitude = float(data[0]['lat'])
                longitude = float(data[0]['lon'])
                address = data[0]['display_name']
                return latitude, longitude, address
    except Exception:
        pass
    return None, None, None


def process_weather_image(avatar_url, content, author_name):
    base_font_size = 88
    normal_font = get_font(base_font_size)
    emoji_font = get_emoji_font(base_font_size)
    author_font = get_font(base_font_size + 30)
    combined_text = f"{author_name}\n\n{content}"
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


def handle_weather_command(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh xem thời tiết"""
    try:
        if len(message.split(' ', 1)) <= 1:
            prompt_message = "📝 Vui lòng nhập tên thành phố. Ví dụ: weather Hà Nội"
            client.replyMessage(Message(text=prompt_message), message_object, thread_id, thread_type,ttl=60000)
            return
        
        location_name = message.split(' ', 1)[1]
        latitude, longitude, address = get_location_details(location_name)

        if latitude is None or longitude is None:
            client.sendMessage(Message(text=f"❌ Không tìm thấy địa điểm '{location_name}'"), thread_id, thread_type,ttl=60000)
            return

        
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={latitude}&longitude={longitude}"
            f"&current_weather=true"
            f"&daily=precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min,weathercode"
            f"&timezone=auto"
        )

        response = requests.get(url, headers={"User-Agent": "vminh-weather-bot/1.0"}, timeout=10)
        if response.status_code != 200:
            client.sendMessage(Message(text="❌ Lỗi khi gọi API thời tiết."), thread_id, thread_type,ttl=60000)
            return

        data = response.json()
        daily = data.get('daily', {})
        current = data.get('current_weather', {})

        if not daily or not current:
            client.sendMessage(Message(text="❌ Không có dữ liệu thời tiết hợp lệ."), thread_id, thread_type,ttl=60000)
            return

        
        weather_code = daily['weathercode'][0]
        min_temp = daily['temperature_2m_min'][0]
        max_temp = daily['temperature_2m_max'][0]
        precipitation = daily['precipitation_sum'][0]
        precipitation_probability = daily['precipitation_probability_max'][0]
        current_temp = current.get('temperature', "N/A")

        
        weather_descriptions = {
            0: "☀️ Trời quang đãng",
            1: "🌤 Chủ yếu nắng",
            2: "⛅ Có mây rải rác",
            3: "🌥 Nhiều mây",
            45: "🌫 Sương mù",
            48: "🌫 Sương mù có sương giá",
            51: "🌦 Mưa phùn nhẹ",
            53: "🌦 Mưa phùn vừa",
            55: "🌧 Mưa phùn dày đặc",
            56: "🌧 Mưa phùn lạnh nhẹ",
            57: "🌧 Mưa phùn lạnh nặng",
            61: "🌦 Mưa nhẹ",
            63: "🌧 Mưa vừa",
            65: "⛈️ Mưa lớn",
            66: "🌧 Mưa lạnh nhẹ",
            67: "🌧 Mưa lạnh nặng",
            71: "❄️ Tuyết nhẹ",
            73: "❄️ Tuyết vừa",
            75: "❄️ Tuyết dày đặc",
            77: "🌨 Tuyết bay",
            80: "🌦 Mưa rào nhẹ",
            81: "🌧 Mưa rào vừa",
            82: "⛈️ Mưa rào lớn",
            85: "🌨 Mưa tuyết nhẹ",
            86: "🌨 Mưa tuyết mạnh",
            95: "⛈️ Dông nhẹ hoặc vừa",
            96: "⛈️ Dông kèm mưa đá nhẹ",
            99: "⛈️ Dông kèm mưa đá mạnh"
        }

        weather_description = weather_descriptions.get(weather_code, "❓ Thời tiết không xác định")

        
        msg = (
            f"📍Địa điểm: {location_name}\n"
            f"🗺 Khu vực: {address}\n"
            f"{weather_description}\n"
            f"🌡 Nhiệt độ hiện tại: {current_temp}°C\n"
            f"⬇️ Thấp nhất: {min_temp}°C\n"
            f"⬆️ Cao nhất: {max_temp}°C\n"
            f"🌧 Lượng mưa: {precipitation} mm\n"
            f"☔ Xác suất mưa: {precipitation_probability}%"
        )

        
        user_info = client.fetchUserInfo(author_id) or {}
        user_data = user_info.get('changed_profiles', {}).get(str(author_id), {})
        avatar_url = user_data.get("avatar", None)
        author_name = user_data.get("zaloName", "Unknown")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            image = executor.submit(process_weather_image, avatar_url, msg, author_name).result()

        
        output_path = "modules/cache/weather_temp.png"
        image.save(output_path, quality=70)
        if os.path.exists(output_path):
            client.sendLocalImage(output_path, thread_id=thread_id, thread_type=thread_type,ttl=60000*5,
                                  width=image.width, height=image.height)
            os.remove(output_path)

    except Exception as e:
        pass


def TQD():
    return {
        'thoitiet': handle_weather_command
    }
