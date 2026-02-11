from zlapi.models import Message
import requests
import urllib.parse
import threading
import os
import time
from config import PREFIX

des = {
    'version': "2.1.1",
    'credits': "Latte",
    'description': "Tạo love link",
    'power': "Thành viên"
}

AUDIO_MAP = {
    "ccyld": "Có Chắc Yêu Là Đây",
    "cgm52": "Cô Gái M52",
    "hgedat": "Hẹn Gặp Em Dưới Ánh Trăng",
    "mrtt": "Mượn Rượu Tỏ Tình",
    "nap": "Người Âm Phủ",
    "nnca": "Nơi Này Có Anh",
    "pm": "Phép Màu",
    "thttt": "Tín Hiệu Từ Trái Tim"
}


def get_user_name_by_id(bot, user_id):
    try:
        info = bot.fetchUserInfo(user_id)
        if hasattr(info, "changed_profiles") and user_id in info.changed_profiles:
            profile = info.changed_profiles[user_id]
            return getattr(profile, "zaloName", None) or getattr(profile, "displayName", "Unknown User")
        return "Unknown User"
    except Exception:
        return "Unknown User"


def get_nemg_link(text: str, audio: str):
    base_url = "https://api.nemg.me/love"
    params = {"text": text, "audio": audio}
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("success") and "url" in data:
                return data["url"]
    except Exception:
        pass
    return None


def capture_website(url_to_capture):
    """Chụp ảnh trang web và trả về đường dẫn ảnh (absolute)"""
    try:
        if not url_to_capture.startswith("http://") and not url_to_capture.startswith("https://"):
            url_to_capture = "https://" + url_to_capture

        # thêm cache:none để tránh ảnh bị cũ
        capture_url = f"https://image.thum.io/get/width/1920/fullpage/noanimate/cache:none/{url_to_capture}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }

        res = requests.get(capture_url, headers=headers, timeout=20)
        if not res.ok or "image" not in res.headers.get("Content-Type", ""):
            return None

        image_path = os.path.abspath("modules/cache/lovelink_preview.jpeg")
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        with open(image_path, "wb") as f:
            f.write(res.content)
        return image_path
    except Exception:
        return None


def handle_lovelink_command(message, message_object, thread_id, thread_type, author_id, client):
    user_name = get_user_name_by_id(client, author_id)
    parts = message.strip().split()

    if len(parts) < 2:
        guide = (
            f"❌ Sai cú pháp!\n\n📌 Dùng đúng dạng:\n"
            f"{PREFIX}lovelink <nội_dung> [mã_nhạc]\n\n"
            f"Ví dụ:\n{PREFIX}lovelink Anh yêu em 💕 mrtt\n\n"
            f"🎵 Mã nhạc có sẵn:\n" + "\n".join([f"{k} - {v}" for k, v in AUDIO_MAP.items()]) +
            f"\n\n(Nếu không nhập mã, mặc định là 'mrtt' - Mượn Rượu Tỏ Tình)\n\n[Ask by: {user_name}]"
        )
        client.replyMessage(Message(text=guide), message_object, thread_id, thread_type, ttl=60000)
        return

    audio_code = "nnca"
    if len(parts) >= 3 and parts[-1] in AUDIO_MAP:
        audio_code = parts[-1]
        love_text = ' '.join(parts[1:-1]).strip()
    else:
        love_text = ' '.join(parts[1:]).strip()

    if not love_text:
        client.replyMessage(Message(text=f"❌ Nội dung không được để trống!\n\n[Ask by: {user_name}]"),
                            message_object, thread_id, thread_type, ttl=60000)
        return

    client.replyMessage(Message(text=f"💌 Đang tạo link tình yêu với nhạc {AUDIO_MAP[audio_code]}...\n⏳ Vui lòng chờ..."),
                        message_object, thread_id, thread_type, ttl=60000)

    def do_create():
        result_url = get_nemg_link(love_text, audio_code)
        if not result_url:
            client.sendMessage(Message(text=f"❌ Không thể tạo link! API đang lỗi hoặc mạng không ổn định.\n\n[Ask by: {user_name}]"),
                               thread_id, thread_type, ttl=60000)
            return

        # đợi API render xong link
        time.sleep(0.5)
        img_path = capture_website(result_url)

        caption = f"""
💞 [ 𝙇𝙊𝙑𝙀 𝙇𝙄𝙉𝙆 ] 💞
━━━━━━━━━━━━━━━━━━━━━━━
👤 Người dùng: {user_name}

🎵 Nhạc nền: {AUDIO_MAP[audio_code]}
📝 Nội dung: {love_text}
🔗 Link: {result_url}
━━━━━━━━━━━━━━━━━━━━━━━
💗 Nhấp vào link để xem điều bất ngờ 💗
""".strip()

        if img_path and os.path.exists(img_path):
            client.sendLocalImage(
                img_path,
                message=Message(text=caption),
                thread_id=thread_id,
                thread_type=thread_type,
                ttl=60000*10
            )
            os.remove(img_path)
        else:
            client.sendMessage(Message(text=caption), thread_id, thread_type, ttl=60000)

    threading.Thread(target=do_create, daemon=True).start()


def TQD():
    return {
        'lovelink': handle_lovelink_command
    }
    
 
 