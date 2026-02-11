import requests
import subprocess
import json
import urllib.parse
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageOps
from zlapi.models import *
from zlapi._threads import ThreadType
import time
import random
import tempfile

des = {
    'version': "2.1.3",
    'credits': "Latte",
    'description': "Tạo sticker",
    'power': "Thành viên"
}

success_styles = MultiMsgStyle([
    MessageStyle(offset=0, length=10000, style="color", color="#15a85f", auto_format=False),
    MessageStyle(offset=0, length=10000, style="font", size="8", auto_format=False),
    MessageStyle(offset=0, length=10000, style="bold", auto_format=False)
])

# ============================================================
def check_ffmpeg_webp_support():
    try:
        result = subprocess.run(["ffmpeg", "-codecs"], capture_output=True, text=True, check=True)
        return "libwebp_anim" in result.stdout or "libwebp" in result.stdout
    except:
        return False

# ============================================================
def upload_file_da_dich_vu(duong_dan_file):
    cac_dich_vu = [
        {
            "ten": "Catbox",
            "url": "https://catbox.moe/user/api.php",
            "data": {"reqtype": "fileupload"},
            "key_file": "fileToUpload"
        },
        {
            "ten": "0x0.st",
            "url": "https://0x0.st",
            "data": {},
            "key_file": "file"
        }
    ]
    
    for dich_vu in cac_dich_vu:
        try:
            with open(duong_dan_file, "rb") as f:
                files = {dich_vu['key_file']: f}
                response = requests.post(
                    dich_vu['url'],
                    files=files,
                    data=dich_vu['data'],
                    timeout=30
                )

            if response.status_code == 200:
                url = response.text.strip()
                if url.startswith("http"):
                    print(f"✅ Upload thành công với {dich_vu['ten']}")
                    return url
        except Exception as e:
            print(f"❌ {dich_vu['ten']} thất bại: {e}")
            continue

    return None

# ============================================================
def get_file_type(media_url):
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
            r = requests.get(media_url, stream=True, timeout=15)
            size = 0
            for chunk in r.iter_content(1024 * 64):
                tmp.write(chunk)
                size += len(chunk)
                if size > 5 * 1024 * 1024:
                    break
            tmp_path = tmp.name

        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-count_frames",
                "-show_entries", "stream=nb_read_frames",
                "-of", "json",
                tmp_path
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        data = json.loads(result.stdout or "{}")
        frames = int(data.get("streams", [{}])[0].get("nb_read_frames", 0))
        return "image" if frames <= 1 else "video"

    except:
        return "unknown"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

