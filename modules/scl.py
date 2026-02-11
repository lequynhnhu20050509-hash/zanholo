import os
import logging
import requests
from bs4 import BeautifulSoup
import re
import time
import tempfile
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from config import PREFIX
import subprocess
from zlapi.models import Message, ThreadType
import json
from fake_useragent import UserAgent  
import random  
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
EMOJI_FONT_PATH = "modules/cache/font/NotoEmoji-Bold.ttf"

AUDIO_QUALITY_PRESET = 'Balanced'

des = {
    'version': "3.1.0",
    'credits': "Latte",
    'description': "Tải nhạc SoundCloud.",
    'power': "Thành viên"
}

SEARCH_TIMEOUT = 120

os.makedirs(os.path.join(os.path.dirname(__file__), 'cache'), exist_ok=True)

client_id_cache = None

def get_user_name(client, uid):
    try:
        user_info = client.fetchUserInfo(uid)
        author_info = user_info.changed_profiles.get(str(uid), {}) if user_info and user_info.changed_profiles else {}
        return author_info.get('zaloName', 'Không xác định')
    except Exception as e:
        logging.error(f"[get_user_name] Lỗi khi lấy tên user {uid}: {e}")
        return 'Không xác định'

def get_headers():
    """Tạo tiêu đề ngẫu nhiên cho yêu cầu HTTP như code mẫu."""
    user_agent = UserAgent()
    headers = {
        "User-Agent": user_agent.random,
        "Accept-Language": random.choice([
            "en-US,en;q=0.9",
            "fr-FR,fr;q=0.9",
            "es-ES,es;q=0.9",
            "de-DE,de;q=0.9",
            "zh-CN,zh;q=0.9"
        ]),
        "Referer": 'https://soundcloud.com/',
        "Upgrade-Insecure-Requests": "1"
    }
    return headers

def get_font(size):
    try: return ImageFont.truetype(FONT_PATH, size)
    except: return ImageFont.load_default()

def get_emoji_font(size):
    try: return ImageFont.truetype(EMOJI_FONT_PATH, size)
    except: return ImageFont.load_default()

def delete_file(file_path):
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logging.info(f"[delete_file] Đã xóa file tạm: {file_path}")
    except Exception as e:
        logging.error(f"[delete_file] Lỗi khi xóa file {file_path}: {e}")

def autosave(img, quality=92):
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        img.convert("RGB").save(tf.name, "JPEG", quality=quality, dpi=(100, 100), optimize=True, progressive=True, subsampling=0)
        return tf.name

def upload_to_temp_service(file_path):
    try:
        logging.info(f"Đang tải {os.path.basename(file_path)} lên dịch vụ lưu trữ tạm thời...")
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            response = requests.post('https://tmpfiles.org/api/v1/upload', files=files, timeout=300)
            response.raise_for_status()

        data = response.json()
        if data.get('status') == 'success':
            url = data['data']['url'].replace('tmpfiles.org/', 'tmpfiles.org/dl/')
            logging.info(f"Tải lên dịch vụ tạm thời thành công. URL: {url}")
            return url
        else:
            error_msg = data.get('error', {}).get('message', 'Lỗi không xác định từ tmpfiles.org')
            raise Exception(f"Tải file lên server tạm thời thất bại: {error_msg}")
    except requests.exceptions.Timeout:
        logging.error("[upload_to_temp_service] Request timed out.")
        raise Exception("Không thể tải file lên server tạm thời: Quá thời gian chờ.")
    except Exception as e:
        logging.error(f"[upload_to_temp_service] Error: {e}")
        raise Exception(f"Không thể tải file lên server tạm thời: {e}")
        
