import json
import requests
import ffmpeg
import yt_dlp
import time
import logging
import os
import re
from pathlib import Path
from PIL import Image
from zlapi.models import *
from config import PREFIX

des = {
    'version': "3.1.0",
    'credits': "Latte",
    'description': "Auto download TikTok + Facebook + YouTube",
    'power': "Thành viên"
}

success_styles = MultiMsgStyle([
    MessageStyle(offset=0, length=10000, style="color", color="#15a85f", auto_format=False),
    MessageStyle(offset=0, length=10000, style="font", size="10", auto_format=False),
    MessageStyle(offset=0, length=10000, style="bold", size="10", auto_format=False)
])



DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
STATE_FILE = DATA_DIR / "autodown_mxh_threads.json"


if STATE_FILE.exists():
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        autodowntik_enabled_threads = set(json.load(f))
else:
    autodowntik_enabled_threads = set()

processed_links = set()  # Anti spam

def save_state():
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(autodowntik_enabled_threads), f, ensure_ascii=False, indent=2)


def autodown(message, message_object, thread_id, thread_type, author_id, client):
    content = message.strip().split()
    if len(content) < 2:
        client.replyMessage(Message(text=f"Dùng: {PFEFIX}atd on/off"), message_object, thread_id, thread_type,ttl=30000)
        return

    cmd = content[1].lower()
    if cmd == "on":
        autodowntik_enabled_threads.add(thread_id)
        save_state()
        client.replyMessage(Message(text="Đã bật autodown trong nhóm này!"), 
                           message_object, thread_id, thread_type, ttl=60000)
    elif cmd == "off":
        autodowntik_enabled_threads.discard(thread_id)
        save_state()
        client.replyMessage(Message(text="Đã tắt autodown trong nhóm này."), 
                           message_object, thread_id, thread_type, ttl=60000)
    else:
        client.replyMessage(Message(text="Chỉ dùng: atdtt on  hoặc  atdtt off"), message_object, thread_id, thread_type)


def get_video_info(video_url):
    try:
        probe = ffmpeg.probe(video_url)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)

        if video_stream:
            duration = float(video_stream['duration']) * 1000
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            return duration, width, height
        else:
            raise Exception("Không tìm thấy luồng video trong URL")
    except Exception as e:
        raise Exception(f"Lỗi khi lấy thông tin video: {str(e)}")


def get_content_message(message_object):
    if message_object.msgType == 'chat.recommended':            
        return ""

    texts = []

    if hasattr(message_object, 'text') and isinstance(message_object.text, str):
        texts.append(message_object.text)
    elif message_object.get('msg') and isinstance(message_object.get('msg'), str):
        texts.append(message_object.get('msg'))

    content = message_object.get('content', {})
    if isinstance(content, str):
        texts.append(content)
    elif isinstance(content, dict):
        if content.get('title'):
            texts.append(content['title'])
        if content.get('href'):
            texts.append(content['href'])
        if content.get('description'):
            texts.append(content['description'])
        if content.get('params') and isinstance(content['params'], str):
            try:
                data = json.loads(content['params'])
                if data.get('mediaTitle'):
                    texts.append(data['mediaTitle'])
                if data.get('href'):
                    texts.append(data['href'])
                if data.get('url'):
                    texts.append(data['url'])
            except:
                pass

    attach = message_object.get('attach', {})
    if isinstance(attach, dict):
        if attach.get('title'):
            texts.append(attach['title'])
        if attach.get('href'):
            texts.append(attach['href'])
        if attach.get('description'):
            texts.append(attach['description'])
        if attach.get('params') and isinstance(attach['params'], str):
            try:
                data = json.loads(attach['params'])
                if data.get('mediaTitle'):
                    texts.append(data['mediaTitle'])
                if data.get('href'):
                    texts.append(data['href'])
                if data.get('url'):
                    texts.append(data['url'])
            except:
                pass

    return " ".join(filter(None, texts))


