import os
import logging
import urllib.parse
import json
import socket
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from zlapi.models import Message
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import tempfile
from config import PREFIX 
import ffmpeg

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Tìm kiếm video tiktok theo từ khóa",
    'power': "Thành viên"
}


logger = logging.getLogger(__name__)
os.makedirs("modules/cache", exist_ok=True)
VIDEO_CACHE = {}
AUTO_TIKTOK = {}  # Lưu trạng thái tự động tải video cho mỗi thread_id

# Session với retry nhiều hơn
session = requests.Session()
_retry = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"]
)
session.mount("https://", HTTPAdapter(max_retries=_retry))

# Hỗ trợ proxy qua biến môi trường
_tt_proxy = os.environ.get("TT_PROXY")
if _tt_proxy:
    session.proxies.update({
        "http": _tt_proxy,
        "https": _tt_proxy,
    })
    logger.info("Using TT_PROXY=%s", _tt_proxy)

FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
EMOJI_FONT_PATH = "modules/cache/font/NotoEmoji-Bold.ttf"

def get_user_name_by_id(bot, user_id):
    try:
        info = bot.fetchUserInfo(user_id)
        if hasattr(info, "changed_profiles") and user_id in info.changed_profiles:
            profile = info.changed_profiles[user_id]
            return getattr(profile, "zaloName", None) or getattr(profile, "displayName", "Unknown User")
        return "Unknown User"
    except Exception:
        return "Unknown User"

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

def get_video_info(video_url):
    try:
        probe = ffmpeg.probe(video_url)
        video_stream = next((s for s in probe["streams"] if s["codec_type"] == "video"), None)
        if not video_stream:
            raise ValueError("Không tìm thấy luồng video!")

        duration = float(video_stream.get("duration") or probe["format"].get("duration", 0)) * 1000
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        return duration, width, height
    except Exception as e:
        print(f"Lỗi khi lấy thông tin video {video_url}: {e}")
        return 0, 720, 1280

def ms_to_mmss(ms):
    try:
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02}:{seconds:02}"
    except:
        return "??:??"

def _host_port_open(host, port=443, timeout=3):
    try:
        socket.create_connection((host, port), timeout=timeout)
        return True
    except Exception as e:
        logger.debug("Host %s:%s not reachable: %s", host, port, e)
        return False

def fetch_from_api(url, headers=None, timeout=(5, 20)):
    headers = headers or {"User-Agent": "Mozilla/5.0 (X11; Linux) AppleWebKit/537.36"}
    try:
        r = session.get(url, headers=headers, timeout=timeout)
    except Exception as e:
        logger.warning("fetch_from_api: request error for %s -> %s", url, e)
        return None

    if r.status_code != 200:
        logger.warning("fetch_from_api: non-200 %s for %s", r.status_code, url)
        return None

    text = r.text.strip()
    if not text:
        logger.warning("fetch_from_api: empty response for %s", url)
        return None

    try:
        return r.json()
    except ValueError:
        try:
            start = text.find("{")
            if start != -1:
                return json.loads(text[start:])
            start = text.find("[")
            if start != -1:
                return json.loads(text[start:])
        except Exception:
            logger.exception("fetch_from_api: failed to parse JSON for %s", url)
            return None
    except Exception as e:
        logger.exception("fetch_from_api: unknown error for %s: %s", url, e)
        return None

