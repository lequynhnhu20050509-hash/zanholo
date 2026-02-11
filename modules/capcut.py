from zlapi.models import Message
import requests
import os
import time
import tempfile
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from config import PREFIX
import threading
import ffmpeg

# FONT_PATH và các hàm vẽ ảnh giữ nguyên
FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
EMOJI_FONT_PATH = "modules/cache/font/NotoEmoji-Bold.ttf"

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Tải template từ CapCut.",
    'power': "Thành viên"
}

user_states = {}  # {author_id: state}
SEARCH_TIMEOUT = 60  # giây

CONFIG = {
    "base_url": "https://edit-api-sg.capcut.com",
    "search_path": "/lv/v1/cc_web/replicate/search_templates",
    "headers": {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9,vi;q=0.8",
        "app-sdk-version": "48.0.0",
        "appvr": "5.8.0",
        "content-type": "application/json",
        "device-time": "1734146729",
        "lan": "vi-VN",
        "loc": "va",
        "origin": "https://www.capcut.com",
        "pf": "7",
        "priority": "u=1, i",
        "referer": "https://www.capcut.com/",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "sign": "8c69245fb9e23bbe2401518a277ef9d4",
        "sign-ver": "1",
        "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"
    },
    "max_results": 10,
    "time_wait_selection": SEARCH_TIMEOUT
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

def autosave(img, quality=92):
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        img.convert("RGB").save(tf, "JPEG", quality=quality, dpi=(100,100), optimize=True, progressive=True, subsampling=0)
        return tf.name

def cleanup_states():
    while True:
        try:
            current_time = time.time()
            to_delete = [aid for aid, state in user_states.items() if 'time_of_search' in state and current_time - state['time_of_search'] > SEARCH_TIMEOUT]
            for aid in to_delete:
                del user_states[aid]
        except Exception as e:
            print(f"Lỗi cleanup_states: {e}")
        time.sleep(5)

threading.Thread(target=cleanup_states, daemon=True).start()

def search_capcut(query, limit=CONFIG["max_results"]):
    try:
        data = {
            "cc_web_version": 0,
            "count": limit,
            "cursor": "0",
            "enter_from": "workspace",
            "query": query,
            "scene": 1,
            "sdk_version": "86.0.0",
            "search_version": 2
        }
        response = requests.post(
            f"{CONFIG['base_url']}{CONFIG['search_path']}",
            json=data,
            headers=CONFIG["headers"],
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("data", {}).get("video_templates", [])
    except Exception as e:
        print(f"Lỗi search CapCut: {e}")
        return []

def draw_template_list_image(templates):
    CARD_W, CARD_H = 560, 150
    PADDING = 30
    CARD_TOP_OFFSET = 60
    CARD_GAP = 6
    COLS = 1 if len(templates) <= 3 else 2
    ROWS = (len(templates) + COLS - 1) // COLS
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
    for idx, template in enumerate(templates):
        title = template['title']
        cover = template['cover_url']
        view = template.get('play_amount', 0)
        like = template.get('like_count', 0)
        usage = template.get('usage_amount', 0)
        row = idx // COLS
        col = idx % COLS
        cx = PADDING + col * (CARD_W + PADDING)
        cy = PADDING + row * (CARD_H + CARD_GAP + PADDING) + CARD_TOP_OFFSET - CARD_GAP * row
        draw.rounded_rectangle([cx, cy, cx+CARD_W, cy+CARD_H], radius=24, fill=card_color)
        draw.text((cx+10, cy+7), "🎥", font=emoji_font, fill=(255,180,60,255))
        if cover:
            try:
                cover_data = requests.get(cover, timeout=5).content
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
        max_title_width = CARD_W - 185  # Sửa lỗi: Định nghĩa biến đúng tên
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
        icon_gap = 96

        draw.text((info_x, info_y), "👁️", font=emoji_info_font, fill=(90,120,140))
        draw.text((info_x+32, info_y+2), f"{view}", font=font_info, fill=(90,120,140))
        like_offset = icon_gap + 34
        draw.text((info_x+like_offset, info_y), "❤️", font=emoji_info_font, fill=(222, 54, 101))
        draw.text((info_x+like_offset+36, info_y+2), f"{like}", font=font_info, fill=(222, 54, 101))
        comment_offset = icon_gap*2 + 65
        draw.text((info_x+comment_offset, info_y), "🔥", font=emoji_info_font, fill=(90,120,140))
        draw.text((info_x+comment_offset+36, info_y+2), f"{usage}", font=font_info, fill=(90,120,140))

        idx_box_w, idx_box_h = 44, 36
        idx_x = cx + CARD_W - idx_box_w - 8
        idx_y = cy + 10
        draw.rounded_rectangle([idx_x, idx_y, idx_x+idx_box_w, idx_y+idx_box_h], radius=14, fill=(210,220,250,255))
        draw.text(
            (idx_x + idx_box_w//2 - font_index.getlength(str(idx+1))//2, idx_y+6),
            f"{idx+1}", font=font_index, fill=(97, 97, 180)
        )

    main_title = "KẾT QUẢ TÌM KIẾM CAPCUT CỦA LATTE"
    draw.text(
        (WIDTH//2 - get_font(36).getlength(main_title)//2, 18),
        main_title,
        font=get_font(36),
        fill=(255,255,255,240)
    )
    
    

    return autosave(img.convert("RGB"), quality=92)

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
        logger.error(f"Lỗi khi lấy thông tin video {video_url}: {e}")
        return 0, 0, 0

def handle_capcut_command(message, message_object, thread_id, thread_type, author_id, client):
    global user_states
    content = message.strip().split()
    client.sendReaction(message_object, "🎵", thread_id, thread_type)
    
    if len(content) < 2:
        client.replyMessage(
            Message(text=f"Vui lòng nhập từ khóa tìm kiếm.\nVí dụ: {PREFIX}capcut Template Cần Tìm"),
            message_object, thread_id, thread_type, ttl=30000
        )
        return
    
    # Kiểm tra state cho chọn số
    if author_id in user_states:
        state = user_states[author_id]
        time_passed = time.time() - state['time_of_search']
        if time_passed < CONFIG["time_wait_selection"]:
            if not all(item.isdigit() for item in content[1:]):
                return
        else:
            del user_states[author_id]
    
    if all(item.isdigit() for item in content[1:]):
        # Xử lý chọn template
        if author_id not in user_states:
            client.replyMessage(Message(text="Không có dữ liệu tìm kiếm."), message_object, thread_id, thread_type, ttl=30000)
            return
        state = user_states[author_id]
        time_passed = time.time() - state['time_of_search']
        if time_passed > CONFIG["time_wait_selection"]:
            del user_states[author_id]
            client.replyMessage(Message(text="Vui lòng tìm kiếm lại."), message_object, thread_id, thread_type, ttl=30000)
            return
        
        templates = state['templates']
        selected_indices = [int(num) - 1 for num in content[1:]]
        some_valid = False
        for index in selected_indices:
            if index < 0 or index >= len(templates):
                client.replyMessage(Message(text=f"Số thứ tự không hợp lệ: {index + 1}"), message_object, thread_id, thread_type, ttl=30000)
                continue
            some_valid = True
            template = templates[index]
            client.replyMessage(
                Message(text=f"Đang gửi template: {template.get('title', 'Unknown')}\nChờ chút nhé!"),
                message_object, thread_id, thread_type, ttl=120000
            )
            video_url = template.get("video_url")
            if not video_url:
                client.replyMessage(
                    Message(text="Không có link video."),
                    message_object, thread_id, thread_type, ttl=30000
                )
                continue

            # LẤY THÔNG TIN VIDEO THỰC TẾ BẰNG FFMPEG
            duration_ms, width, height = get_video_info(video_url)
            if duration_ms <= 0 or width <= 0 or height <= 0:
                duration_ms = template.get("duration", 90000)  # fallback từ API
                width, height = 1080, 1920
                logger.warning(f"Không lấy được info video CapCut, dùng fallback: {duration_ms}ms, {width}x{height}")

            thumbnail = template.get("cover_url")
            duration_sec = int(duration_ms // 1000)
            text_info = (
                f"🎬 Template: {template.get('title', 'Unknown')}\n"
                f"⏱️ Thời Lượng: {duration_sec}s\n"
                f"👁 ️Lượt Xem: {template.get('play_amount', 0)}\n"
                f"❤ ️Lượt Thích: {template.get('like_count', 0)}\n"
                f"🔥 Lượt Sử Dụng: {template.get('usage_amount', 0)}\n"
                f"🔗 Link Template: {template.get('template_url', 'N/A')}"
            )
            try:                                   
                client.sendRemoteVideo(
                    videoUrl=video_url,                                   
                    thumbnailUrl=thumbnail,      
                    duration=duration_sec,
                    message=Message(text=text_info),
                    thread_id=thread_id,
                    thread_type=thread_type,                                                 
                    width=width,
                    height=height,
                    ttl=3600000
                )
            except Exception as e:
                print(f"Lỗi gửi video: {e}")
                client.sendMessage(
                    Message(text=text_info),
                    thread_id=thread_id,
                    thread_type=thread_type,
                    ttl=60000 
                )	 
        if some_valid:
            del user_states[author_id]
        return
    
    # Tìm kiếm mới
    query = ' '.join(content[1:])
    print(f"Tìm Capcut: {query}")
    templates_raw = search_capcut(query)
    if not templates_raw:
        client.replyMessage(Message(text=f"Không tìm thấy template với: {query}"), message_object, thread_id, thread_type, ttl=30000)
        return
    
    user_states[author_id] = {
        'templates': templates_raw,
        'time_of_search': time.time()
    }
    img_path = draw_template_list_image(templates_raw)
    try:
        with Image.open(img_path) as im:
            width, height = im.size
        client.sendLocalImage(
            img_path,
            thread_id=thread_id,
            thread_type=thread_type,
            width=width,
            height=height,
            ttl=120000,
            message=Message(text=f"Nhập {PREFIX}capcut <số> để tải template ({PREFIX}capcut 3):")
        )
        os.remove(img_path)        
    except Exception as e:
        print(f"Lỗi gửi ảnh: {e}")
        client.replyMessage(Message(text="Lỗi gửi ảnh kết quả!"), message_object, thread_id, thread_type)

def TQD():
    return {
        'capcut': handle_capcut_command
    }