def convert_audio_high_quality(input_path, output_path):
    command = []
    encoder_to_try = 'libfdk_aac'

    if AUDIO_QUALITY_PRESET == 'High_Quality':
        command = ['ffmpeg', '-y', '-i', input_path, '-vn', '-c:a', encoder_to_try, '-vbr', '5', output_path]
        logging.info(f"Đang thử chuyển đổi với encoder chất lượng cao: {encoder_to_try} (VBR 5)")

    else:
        command = ['ffmpeg', '-y', '-i', input_path, '-vn', '-c:a', 'aac', '-b:a', '128k', output_path]
        logging.info("Đang chuyển đổi với encoder tiêu chuẩn: aac (128kbps)")

    try:
        subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', timeout=400)
        logging.info(f"FFmpeg chuyển đổi thành công với lệnh: {' '.join(command)}")
        return output_path

    except FileNotFoundError:
        logging.error("FFmpeg not found. Vui lòng đảm bảo FFmpeg đã được cài đặt và nằm trong PATH hệ thống.")
        raise Exception("FFmpeg không được tìm thấy. Chủ bot cần cài đặt nó trên server.")

    except subprocess.TimeoutExpired:
        logging.error(f"FFmpeg conversion timed out for {input_path}")
        raise Exception("Lỗi khi xử lý audio: Quá thời gian cho phép. File có thể quá lớn.")

    except subprocess.CalledProcessError as e:
        if AUDIO_QUALITY_PRESET == 'High_Quality' and f"Unknown encoder '{encoder_to_try}'" in e.stderr:
            logging.warning(f"Encoder '{encoder_to_try}' không được tìm thấy. Tự động chuyển sang encoder 'aac' tiêu chuẩn.")
            fallback_command = ['ffmpeg', '-y', '-i', input_path, '-vn', '-c:a', 'aac', '-b:a', '192k', output_path]
            try:
                subprocess.run(fallback_command, check=True, capture_output=True, text=True, encoding='utf-8', timeout=400)
                logging.info(f"FFmpeg chuyển đổi thành công với lệnh dự phòng: {' '.join(fallback_command)}")
                return output_path
            except Exception as fallback_e:
                logging.error(f"Lỗi ngay cả khi dùng encoder dự phòng. stderr: {fallback_e.stderr if hasattr(fallback_e, 'stderr') else fallback_e}")
                raise Exception(f"Lỗi khi xử lý audio bằng FFmpeg (cả phương án dự phòng): {fallback_e}")
        else:
            logging.error(f"FFmpeg conversion failed. stderr: {e.stderr}")
            raise Exception(f"Lỗi khi xử lý audio bằng FFmpeg: {e.stderr}")

def process_audio(audio_url, title):
    original_file_path, compressed_file_path = None, None
    try:
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)[:50]
        temp_id = int(time.time() * 1000)

        logging.info(f"Đang tải audio gốc cho '{title}' từ {audio_url}")
        response = requests.get(audio_url, headers=get_headers(), stream=True, timeout=100)
        response.raise_for_status()

        CACHE_DIR_SCL = os.path.join(os.path.dirname(__file__), 'cache')
        original_file_path = os.path.join(CACHE_DIR_SCL, f"{safe_title}_{temp_id}_original.mp3")
        with open(original_file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
        logging.info(f"Đã tải xong file gốc: {original_file_path}")

        compressed_file_path = os.path.join(CACHE_DIR_SCL, f"{safe_title}_{temp_id}_rachviec_obj_conmemay.aac")
        convert_audio_high_quality(original_file_path, compressed_file_path)

        delete_file(original_file_path)
        original_file_path = None

        public_url = upload_to_temp_service(compressed_file_path)
        return public_url, compressed_file_path
    finally:
        if original_file_path and os.path.exists(original_file_path):
            delete_file(original_file_path)

def get_client_id():
    global client_id_cache
    if client_id_cache:
        print(f"[DEBUG] Dùng client_id cache: {client_id_cache}")
        return client_id_cache

    try:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'client_id.txt')

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                client_id_cache = file.read().strip()
                if client_id_cache:
                    print(f"[DEBUG] Đọc client_id từ file: {client_id_cache}")
                    return client_id_cache
                else:
                    print("[DEBUG] File client_id.txt rỗng, đang lấy mới...")

        # Scrape SoundCloud
        print("[DEBUG] Đang truy cập SoundCloud để lấy client_id...")
        res = requests.get('https://soundcloud.com/', headers=get_headers())
        res.raise_for_status()

        soup = BeautifulSoup(res.text, 'html.parser')
        script_tags = soup.find_all('script', {'crossorigin': True})
        urls = [tag.get('src') for tag in script_tags if tag.get('src') and tag.get('src').startswith('https')]

        if not urls:
            raise Exception('Không tìm thấy URL script SoundCloud.')

        res = requests.get(urls[-1], headers=get_headers())
        res.raise_for_status()

        match = re.search(r'client_id:"(.*?)"', res.text)
        if not match:
            raise Exception('Không tìm thấy client_id trong script.')

        client_id_cache = match.group(1)
        print(f"[DEBUG] Lấy client_id mới: {client_id_cache}")

        # Lưu vào file
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(client_id_cache)
        print(f"[DEBUG] Đã lưu client_id vào file: {file_path}")

        return client_id_cache

    except Exception as e:
        print(f"[ERROR] Lấy client_id thất bại: {e}")
        return None