# ============================================================
def convert_stk_image(media_url, unique_id):
    """
    Convert media URL thành sticker WebP.
    Video dài bao nhiêu cũng được.
    """
    script_dir = os.path.dirname(__file__)
    temp_dir = os.path.join(script_dir, 'cache', 'temp')
    os.makedirs(temp_dir, exist_ok=True)

    temp_input = os.path.join(temp_dir, f"input_{unique_id}")
    temp_webp = os.path.join(temp_dir, f"output_{unique_id}.webp")
    files_to_cleanup = [temp_input, temp_webp]

    try:
        # 1. Tải media
        r = requests.get(media_url, stream=True, timeout=30)
        r.raise_for_status()
        with open(temp_input, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)

        # 2. Kiểm tra file có phải ảnh
        is_image = False
        try:
            with Image.open(temp_input) as img:
                img.verify()
            is_image = True
        except:
            is_image = False

        if is_image:
            # Ảnh tĩnh → bo góc
            with Image.open(temp_input).convert("RGBA") as img:
                img.thumbnail((512, 512), Image.Resampling.LANCZOS)
                corner_radius = max(20, min(img.size) // 8)

                mask = Image.new("L", img.size, 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle([(0, 0), img.size], radius=corner_radius, fill=255)
                img.putalpha(mask)

                img.save(temp_webp, format="WEBP", quality=85)
        else:
            # Video dài → convert thẳng sang WebP animation
            subprocess.run([
                "ffmpeg", "-y", "-i", temp_input,
                "-vf", "scale='min(512,iw)':-2,fps=10",
                "-c:v", "libwebp_anim",
                "-loop", "0",
                "-an",
                "-lossless", "0",
                "-q:v", "60",
                "-preset", "default",
                "-loglevel", "error",
                temp_webp
            ], check=True)

        # 3. Upload
        return upload_file_da_dich_vu(temp_webp)

    except Exception as e:
        print(f"Lỗi convert sticker: {e}")
        return None

    finally:
        for f in files_to_cleanup:
            if os.path.exists(f):
                os.remove(f)

# ============================================================
def convert_spin_image(media_url, unique_id, spin_value=5):
    script_dir = os.path.dirname(__file__)
    temp_dir = os.path.join(script_dir, 'cache', 'temp')
    os.makedirs(temp_dir, exist_ok=True)

    temp_input = os.path.join(temp_dir, f"input_{unique_id}")
    temp_webp = os.path.join(temp_dir, f"spin_{unique_id}.webp")
    files_to_cleanup = [temp_input, temp_webp]

    try:
        r = requests.get(media_url, stream=True, timeout=20)
        r.raise_for_status()
        with open(temp_input, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)

        if get_file_type(media_url) != "image":
            return convert_stk_image(media_url, unique_id)

        with Image.open(temp_input).convert("RGBA") as img:
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            size = min(img.size)
            img = ImageOps.fit(img, (size, size), Image.Resampling.LANCZOS)

            mask = Image.new("L", (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            img.putalpha(mask)

            border_size = 6
            border_color = (210, 255, 190, 255)
            bordered_size = size + border_size * 2
            bordered_img = Image.new("RGBA", (bordered_size, bordered_size), (0, 0, 0, 0))

            border_layer = Image.new("RGBA", (bordered_size, bordered_size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(border_layer)
            draw.ellipse((0, 0, bordered_size, bordered_size), fill=border_color)
            draw.ellipse((border_size, border_size, size + border_size, size + border_size), fill=(0, 0, 0, 0))

            bordered_img.paste(border_layer, (0, 0), border_layer)
            bordered_img.paste(img, (border_size, border_size), img)

            spin_value = max(1, min(spin_value, 15))
            total_frames = 60
            angle_step = 360 / total_frames

            max_duration = 100
            min_duration = 5
            frame_duration = int(max_duration - (spin_value - 1) * (max_duration - min_duration) / 14)

            frames = []
            for i in range(total_frames):
                rotated = bordered_img.rotate(-i * angle_step, resample=Image.BICUBIC)
                rotated = rotated.resize((512, 512), Image.Resampling.LANCZOS)
                frames.append(rotated)

            frames[0].save(
                temp_webp,
                format="WEBP",
                save_all=True,
                append_images=frames[1:],
                duration=frame_duration,
                loop=0,
                quality=90
            )

        return upload_file_da_dich_vu(temp_webp)

    finally:
        for f in files_to_cleanup:
            if os.path.exists(f):
                os.remove(f)

# ============================================================
def handle_stk_command(message, message_object, thread_id, thread_type, author_id, client):
    if not check_ffmpeg_webp_support():
        client.replyMessage(Message(text="➜ FFmpeg không hỗ trợ WebP."),
                            message_object, thread_id, thread_type, ttl=60000)
        return

    if not message_object.quote or not message_object.quote.attach:
        client.replyMessage(Message(text="➜ Vui lòng reply vào ảnh / GIF / video."),
                            message_object, thread_id, thread_type, ttl=60000)
        return

    try:
        attach_data = json.loads(message_object.quote.attach)
    except:
        client.replyMessage(Message(text="➜ Dữ liệu đính kèm không hợp lệ."),
                            message_object, thread_id, thread_type, ttl=60000)
        return

    media_url = attach_data.get('hdUrl') or attach_data.get('href')
    if not media_url:
        client.replyMessage(Message(text="➜ Không tìm thấy URL media."),
                            message_object, thread_id, thread_type, ttl=60000)
        return

    media_url = urllib.parse.unquote(media_url.replace("\\/", "/"))
    if "jxl" in media_url:
        media_url = media_url.replace("jxl", "jpg")

    file_type = get_file_type(media_url)
    if file_type not in ["image", "video"]:
        client.replyMessage(Message(text="➜ Không xác định loại file."),
                            message_object, thread_id, thread_type, ttl=60000)
        return

    msg_lower = message.strip().lower()
    is_spin_mode = "spin" in msg_lower
    spin_value = 5

    if is_spin_mode:
        parts = msg_lower.split()
        for p in parts:
            if p.isdigit():
                spin_value = int(p)
                break
        spin_value = max(1, min(spin_value, 15))

    client.replyMessage(Message(text="⏳ Đang xử lý sticker, vui lòng đợi..."),
                        message_object, thread_id, thread_type, ttl=60000)

    try:
        unique_id = f"{thread_id}_{int(time.time())}_{random.randint(1000, 9999)}"
        if is_spin_mode:
            webp_url = convert_spin_image(media_url, unique_id, spin_value)
        else:
            webp_url = convert_stk_image(media_url, unique_id)

        if not webp_url:
            raise Exception("Upload thất bại.")

        client.sendCustomSticker(
            animationImgUrl=webp_url,
            staticImgUrl=webp_url,
            thread_id=thread_id,
            thread_type=thread_type,
            width=512,
            height=512            
        )

        try:
            user_info = client.fetchUserInfo(author_id)
            username = user_info.changed_profiles.get(author_id, {}).get('zaloName', 'không xác định')
        except:
            username = "bạn"

        tag = f"@{username} "
        message_content = f"{tag} Sticker đã tạo thành công."

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
            ttl=60000
        )

    except Exception as e:
        client.replyMessage(Message(text=f"➜ Lỗi tạo sticker: {e}"),
                            message_object, thread_id, thread_type, ttl=30000)

# ============================================================
def TQD():
    return {'stk': handle_stk_command}