def extract_links(message_object):
    raw = get_content_message(message_object)
    if not raw: 
        return []

    raw = re.sub(r'\s+', ' ', raw)
    raw = raw.replace("tiktok . com", "tiktok.com").replace("tiktok .com", "tiktok.com")
    raw = raw.replace("fb . watch", "fb.watch").replace("facebook . com", "facebook.com")

    patterns = [
        r"https?://[^\s]+tiktok\.com/[^\s]*",
        r"https?://[^\s]+vm\.tiktok\.com/[^\s]*",
        r"https?://[^\s]+vt\.tiktok\.com/[^\s]*",
        r"https?://[^\s]+fb\.watch/[^\s]*",
        r"https?://[^\s]+facebook\.com/[^\s]*",
        r"https?://[^\s]+m\.facebook\.com/[^\s]*",
        r"https?://youtu\.be/[^\s?]+",
        r"https?://youtube\.com/shorts/[^\s?]+",
        r"https?://(www\.)?youtube\.com/watch\?v=[^\s&]+"
    ]

    links = []
    for pat in patterns:
        found = re.findall(pat, raw, re.IGNORECASE)
        for url in found:
            url = url.split("&")[0].split("?")[0].rstrip(".,!?")
            if not url.startswith("http"):
                url = "https://" + url
            links.append(url)
    return list(dict.fromkeys(links))

def handle_message(message, message_object, thread_id, thread_type, author_id, client):
    if thread_id not in autodowntik_enabled_threads:
        return

    links = extract_links(message_object)
    if not links: return

    for link in links:
        if link in processed_links: continue
        processed_links.add(link)

        client.sendReaction(message_object, "💧", thread_id, thread_type)

        try:
            if "tiktok.com" in link or "vm.tiktok.com" in link:
                downtik(f"*downtik {link}", message_object, thread_id, thread_type, author_id, client)
            elif "facebook.com" in link or "fb.watch" in link:
                download_facebook(link, message_object, thread_id, thread_type, author_id,client)
            elif "youtube.com" in link or "youtu.be" in link:
                download_youtube(link, message_object, thread_id, thread_type, author_id,client)
        except Exception as e:
            client.sendMessage(Message(text=f"Lỗi: {str(e)}"), thread_id, thread_type)

        processed_links.discard(link)


def downtik(message, message_object, thread_id, thread_type, author_id, client):
    import requests
    from PIL import Image

    content = message.strip().split()
    if len(content) < 2:
        client.replyMessage(
            Message(text="Vui lòng nhập một đường link TikTok hợp lệ."),
            message_object, thread_id, thread_type, ttl=60000
        )
        return

    video_url = content[1].strip()

    try:
        api_url = "https://www.tikwm.com/api/"
        payload = {
            "url": video_url,
            "count": 12,
            "cursor": 0,
            "web": 1,
            "hd": 1
        }
        headers = {
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "user-agent": "Mozilla/5.0"
        }

        response = requests.post(api_url, data=payload, headers=headers, timeout=20)
        data = response.json()

        if data.get("code") != 0:
            raise Exception(f"Lỗi API TikWM: {data.get('msg')}")

        video_data = data["data"]
        title = video_data.get("title") or "Không có tiêu đề"
        author = video_data.get("author", {}).get("nickname", "Không rõ")
        unique_id = video_data.get("author", {}).get("unique_id", "Không rõ")

        

        # ========== CASE ẢNH ==========
        images = video_data.get("images", [])
        if isinstance(images, str):
            try:
                images = json.loads(images)
            except:
                images = []

        if images:
            temp_paths = []

            first_url = images[0]
            first_temp = f"modules/cache/tik_first.jpg"
            r = requests.get(first_url, stream=True, timeout=15)
            with open(first_temp, "wb") as f:
                f.write(r.content)

            with Image.open(first_temp) as img:
                w, h = img.size

            temp_paths.append(first_temp)

            for i, url in enumerate(images[1:], start=1):
                path = f"modules/cache/tik_{i}.jpg"
                try:
                    r = requests.get(url, stream=True, timeout=15)
                    with open(path, "wb") as f:
                        f.write(r.content)
                    temp_paths.append(path)
                except:
                    pass
            try:
                user_info = client.fetchUserInfo(author_id)
                username = user_info.changed_profiles.get(author_id, {}).get('zaloName', 'không xác định')
            except:
                username = "bạn"

        
            tag = f"@{username} "
            message_content = f"{tag} 👉 Đây là ảnh và nhạc của bạn"

            offset = message_content.index(tag)
            length = len(tag) 
        
            msg_intro = Message(
                 text=message_content,                        
                  mention=Mention(author_id, length=length, offset=offset),
                 style=success_styles
            )

            client.replyMessage(
                                 msg_intro,
                                 message_object,
                                 thread_id,
                                 thread_type,
                                 ttl=60000*10
                             )      
            client.sendMultiLocalImage(
                temp_paths,
                thread_id,
                thread_type,
                width=w,
                height=h,           
                ttl=60000*60
            )

            for p in temp_paths:
                if os.path.exists(p):
                    os.remove(p)

            music_url = video_data.get("music_info", {}).get("play")
            if music_url:
                client.sendRemoteVoice(music_url, thread_id, thread_type,ttl=60000*60)

            return

        
        domain = "https://www.tikwm.com"
        play_url = domain + (video_data.get("hdplay") or video_data.get("play"))   
        duration, w, h = get_video_info(play_url)
        try:
            user_info = client.fetchUserInfo(author_id)
            username = user_info.changed_profiles.get(author_id, {}).get('zaloName', 'không xác định')
        except:
            username = "bạn"

        # --- Tạo message tag người dùng ---
        tag = f"@{username} "
        message_content = f"{tag} 👉 Đây là video của bạn"

        offset = message_content.index(tag)
        length = len(tag) 
        
        msg_intro = Message(
            text=message_content,                        
            mention=Mention(author_id, length=length, offset=offset),
            style=success_styles
        )

        client.replyMessage(
                                 msg_intro,
                                 message_object,
                                 thread_id,
                                 thread_type,
                                 ttl=60000*10
                             )      
        client.sendRemoteVideo(
                play_url,
                domain + video_data.get("cover", ""),
                duration=int(duration),
                message=Message(text=f"🎥 From Tiktok\n🎬 Tiêu đề: {title}\n👤 Kênh: {author} | {unique_id}"),
                thread_id=thread_id,
                thread_type=thread_type,
                width=w,
                height=h,
                ttl=60000*60
        )
        return

        client.sendMessage(Message(text="Không tìm thấy video hoặc ảnh để gửi."), thread_id, thread_type,ttl=30000)

    except Exception as e:
        client.sendMessage(Message(text=f"Lỗi: {str(e)}"), thread_id, thread_type,ttl=30000)

            