def wait_for_client_id():
    client_id = get_client_id()
    while not client_id:
        time.sleep(1)  # Sửa loop vô tận
        client_id = get_client_id()
    return client_id    

def ms_to_mmss(ms):
    try:
        seconds = ms // 1000
        minutes = seconds // 60
        seconds %= 60
        return f"{minutes:02}:{seconds:02}"
    except: return "??:??"

def get_song_details(link):
    try:
        client_id = wait_for_client_id()
        api_url = f'https://api-v2.soundcloud.com/resolve?url={link}&client_id={client_id}'
        response = requests.get(api_url, headers=get_headers(), timeout=5)
        response.raise_for_status()
        data = response.json()
        return {
            "duration": ms_to_mmss(data.get("duration", 0)),
            "duration_ms": data.get("duration", 0),
            "playback_count": data.get("playback_count", 0),
            "likes_count": data.get("likes_count", 0),
            "comment_count": data.get("comment_count", 0),
            "artist": data.get("user", {}).get("username", "Unknown Artist")
        }
    except Exception as e:
        logging.error(f"[get_song_details] Lỗi khi lấy chi tiết bài hát {link}: {e}")
        return { "duration": "??:??", "duration_ms": 0, "playback_count": 0, "likes_count": 0, "comment_count": 0, "artist": "Unknown Artist" }