def tiktok_preview(url):
    """
    Lấy dữ liệu video TikTok từ API TikWM
    :param url: Link TikTok (rút gọn hoặc gốc)
    :return: dict chứa link video, nhạc, cover, title, author
    """
    api_url = "https://www.tikwm.com/api/"
    payload = {
        "url": url,
        "count": 12,
        "cursor": 0,
        "web": 1,
        "hd": 1
    }
    headers = {
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "user-agent": "Mozilla/5.0"
    }

    try:
        response = session.post(api_url, data=payload, headers=headers, timeout=(5, 20))
    except Exception as e:
        logger.warning("tiktok_preview: request error for %s -> %s", url, e)
        return None

    if response.status_code != 200:
        logger.warning("tiktok_preview: non-200 %s for %s", response.status_code, url)
        return None

    try:
        result = response.json()
    except ValueError:
        logger.exception("tiktok_preview: failed to parse JSON for %s", url)
        return None

    if result.get("code") != 0:
        logger.warning("tiktok_preview: API error: %s", result.get("msg"))
        return None

    data = result.get("data")
    if not data:
        logger.warning("tiktok_preview: no data in response for %s", url)
        return None

    domain = "https://www.tikwm.com"
    video_info = {
        "video_id": data.get("id"),
        "title": data.get("title") or "Không có mô tả",
        "author": data.get("author", {}).get("nickname", "Không rõ"),
        "images": data.get("images", []),
        "music": data.get("music_info", {}).get("play") or data.get("music", ""),
        "unique_id": data.get("author", {}).get("unique_id", "Không rõ"),
        "play": domain + (data.get("play") or "") if data.get("play") else "",
        "wmplay": domain + (data.get("wmplay") or "") if data.get("wmplay") else "",
        "hdplay": domain + (data.get("hdplay") or "") if data.get("hdplay") else "",
        "music": domain + (data.get("music") or "") if data.get("music") else "",
        "cover": domain + (data.get("cover") or "") if data.get("cover") else "",
        "duration": data.get("duration", 0) * 1000,
        "play_count": data.get("play_count", 0),
        "digg_count": data.get("digg_count", 0),
        "comment_count": data.get("comment_count", 0)
    }
    return video_info

def _extract_videos(data):
    if not data:
        return None
    if isinstance(data, dict):
        core = data.get("data") or data
        if isinstance(core, dict):
            for k in ("videos", "aweme_list", "feeds", "list", "items"):
                v = core.get(k)
                if isinstance(v, list):
                    return [
                        {
                            "video_id": video.get("video_id") or video.get("aweme_id") or video.get("id"),
                            "title": video.get("title") or video.get("desc") or "Không có mô tả",
                            "cover": video.get("cover") or video.get("thumbnail") or "",
                            "duration": video.get("duration", 0) * 1000,
                            "play_count": video.get("play_count", 0),
                            "digg_count": video.get("digg_count") or video.get("like_count", 0),
                            "comment_count": video.get("comment_count") or video.get("comments", 0),
                            "nickname": video.get("author", {}).get("nickname", "Không rõ"),
                            "unique_id": video.get("author", {}).get("unique_id", "Không rõ"),
                            "play": video.get("play", ""),
                            "wmplay": video.get("wmplay", "")
                        }
                        for video in v
                    ]
        if "videos" in data and isinstance(data["videos"], list):
            return [
                {
                    "video_id": video.get("video_id") or video.get("aweme_id") or video.get("id"),
                    "title": video.get("title") or video.get("desc") or "Không có mô tả",
                    "cover": video.get("cover") or video.get("thumbnail") or "",
                    "duration": video.get("duration", 0) * 1000,
                    "play_count": video.get("play_count", 0),
                    "digg_count": video.get("digg_count") or video.get("like_count", 0),
                    "comment_count": video.get("comment_count") or video.get("comments", 0),
                    "nickname": video.get("author", {}).get("nickname", "Không rõ"),
                    "unique_id": video.get("author", {}).get("unique_id", "Không rõ"),
                    "play": video.get("play", ""),
                    "wmplay": video.get("wmplay", "")
                }
                for video in data["videos"]
            ]
    return None

def _safe_video_url(video_data):
    if not isinstance(video_data, dict):
        return None
    candidates = [
        "hdplay", "play", "wmplay", "play_url", "download_url", "video_url", "url"
    ]
    for k in candidates:
        v = video_data.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, dict):
            for subk in ("url", "uri", "src", "play", "wmplay", "hdplay"):
                sv = v.get(subk)
                if isinstance(sv, str) and sv.strip():
                    return sv.strip()
        if isinstance(v, list) and v:
            first = v[0]
            if isinstance(first, str) and first.strip():
                return first.strip()
            if isinstance(first, dict):
                for subk in ("url", "uri", "src", "play", "wmplay", "hdplay"):
                    sv = first.get(subk)
                    if isinstance(sv, str) and sv.strip():
                        return sv.strip()
    nested = video_data.get("video")
    if isinstance(nested, dict):
        for k in ("play_addr", "playUrl", "download_addr", "hdplay"):
            v = nested.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None

def autosave(img, quality=92):
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        img.convert("RGB").save(
            tf,
            "JPEG",
            quality=quality,
            dpi=(100,100),
            optimize=True,
            progressive=True,
            subsampling=0
        )
        return tf.name