def upload_to_uguu(file_path):
    try:
        with open(file_path, 'rb') as f:
            resp = requests.post("https://uguu.se/upload", files={'files[]': f}, timeout=90)
            resp.raise_for_status()
            return resp.json()['files'][0]['url']
    except Exception as e:
        print(f"Upload uguu lỗi: {e}")
        return None

def download_facebook(url, message_object, thread_id, thread_type, author_id,client):
    try:
        
        api = f"https://api.nemg.me/all?link={requests.utils.quote(url)}"
        data = requests.get(api).json()

        images = [m["url"] for m in data.get("medias", []) if m.get("type") == "image"]
        if images:
            title = data.get("title", "Facebook Post")
            author = data.get("author", "Facebook")
            

            paths = []
            w, h = 720, 1280
            for i, img_url in enumerate(images):
                path = f"modules/cache/fb_img_{thread_id}_{int(time.time())}_{i}.jpg"
                r = requests.get(img_url, stream=True, timeout=20)
                with open(path, "wb") as f: f.write(r.content)
                paths.append(path)
                if i == 0:
                    try: w, h = Image.open(path).size
                    except: pass
            try:
                user_info = client.fetchUserInfo(author_id)
                username = user_info.changed_profiles.get(author_id, {}).get('zaloName', 'không xác định')
            except:
                username = "bạn"

        
            tag = f"@{username} "
            message_content = f"{tag} 👉 Đây là ảnh của bạn"

            offset = message_content.index(tag)
            length = len(tag) 
        
            msg_intro = Message(
                 text=message_content,                        
                  mention=Mention(author_id, length=length, offset=offset),
                 style=success_styles
            )

            client.replyMessage(
                                 msg_intro,
                                 message_object,
                                 thread_id,
                                 thread_type,
                                 ttl=60000*10
                             )      
            client.sendMultiLocalImage(paths, thread_id, thread_type,ttl=60000*60, width=w, height=h)
            for p in paths:
                if os.path.exists(p): os.remove(p)
            return

        
        os.makedirs("modules/cache", exist_ok=True)
        ydl_opts = {
            'format': 'best[height<=1080]/best',
            'outtmpl': f'modules/cache/fb_{thread_id}_{int(time.time())}. %(ext)s',
            'merge_output_format': 'mp4',
            'quiet': True,
            'retries': 10,
            'fragment_retries': 10,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)

        if not os.path.exists(video_path):
            raise Exception("yt-dlp không tải được video")

        upload_url = upload_to_uguu(video_path)
        if not upload_url:
            raise Exception("Upload uguu thất bại")

        title = info.get("title", "Facebook Video")
        uploader = info.get("uploader", "Facebook")
        thumbnail = info.get("thumbnail", "")
        duration,w, h = get_video_info(upload_url)
        try:
            user_info = client.fetchUserInfo(author_id)
            username = user_info.changed_profiles.get(author_id, {}).get('zaloName', 'không xác định')
        except:
            username = "bạn"

        # --- Tạo message tag người dùng ---
        tag = f"@{username} "
        message_content = f"{tag} 👉 Đây là video của bạn"

        offset = message_content.index(tag)
        length = len(tag) 
        
        msg_intro = Message(
            text=message_content,                        
            mention=Mention(author_id, length=length, offset=offset),
            style=success_styles
        )

        client.replyMessage(
                                 msg_intro,
                                 message_object,
                                 thread_id,
                                 thread_type,
                                 ttl=60000*10
                             )         
        client.sendRemoteVideo(
            videoUrl=upload_url,
            thumbnailUrl=thumbnail,
            duration=int(duration),
            width=w,
            height=h,
            message=Message(text=f"🎥 From Facebook\n🎬 Tiêu đề: {title}\n👤 Người đăng: {uploader}"),
            thread_id=thread_id,
            thread_type=thread_type,
            ttl=60000*60
        )
        if os.path.exists(video_path):
            os.remove(video_path)

    except Exception as e:
        client.sendMessage(Message(text=f"Lỗi Facebook: {str(e)}"), thread_id, thread_type,ttl=30000)