def search_songs(query):
    try:
        base_url = 'https://soundcloud.com'
        search_url = f'https://m.soundcloud.com/search?q={requests.utils.quote(query)}'
        response = requests.get(search_url, headers=get_headers(), timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        songs = []
        url_pattern = re.compile(r'^/[^/]+/[^/]+$')
        for element in soup.select('li > div'):
            a_tag = element.select_one('a')
            if a_tag and a_tag.has_attr('href'):
                relative_url = a_tag['href']
                if url_pattern.match(relative_url):
                    title = a_tag.get('aria-label', '').strip()
                    link = base_url + relative_url
                    img_tag = element.select_one('img')
                    cover_url = img_tag['src'] if img_tag and img_tag.has_attr('src') else ""
                    detail = get_song_details(link)
                    songs.append((link, title, cover_url, detail.get('duration'), detail.get('playback_count'), detail.get('likes_count'), detail.get('comment_count'), detail.get('artist')))
            if len(songs) >= 10: break
        return songs
    except Exception as e:
        logging.error(f"[search_songs] Error: {e}")
        return []

def get_music_stream_url(link):
    try:
        client_id = wait_for_client_id()
        api_url = f'https://api-v2.soundcloud.com/resolve?url={link}&client_id={client_id}'
        response = requests.get(api_url, headers=get_headers(), timeout=5)
        response.raise_for_status()
        data = response.json()
        for transcode in data.get('media', {}).get('transcodings', []):
            if transcode.get('format', {}).get('protocol') == 'progressive':
                stream_url_req = requests.get(f"{transcode['url']}?client_id={client_id}", headers=get_headers(), timeout=5)
                stream_url_req.raise_for_status()
                return stream_url_req.json().get('url')
        raise Exception("Không tìm thấy stream URL hợp lệ.")
    except Exception as e:
        logging.error(f"[get_music_stream_url] Lỗi khi lấy stream URL cho {link}: {e}")
        return None

def get_track_cover(link):
    try:
        client_id = wait_for_client_id()
        api_url = f'https://api-v2.soundcloud.com/resolve?url={link}&client_id={client_id}'
        response = requests.get(api_url, headers=get_headers(), timeout=5)
        response.raise_for_status()
        data = response.json()
        cover_url = data.get("artwork_url")
        if cover_url: cover_url = cover_url.replace('-large', '-t500x500')
        else:
            cover_url = data.get("user", {}).get("avatar_url", "")
            if cover_url: cover_url = cover_url.replace('-large', '-t500x500')
        return cover_url
    except Exception as e:
        logging.error(f"[get_track_cover] Lỗi khi lấy ảnh bìa cho {link}: {e}")
        return None

def draw_song_list_image(songs):
    CARD_W, CARD_H = 560, 150; PADDING = 30; CARD_TOP_OFFSET = 60; CARD_GAP = 6
    COLS = 1 if len(songs) <= 3 else 2; ROWS = (len(songs) + COLS - 1) // COLS
    WIDTH = CARD_W * COLS + PADDING * (COLS + 1); HEIGHT = CARD_H * ROWS + PADDING * (ROWS + 1) + 30 + CARD_TOP_OFFSET - (CARD_GAP * (ROWS - 1))
    bg_color = (34, 34, 58); card_color = (255, 255, 255, 238)
    font_title = get_font(28); font_small = get_font(19); font_info = get_font(24); font_index = get_font(26)
    emoji_font = get_emoji_font(32); emoji_info_font = get_emoji_font(28)
    img = Image.new("RGBA", (WIDTH, HEIGHT), bg_color); draw = ImageDraw.Draw(img)
    for idx, (link, title, cover, duration, playback_count, like_count, comment_count, artist) in enumerate(songs):
        row = idx // COLS; col = idx % COLS
        cx = PADDING + col * (CARD_W + PADDING); cy = PADDING + row * (CARD_H + CARD_GAP + PADDING) + CARD_TOP_OFFSET - CARD_GAP * row
        draw.rounded_rectangle([cx, cy, cx+CARD_W, cy+CARD_H], radius=24, fill=card_color)
        draw.text((cx+10, cy+7), "🎵", font=emoji_font, fill=(255,180,60,255))
        if cover:
            try:
                cover_data = requests.get(cover, headers=get_headers(), timeout=5).content
                with Image.open(BytesIO(cover_data)) as cover_img:
                    cover_img = cover_img.convert("RGBA"); min_side = min(cover_img.width, cover_img.height)
                    left = (cover_img.width - min_side) // 2; top = (cover_img.height - min_side) // 2
                    cover_img = cover_img.crop((left, top, left+min_side, top+min_side)).resize((95, 95), Image.LANCZOS)
                    img.paste(cover_img, (cx+44, cy+5), cover_img)
            except Exception as e: logging.warning(f"Không thể tải ảnh bìa: {e}")
        title_x = cx + 160; title_y = cy + 22; max_title_width = CARD_W - 185
        title_lines = []; line = ""
        for word in title.split():
            test_line = (line + " " if line else "") + word
            if font_title.getlength(test_line) > max_title_width and line: title_lines.append(line); line = word
            else: line = test_line
        if line: title_lines.append(line)
        for l in title_lines[:2]: draw.text((title_x, title_y), l, font=font_title, fill=(40, 40, 70)); title_y += font_title.size + 1
        info_y_duration = cy + 5 + 95 + 10; info_x = cx + 24
        draw.text((info_x, info_y_duration), "⏱", font=emoji_info_font, fill=(90,120,140))
        draw.text((info_x + emoji_info_font.getlength("⏱") + 5, info_y_duration + 2), duration, font=font_info, fill=(90,120,140))
        info_y_stats = cy + CARD_H - 48; info_x_stats = title_x
        draw.text((info_x_stats, info_y_stats), "🎧", font=emoji_info_font, fill=(90,120,140))
        playback_width = font_info.getlength(str(playback_count))
        draw.text((info_x_stats + emoji_info_font.getlength("🎧") + 5, info_y_stats + 2), f"{playback_count:,}", font=font_info, fill=(90,120,140))
        next_x = info_x_stats + emoji_info_font.getlength("🎧") + 5 + playback_width + 10
        draw.text((next_x, info_y_stats), "❤️", font=emoji_info_font, fill=(222, 54, 101))
        like_width = font_info.getlength(str(like_count))
        draw.text((next_x + emoji_info_font.getlength("❤️") + 5, info_y_stats + 2), f"{like_count:,}", font=font_info, fill=(222, 54, 101))
        next_x += emoji_info_font.getlength("❤️") + 5 + like_width + 10
        draw.text((next_x, info_y_stats), "💬", font=emoji_info_font, fill=(90,120,140))
        comment_width = font_info.getlength(str(comment_count))
        draw.text((next_x + emoji_info_font.getlength("💬") + 5, info_y_stats + 2), f"{comment_count:,}", font=font_info, fill=(90,120,140))
        idx_box_w, idx_box_h = 44, 36; idx_x = cx + CARD_W - idx_box_w - 8; idx_y = cy + 10
        draw.rounded_rectangle([idx_x, idx_y, idx_x+idx_box_w, idx_y+idx_box_h], radius=14, fill=(210,220,250,255))
        draw.text((idx_x + idx_box_w//2 - font_index.getlength(str(idx+1))//2, idx_y+6), f"{idx+1}", font=font_index, fill=(97, 97, 180))
    main_title = "KẾT QUẢ TÌM KIẾM SOUNDCLOUD"
    draw.text((WIDTH//2 - get_font(36).getlength(main_title)//2, 18), main_title, font=get_font(36), fill=(255,255,255,240))
    footer = f"➜ Nhập lựa chọn của bạn"
    draw.text((WIDTH//2 - font_small.getlength(footer)//2, HEIGHT-28), footer, font=font_small, fill=(210,210,230))
    out_path = autosave(img)
    return out_path

def draw_song_detail_image(title, artist, duration, playback_count, like_count, comment_count, cover):
    CARD_W = 560
    PADDING = 30
    BASE_CARD_H = 180  # đủ gọn

    font_title = get_font(27)
    font_small = get_font(18)
    font_info = get_font(18)
    emoji_info_font = get_emoji_font(22)

    # Chuẩn bị title
    formatted_title = title
    max_title_width = CARD_W - 220
    title_lines, line = [], ""
    for word in formatted_title.split():
        test_line = (line + " " if line else "") + word
        if font_title.getlength(test_line) > max_title_width and line:
            title_lines.append(line)
            line = word
        else:
            line = test_line
    if line:
        title_lines.append(line)
    num_title_lines = min(len(title_lines), 2)
    extra_height = (font_title.size + 1) * (num_title_lines - 1)
    CARD_H = BASE_CARD_H + extra_height
    WIDTH = CARD_W + 2 * PADDING
    HEIGHT = CARD_H + 2 * PADDING

    # Vẽ nền
    bg_color = (34, 34, 58)
    card_color = (255, 255, 255, 238)
    img = Image.new("RGBA", (WIDTH, HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)

    cx, cy = PADDING, PADDING
    draw.rounded_rectangle([cx, cy, cx + CARD_W, cy + CARD_H], radius=24, fill=card_color)

    # From SoundCloud
    from_text = "From SoundCloud"
    from_width = font_small.getlength(from_text)
    from_y = cy + 8
    draw.text((cx + (CARD_W - from_width) / 2, from_y), from_text, font=font_small, fill=(255, 165, 0))

    # Cover
    cover_size = 120
    cover_x = cx + 25
    cover_y = from_y + 25
    if cover:
        try:
            cover_data = requests.get(cover, headers=get_headers(), timeout=5).content
            with Image.open(BytesIO(cover_data)) as cover_img:
                cover_img = cover_img.convert("RGBA")
                min_side = min(cover_img.width, cover_img.height)
                left = (cover_img.width - min_side) // 2
                top = (cover_img.height - min_side) // 2
                cover_img = cover_img.crop((left, top, left + min_side, top + min_side)).resize((cover_size, cover_size), Image.LANCZOS)
                img.paste(cover_img, (cover_x, cover_y), cover_img)
        except Exception as e:
            logging.warning(f"Không thể tải ảnh bìa chi tiết: {e}")

    # Text bên phải cover
    spacing = 20
    text_x = cover_x + cover_size + spacing
    text_y = cover_y + 5

    # Title
    for l in title_lines[:2]:
        draw.text((text_x, text_y), l, font=font_title, fill=(40, 40, 70))
        text_y += font_title.size + 4

    # Duration ngay dưới title
    duration_text = f"Thời lượng: {duration}"
    draw.text((text_x, text_y), duration_text, font=font_small, fill=(100, 100, 120))
    text_y += font_small.size + 3

    # Artist ngay sau duration
    draw.text((text_x, text_y), f"Artist: {artist}", font=font_small, fill=(255, 165, 0))
    text_y += font_small.size + 3

    # Stats ngay sau artist
    stats_y = text_y
    info_x = text_x

    draw.text((info_x, stats_y), "🎧", font=emoji_info_font, fill=(90, 120, 140))
    draw.text((info_x + emoji_info_font.getlength("🎧") + 2, stats_y + 3), f"{playback_count:,}", font=font_info, fill=(90, 120, 140))

    next_x = info_x + emoji_info_font.getlength("🎧") + 2 + font_info.getlength(f"{playback_count:,}") + 15
    draw.text((next_x, stats_y), "❤️", font=emoji_info_font, fill=(222, 54, 101))
    draw.text((next_x + emoji_info_font.getlength("❤️") + 2, stats_y + 3), f"{like_count:,}", font=font_info, fill=(222, 54, 101))

    next_x += emoji_info_font.getlength("❤️") + 2 + font_info.getlength(f"{like_count:,}") + 15
    draw.text((next_x, stats_y), "💬", font=emoji_info_font, fill=(90, 120, 140))
    draw.text((next_x + emoji_info_font.getlength("💬") + 2, stats_y + 3), f"{comment_count:,}", font=font_info, fill=(90, 120, 140))

    out_path = autosave(img)
    return out_path



def handle_scl_command(message_text, message_object, thread_id, thread_type, author_id, client):
    user_states = client.scl_user_states
    name = get_user_name(client, author_id)
    parts = message_text.strip().split()
    query_or_choice = " ".join(parts[1:]) if len(parts) > 1 else ""
    platform = "soundcloud"
    compressed_path_to_delete = None

    try:
        if query_or_choice.isdigit() and author_id in user_states:
            state = user_states[author_id]
            if time.time() - state['time_of_search'] > SEARCH_TIMEOUT:
                del user_states[author_id]
                client.replyMessage(Message(text=f"➜ {name}, kết quả đã hết hạn, vui lòng tìm lại."), message_object, thread_id, thread_type, ttl=60000)
                return

            songs = state['songs']
            index = int(query_or_choice) - 1
            if not (0 <= index < len(songs)):
                client.replyMessage(Message(text=f"➜ {name}, lựa chọn không hợp lệ."), message_object, thread_id, thread_type, ttl=60000)
                return

            del user_states[author_id]

            link, title, _, _, _, _, _, artist = songs[index]
            detail = get_song_details(link)
            duration_ms = detail.get('duration_ms', 0)
            if duration_ms > 5400000:
                client.replyMessage(Message(text=f"➜ {name}, server chưa thể tải nhạc với thời lượng trên 90 phút."), message_object, thread_id, thread_type, ttl=60000)
                return

            client.replyMessage(Message(text=f"➜ Đang xử lý bài hát '{title}' với chất lượng cao nhất.\nQuá trình này có thể mất vài phút, vui lòng chờ..."), message_object, thread_id, thread_type, ttl=60000)

            audio_stream_url = get_music_stream_url(link)
            if not audio_stream_url:
                raise Exception("Không thể lấy stream URL từ SoundCloud.")

            public_url, compressed_path_to_delete = process_audio(audio_stream_url, title)
            voice_url = public_url

            if not voice_url:
                raise Exception("Lỗi trong quá trình xử lý và tải lên âm thanh.")

            file_size = os.path.getsize(compressed_path_to_delete) if compressed_path_to_delete and os.path.exists(compressed_path_to_delete) else 0
            cover_url = get_track_cover(link)
            detail_image_path = draw_song_detail_image(
                title, artist, detail['duration'],
                detail['playback_count'], detail['likes_count'], detail['comment_count'],
                cover_url
            )
            with Image.open(detail_image_path) as im: width, height = im.size
            client.sendLocalImage(
                detail_image_path,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                message=Message(text=f"> From SoundCloud <\n🎵Nhạc Bạn Chọn Đây!\n{title} - {artist}\n🎧 Mời bạn thưởng thức"),
                ttl=60000*60
            )
            delete_file(detail_image_path)

            
            client.sendRemoteVoice(
                voice_url,
                thread_id=thread_id,
                thread_type=thread_type,
                fileSize=int(file_size),
                ttl=60000*60
            )
            return
            

        if not query_or_choice:
            client.replyMessage(Message(text=f"➜ {name}, vui lòng nhập tên bài hát. Ví dụ: {PREFIX}scl Hạnh Phúc Nhé"), message_object, thread_id, thread_type, ttl=60000)
            return

        client.replyMessage(Message(text=f"➜ Đang tìm kiếm '{query_or_choice}'..."), message_object, thread_id, thread_type, ttl=30000)
        songs = search_songs(query_or_choice)
        if not songs:
            client.replyMessage(Message(text=f"➜ {name}, không tìm thấy kết quả cho '{query_or_choice}'."), message_object, thread_id, thread_type, ttl=60000)
            return

        user_states[author_id] = {'songs': songs, 'time_of_search': time.time()}
        img_path = draw_song_list_image(songs)
        with Image.open(img_path) as im: width, height = im.size
        client.sendLocalImage(
            img_path, thread_id=thread_id, thread_type=thread_type, width=width, height=height,
            message=Message(text=f"➜ {name}, đây là kết quả cho '{query_or_choice}'.\n➜ Vui lòng reply số để tải."),
            ttl=120000
        )
        delete_file(img_path)
        
    except Exception as e:
        logging.error(f"Lỗi trong handle_scl_command: {e}", exc_info=True)
        client.replyMessage(Message(text=f"➜ {name}, đã xảy ra lỗi nghiêm trọng: {e}"), message_object, thread_id, thread_type, ttl=60000)
    finally:
        if compressed_path_to_delete:
            delete_file(compressed_path_to_delete)

def TQD():
    return { 'scl': handle_scl_command }

