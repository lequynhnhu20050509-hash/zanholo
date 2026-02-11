import requests
from bs4 import BeautifulSoup
import random
from zlapi import ZaloAPI
from zlapi.models import Message
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import emoji

des = {
    'version': "7.5.0",
    'credits': "Latte",
    'description': "Bói Tình Yêu",
    'power': "Thành viên"
}

# ========================= DOWNLOAD AVATAR =========================
def download_avatar(url, size=300):
    try:
        if not url:
            return None
        r = requests.get(url, timeout=5)
        img = Image.open(BytesIO(r.content)).convert("RGBA")
        img = img.resize((size, size), Image.LANCZOS)
        # mask bo tròn
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)
        return img
    except:
        return None

EMOJI_FONT_PATH = "modules/cache/font/NotoEmoji-Bold.ttf"

def render_boi_image(name1, name2, percent, avatar1, avatar2, kieu_boi_title="Kết quả duyên phận"):
    W, H = 1080, 900

    # Màu nền theo % (nhạt → đậm)
    pink_light = (255, 228, 237)
    pink_dark = (255, 100, 150)
    t = percent / 100
    bg = tuple(int(pink_light[i]*(1-t) + pink_dark[i]*t) for i in range(3))
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    # Fonts
    font_title = ImageFont.truetype("modules/cache/font/BeVietnamPro-Bold.ttf", 70)
    font_name = ImageFont.truetype("modules/cache/font/BeVietnamPro-Bold.ttf", 50)
    font_percent = ImageFont.truetype("modules/cache/font/BeVietnamPro-Bold.ttf", 45)
    font_heart = ImageFont.truetype(EMOJI_FONT_PATH, 120)       # 💖 giữa avatar
    font_emoji_title = ImageFont.truetype(EMOJI_FONT_PATH, 70)  # 💞 đầu/cuối title

    # ===== AVATAR =====
    AVT_SIZE = 220
    if avatar1:
        avatar1 = avatar1.resize((AVT_SIZE, AVT_SIZE), Image.LANCZOS)
    if avatar2:
        avatar2 = avatar2.resize((AVT_SIZE, AVT_SIZE), Image.LANCZOS)

    # ===== 💖 giữa 2 avatar, căn ngang & dọc =====
    heart_text = "💖"
    bbox_heart = draw.textbbox((0,0), heart_text, font=font_heart)
    hw = bbox_heart[2] - bbox_heart[0]
    hh = bbox_heart[3] - bbox_heart[1]

    # Tạm đặt x,y avatar trước khi paste
    if avatar1 and avatar2:
        # Xét khoảng cách mặc định giữa 💖 và avatar
        gap = 50
        # Tâm ngang
        center_x = W // 2
        # Tâm dọc
        center_y = H // 2 - 50
        # Vị trí avatar
        x1 = center_x - AVT_SIZE - hw//2 - gap
        y1 = center_y - AVT_SIZE//2
        x2 = center_x + hw//2 + gap
        y2 = center_y - AVT_SIZE//2
        # Vị trí 💖
        heart_x = center_x - hw//2
        heart_y = center_y - hh//2
    else:
        # Nếu chỉ có 1 avatar hoặc không có, vẫn căn giữa
        center_x = W // 2
        center_y = H // 2
        heart_x = center_x - hw//2
        heart_y = center_y - hh//2
        x1 = center_x - AVT_SIZE//2
        y1 = center_y - AVT_SIZE//2
        x2 = center_x - AVT_SIZE//2
        y2 = center_y - AVT_SIZE//2

    # Paste avatar
    if avatar1:
        img.paste(avatar1, (x1, y1), avatar1)
    if avatar2:
        img.paste(avatar2, (x2, y2), avatar2)

    # Vẽ 💖
    draw.text((heart_x, heart_y), heart_text, font=font_heart, fill=(255,0,120))

    # ===== TITLE 💞 Kết quả duyên phận 💞 =====
    title_y = 50
    emoji_left = "💞"
    emoji_right = "💞"
    title_text = kieu_boi_title

    # Tính tâm giữa 2 avatar để căn title
    if avatar1 and avatar2:
        center_avatars = (x1 + x2 + AVT_SIZE) // 2
    else:
        center_avatars = W // 2

    # Tính width từng phần
    w_emoji_left = draw.textbbox((0,0), emoji_left, font=font_emoji_title)[2]
    w_title = draw.textbbox((0,0), title_text, font=font_title)[2]
    w_emoji_right = draw.textbbox((0,0), emoji_right, font=font_emoji_title)[2]
    total_w = w_emoji_left + 10 + w_title + 10 + w_emoji_right

    start_x = center_avatars - total_w // 2

    draw.text((start_x, title_y), emoji_left, font=font_emoji_title, fill=(255,0,120))
    draw.text((start_x + w_emoji_left + 10, title_y), title_text, font=font_title, fill=(255,0,120))
    draw.text((start_x + w_emoji_left + 10 + w_title + 10, title_y), emoji_right, font=font_emoji_title, fill=(255,0,120))

    # ===== NAMES =====
    name_y = center_y + AVT_SIZE//2 + 30
    if avatar1:
        w1 = draw.textbbox((0,0), name1, font=font_name)[2]
        draw.text((x1 + (AVT_SIZE - w1)//2, name_y), name1, font=font_name, fill=(0,0,0))
    if avatar2:
        w2 = draw.textbbox((0,0), name2, font=font_name)[2]
        draw.text((x2 + (AVT_SIZE - w2)//2, name_y), name2, font=font_name, fill=(0,0,0))

    # ===== % HỢP NHAU =====
    rect_w, rect_h = 250, 80
    rect_x, rect_y = (W - rect_w)//2, H - 220
    radius = 25

    def rounded_rect(draw, xy, radius, fill):
        x0, y0, x1, y1 = xy
        draw.rectangle([x0+radius, y0, x1-radius, y1], fill=fill)
        draw.rectangle([x0, y0+radius, x1, y1-radius], fill=fill)
        draw.pieslice([x0, y0, x0+radius*2, y0+radius*2], 180, 270, fill=fill)
        draw.pieslice([x1-2*radius, y0, x1, y0+2*radius], 270, 360, fill=fill)
        draw.pieslice([x0, y1-2*radius, x0+2*radius, y1], 90, 180, fill=fill)
        draw.pieslice([x1-2*radius, y1-2*radius, x1, y1], 0, 90, fill=fill)

    rounded_rect(draw, (rect_x, rect_y, rect_x+rect_w, rect_y+rect_h), radius, (255,255,255))
    percent_text = f"{percent}%"
    pw, ph = draw.textbbox((0,0), percent_text, font=font_percent)[2:]
    draw.text((rect_x + (rect_w - pw)//2, rect_y + (rect_h - ph)//2), percent_text, font=font_percent, fill=(255,0,89))

    return img

# ========================= XỬ LÝ BÓI =========================
def run_boi_with_tag(message, message_object, thread_id, thread_type, author_id, kieu_boi, title, client):
    mentions = message_object.mentions
    if not mentions or len(mentions) == 0:
        client.replyMessage(Message(text=f"Vui lòng tag ít nhất 1 người!"), message_object, thread_id, thread_type)
        return

    if len(mentions) == 1:
        uid1 = author_id
        uid2 = mentions[0].uid
    else:
        uid1 = mentions[0].uid
        uid2 = mentions[1].uid

    # Tên zalo
    name1 = client.fetchUserInfo([uid1]).changed_profiles.get(uid1).zaloName
    name2 = client.fetchUserInfo([uid2]).changed_profiles.get(uid2).zaloName

    # Random %
    percent = random.randint(10, 99)

    # Lấy avatar
    info1 = client.fetchUserInfo([uid1]).changed_profiles.get(uid1)
    info2 = client.fetchUserInfo([uid2]).changed_profiles.get(uid2)
    avatar1 = download_avatar(info1.avatar if info1 else None)
    avatar2 = download_avatar(info2.avatar if info2 else None)

    # Render ảnh
    img = render_boi_image(name1, name2, percent, avatar1, avatar2, kieu_boi_title=title)

    # Lưu
    path = f"modules/cache/boi_{uid1}_{uid2}.png"
    img.save(path)

    # Gửi ảnh
    w, h = img.size
    client.sendLocalImage(path, thread_id, thread_type, ttl=60000*2, width=w, height=h)

    # Xóa ảnh
    try:
        os.remove(path)
    except:
        pass



def handle_duyenphan_command(message, message_object, thread_id, thread_type, author_id, client):
    run_boi_with_tag(message, message_object, thread_id, thread_type, author_id, "duyenphan", "Kết quả duyên phận", client)

def handle_tuonglai_command(message, message_object, thread_id, thread_type, author_id, client):
    run_boi_with_tag(message, message_object, thread_id, thread_type, author_id, "tuonglai", "Kết quả tương lai", client)

def handle_tamdauyhop_command(message, message_object, thread_id, thread_type, author_id, client):
    run_boi_with_tag(message, message_object, thread_id, thread_type, author_id, "tamdauyhop", "Kết quả tâm đầu ý hợp", client)

def TQD():
    return {
        "duyenphan": handle_duyenphan_command,
        "tuonglai": handle_tuonglai_command,
        "tamdauyhop": handle_tamdauyhop_command
    }