def draw_video_list_image(videos):
    CARD_W, CARD_H = 560, 150
    PADDING = 30
    CARD_TOP_OFFSET = 60
    CARD_GAP = 6
    COLS = 1 if len(videos) <= 3 else 2
    ROWS = (len(videos) + COLS - 1) // COLS
    WIDTH = CARD_W * COLS + PADDING * (COLS + 1)
    HEIGHT = CARD_H * ROWS + PADDING * (ROWS + 1) + 30 + CARD_TOP_OFFSET - (CARD_GAP * (ROWS - 1))

    bg_color = (34, 34, 58)
    card_color = (255, 255, 255, 238)
    font_title = get_font(28)
    font_small = get_font(19)
    font_info = get_font(22)
    font_index = get_font(26)
    emoji_font = get_emoji_font(32)
    emoji_info_font = get_emoji_font(26)

    img = Image.new("RGBA", (WIDTH, HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)
    for idx, video in enumerate(videos):
        row = idx // COLS
        col = idx % COLS
        cx = PADDING + col * (CARD_W + PADDING)
        cy = PADDING + row * (CARD_H + CARD_GAP + PADDING) + CARD_TOP_OFFSET - CARD_GAP * row
        draw.rounded_rectangle([cx, cy, cx+CARD_W, cy+CARD_H], radius=24, fill=card_color)
        draw.text((cx+10, cy+7), "🎥", font=emoji_font, fill=(255,180,60,255))
        if video.get("cover"):
            try:
                cover_url = video["cover"]
                if cover_url.startswith("/"):
                    cover_url = "https://www.tikwm.com" + cover_url
                cover_data = requests.get(cover_url, timeout=5).content
                with Image.open(BytesIO(cover_data)) as cover_img:
                    cover_img = cover_img.convert("RGBA")
                    min_side = min(cover_img.width, cover_img.height)
                    left = (cover_img.width - min_side) // 2
                    top = (cover_img.height - min_side) // 2
                    cover_img = cover_img.crop((left, top, left+min_side, top+min_side))
                    cover_img = cover_img.resize((95, 95), Image.LANCZOS)
                    img.paste(cover_img, (cx+44, cy+25), cover_img)
            except:
                pass

        title_x = cx + 160
        title_y = cy + 22
        max_title_width = CARD_W - 185
        title = video.get("title", "Không có mô tả")
        title_lines = []
        line = ""
        for word in title.split():
            test_line = (line + " " if line else "") + word
            if font_title.getlength(test_line) > max_title_width and line:
                title_lines.append(line)
                line = word
            else:
                line = test_line
        if line:
            title_lines.append(line)
        for l in title_lines[:2]:
            draw.text((title_x, title_y), l, font=font_title, fill=(40, 40, 70))
            title_y += font_title.size + 1

        info_y = cy + CARD_H - 48
        info_x = title_x
        icon_gap = 94
     

        duration = ms_to_mmss(video.get("duration", 0))
        draw.text((info_x, info_y), "⏱", font=emoji_info_font, fill=(90,120,140))
        draw.text((info_x+32, info_y+2), f"{duration}", font=font_info, fill=(90,120,140))
        like_offset = icon_gap + 27
        draw.text((info_x+like_offset, info_y), "❤️", font=emoji_info_font, fill=(222, 54, 101))
        draw.text((info_x+like_offset+36, info_y+2), f"{video.get('digg_count', 0)}", font=font_info, fill=(222, 54, 101))
        view_offset = icon_gap*2 + 63
        draw.text((info_x+view_offset, info_y), "👁", font=emoji_info_font, fill=(90,120,140))
        draw.text((info_x+view_offset+36, info_y+2), f"{video.get('play_count', 0)}", font=font_info, fill=(90,120,140))

        idx_box_w, idx_box_h = 44, 36
        idx_x = cx + CARD_W - idx_box_w - 8
        idx_y = cy + 10
        draw.rounded_rectangle([idx_x, idx_y, idx_x+idx_box_w, idx_y+idx_box_h], radius=14, fill=(210,220,250,255))
        draw.text(
            (idx_x + idx_box_w//2 - font_index.getlength(str(idx+1))//2, idx_y+6),
            f"{idx+1}", font=font_index, fill=(97, 97, 180)
        )

    main_title = "KẾT QUẢ TÌM KIẾM TIKTOK"
    draw.text(
        (WIDTH//2 - get_font(36).getlength(main_title)//2, 18),
        main_title,
        font=get_font(36),
        fill=(255,255,255,240)
    )
      

    out_path = autosave(img, quality=92)
    return out_path

def is_tiktok_url(url):
    try:
        parsed = urllib.parse.urlparse(url.strip())
        return parsed.hostname and (
            "tiktok.com" in parsed.hostname or
            "vt.tiktok.com" in parsed.hostname or
            "www.tiktok.com" in parsed.hostname
        )
    except:
        return False

def send_tiktok_video(video, user_name, message_object, thread_id, thread_type, client):
    

    nickname = video.get("author") or video.get("nickname", "Không rõ")
    unique_id = video.get("unique_id", "Không rõ")
    caption = video.get("title") or "Không có mô tả"

    images = video.get("images", [])
    music_url = video.get("music", "")

    if images:
        temp_paths = []

        # Lấy ảnh đầu để xác định kích thước
        first_img_url = images[0]
        try:
            r = requests.get(first_img_url, stream=True, timeout=15)
            first_temp_path = "modules/cache/temp_image_0.jpeg"
            with open(first_temp_path, "wb") as f:
                f.write(r.content)
            with Image.open(first_temp_path) as img:
                w, h = img.size
        except:
            w, h = 1200, 1600
            first_temp_path = None

        # Tải tất cả ảnh
        for i, img_url in enumerate(images):
            temp_path = f"modules/cache/temp_image_{i}.jpeg"
            try:
                r = requests.get(img_url, stream=True, timeout=15)
                with open(temp_path, "wb") as f:
                    f.write(r.content)
            except:
                # Nếu ảnh đầu đã thành công thì copy lại kích thước
                if i == 0 and first_temp_path:
                    temp_path = first_temp_path
            temp_paths.append(temp_path)

        # Gửi nhiều ảnh cùng lúc, dùng w,h của ảnh đầu tiên
        client.sendMultiLocalImage( 
            temp_paths,
            thread_id,
            thread_type,
            width=w,
            height=h,
            message=None,
            ttl=60000*60
        )

        # Gửi nhạc nếu có
        if music_url:
            client.sendRemoteVoice(music_url, thread_id, thread_type, ttl=60000*60)

        # Xóa file tạm
        for path in temp_paths:
            if path and os.path.exists(path):
                os.remove(path)
        return

    # 📌 Trường hợp không có ảnh thì gửi video
    domain = "https://www.tikwm.com"
    video_play_url = video.get("hdplay") if video.get("hdplay") else video.get("play")
    
    duration, width, height = get_video_info(video_play_url)
    thumbnail = video.get("cover") or ""
    if thumbnail.startswith("/"):
        thumbnail = "https://www.tikwm.com" + thumbnail
    
    try:
        client.sendRemoteVideo(
            videoUrl=video_play_url,
            thumbnailUrl=thumbnail,
            duration=int(duration),
            message=Message(text=f"[{user_name}]\n\n🧸Người dùng: {nickname} ({unique_id})\n\n📽 Tiêu đề: {caption}"),
            thread_id=thread_id,
            thread_type=thread_type,
            width=width,
            height=height,
            ttl=60000*60
        )
        return
    except Exception as e:
        pass

    # Nếu cả ảnh và video đều không có
    client.sendMessage(
        Message(text="⚠️ Không tìm thấy video, ảnh hay âm thanh để gửi."),
        thread_id, thread_type, ttl=60000
    )

def handle_tt_command(message, message_object, thread_id, thread_type, author_id, client):
    client.sendReaction(message_object, "🎵", thread_id, thread_type)
    try:
        user_name = get_user_name_by_id(client, author_id) or "Người dùng"

        # Kiểm tra lệnh bật/tắt tự động tải video
        parts = message.strip().split(maxsplit=1)
        if len(parts) == 1 and parts[0].lower() == (PREFIX + "tt"):
    
            client.replyMessage(Message(
                text=f"❌ Vui lòng nhập từ khóa, số video hoặc URL.\n📌 Ví dụ: {PREFIX}tt gái xinh, {PREFIX}tt 2, {PREFIX}tt https://www.tiktok.com/..."
            ), message_object, thread_id, thread_type, ttl=60000)
            return

        arg = parts[1].strip() if len(parts) > 1 else ""

        # Kiểm tra nếu tin nhắn chỉ chứa URL TikTok và tự động tải bật
        if not message.lower().startswith(PREFIX + "tt") and AUTO_TIKTOK.get(thread_id, True):
            if is_tiktok_url(message):
                video_data = tiktok_preview(message)
                if video_data:
                    send_tiktok_video(video_data, user_name, message_object, thread_id, thread_type, client)
                else:
                    client.replyMessage(Message(
                        text="❌ Không thể lấy dữ liệu video từ URL."
                    ), message_object, thread_id, thread_type, ttl=60000)
                return
            return

        # Nếu arg là số → kiểm tra cache trước
        if arg.isdigit():
            index = int(arg) - 1
            videos = VIDEO_CACHE.get(thread_id)
            if videos:  # Nếu có cache, gửi video và xóa cache
                if index < 0 or index >= len(videos):
                    client.replyMessage(Message(
                        text=f"❌ Chỉ có {len(videos)} video trong danh sách. Hãy chọn từ 1 đến {len(videos)}."
                    ), message_object, thread_id, thread_type, ttl=60000)
                    return
                video = videos[index]
                if send_tiktok_video(video, user_name, message_object, thread_id, thread_type, client):
                    # Xóa cache sau khi gửi video thành công
                    VIDEO_CACHE.pop(thread_id, None)                    
                return
            else:
                # Nếu không có cache, coi số là từ khóa để tìm kiếm
                arg = str(arg)

        # Nếu arg là URL TikTok
        if is_tiktok_url(arg):
            video_data = tiktok_preview(arg)
            if video_data:
                send_tiktok_video(video_data, user_name, message_object, thread_id, thread_type, client)
            else:
                client.replyMessage(Message(
                    text="❌ Không thể lấy dữ liệu video từ URL."
                ), message_object, thread_id, thread_type, ttl=60000)
            return

        # Arg là từ khóa → tìm video
        keyword_raw = arg
        keyword = urllib.parse.quote_plus(keyword_raw)

        apis = [
            f"https://www.tikwm.com/api/feed/search?keywords={keyword}&count=15",            
        ]

        videos = None
        for api in apis:
            parsed = urllib.parse.urlparse(api)
            host = parsed.hostname
            if host and not _host_port_open(host, 443, timeout=3):
                logger.warning("Host %s unreachable; skip %s", host, api)
                continue
            data = fetch_from_api(api, timeout=(5, 15))
            videos = _extract_videos(data)
            if videos:
                logger.info("Got videos from %s", api)
                break
            else:
                logger.debug("No videos from %s", api)

        if not videos:
            search_link = f"https://www.tiktok.com/search?q={urllib.parse.quote(keyword_raw)}"
            client.replyMessage(Message(
                text=(
                    f"❌ Không tìm thấy hoặc không thể kết nối tới API TikTok hiện tại.\n"
                    f"👉 Thử mở trực tiếp: {search_link}\n"
                    f"Nếu bạn đang chạy bot trên host bị chặn, hãy thử bật VPN hoặc cấu hình proxy (TT_PROXY)."
                )
            ), message_object, thread_id, thread_type, ttl=60000)
            return

        # Lưu cache tối đa 15 video
        VIDEO_CACHE[thread_id] = videos[:15]

        # In danh sách video ra console
        lines = [f"📌 Tìm thấy {len(VIDEO_CACHE[thread_id])} video (từ khóa: {keyword_raw})"]
        for i, v in enumerate(VIDEO_CACHE[thread_id], 1):
            title = (v.get("title") or v.get("desc") or "Không có mô tả")
            likes = v.get("digg_count") or v.get("like_count") or 0
            comments = v.get("comment_count") or v.get("comments") or 0
            lines.append(f"{i}. {title[:60]}... ❤️{likes} 💬{comments}")        
        print("\n".join(lines))

        # Gửi danh sách video dưới dạng ảnh
        img_path = draw_video_list_image(videos[:15])
        try:
            with Image.open(img_path) as im:
                width, height = im.size
            client.sendLocalImage(
                img_path,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                message=Message(text=f"➜ Nhập {PREFIX}tt <số> (1-{len(videos)}) để chọn video."),
                ttl=60000*2
            )
            os.remove(img_path)
        except Exception as e:
            logger.exception("Failed to send image: %s", e)
            client.replyMessage(Message(
                text="❌ Lỗi khi gửi ảnh danh sách video."
            ), message_object, thread_id, thread_type, ttl=60000)

    except Exception as e:
        logger.exception("TikTok command error: %s", e)
        client.replyMessage(Message(
            text=f"❌ Lỗi xử lý TikTok: {e}"
        ), message_object, thread_id, thread_type, ttl=60000)

def TQD():
    return {
        'tt': handle_tt_command
    }
    