def download_youtube(url, message_object, thread_id, thread_type, author_id, client):
    try:
        os.makedirs("modules/cache", exist_ok=True)

        # ==== TỐI ƯU TỐC ĐỘ ====
        ydl_opts = {
            'format': 'bv*[vcodec^=avc1][height<=1080]+ba[acodec^=mp4a]/bv*[height<=1080]+ba/best',
            'outtmpl': f'modules/cache/yt_{thread_id}_{int(time.time())}.%(ext)s',
            'merge_output_format': 'mp4',

            # Tăng tốc tải
            'concurrent_fragments': 60,
            'retries': 10,
            'fragment_retries': 10,
            'skip_unavailable_fragments': True,

            # Tắt warning + log
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,

            # Tối ưu phân tích YouTube cho tốc độ nhanh
            'force_generic_extractor': False,
        }

        # ==== TẢI VIDEO ====
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        if not os.path.exists(file_path):
            raise Exception("Tải video thất bại")

        # ==== UPLOAD ====
        upload_url = upload_to_uguu(file_path)
        if not upload_url:
            raise Exception("Upload Uguu thất bại")

        # ==== LẤY VIDEO INFO ====
        title = info.get("title", "YouTube Video")
        channel = info.get("uploader", "Unknown")
        thumbnail = info.get("thumbnail", "")

        duration, w, h = get_video_info(upload_url)

        # ==== LẤY USERNAME ====
        try:
            user_info = client.fetchUserInfo(author_id)
            username = user_info.changed_profiles.get(author_id, {}).get('zaloName', 'không xác định')
        except:
            username = "bạn"

        # ==== MESSAGE TAG ====
        tag = f"@{username} "
        message_content = f"{tag}👉 Đây là video của bạn"

        offset = message_content.index(tag)
        length = len(tag)

        msg_intro = Message(
            text=message_content,
            mention=Mention(author_id, length=length, offset=offset),
            style=success_styles
        )

        client.replyMessage(
            msg_intro,
            message_object,
            thread_id,
            thread_type,
            ttl=60000*10
        )

        # ==== GỬI VIDEO ====
        client.sendRemoteVideo(
            videoUrl=upload_url,
            thumbnailUrl=thumbnail,
            duration=int(duration),
            width=w,
            height=h,
            message=Message(text=f"🎥 From YouTube\n🎬 Tiêu đề: {title}\n🌐 Kênh: {channel}"),
            thread_id=thread_id,
            thread_type=thread_type,
            ttl=60000*60
        )

        # Xóa file tạm
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        client.sendMessage(Message(text=f"Lỗi YouTube: {str(e)}"), thread_id, thread_type,ttl=30000)

def TQD():
    return {'atd': autodown}
    
 
