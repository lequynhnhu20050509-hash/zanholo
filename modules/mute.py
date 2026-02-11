import json
import os
import time
import threading
from datetime import datetime
from zlapi.models import Message, ThreadType
from config import PREFIX
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import tempfile
import requests
from io import BytesIO

with open('seting.json', 'r') as f:
    settings = json.load(f)

ADMIN_ID = settings['admin']
ADM_IDS = settings['adm']
mute_tmq = "data/khoamom.json"

des = {
    'version': "2.0.2",
    'credits': "Latte",
    'description': "Cấm chat thành viên gây phiền phức",
    'power': "Admin"
}

FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
EMOJI_FONT_PATH = "modules/cache/font/NotoEmoji-Bold.ttf"

def get_font(size):
    return ImageFont.truetype(FONT_PATH, size)

def get_emoji_font(size):
    return ImageFont.truetype(EMOJI_FONT_PATH, size)

def load_mute_list():
    if os.path.exists(mute_tmq):
        with open(mute_tmq, 'r') as f:
            return json.load(f)
    return {}

def save_mute_list(data):
    with open(mute_tmq, 'w') as f:
        json.dump(data, f, indent=4)

def parse_time_duration(time_str):
    if not time_str or len(time_str) < 2:
        return None
    unit = time_str[-1].lower()
    try:
        value = int(time_str[:-1])
        if unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 3600
        elif unit == 'd':
            return value * 86400
        else:
            return None
    except ValueError:
        return None

def welcome_unmuted_user(client, user_id, thread_id):
    try:
        user_info = client.fetchUserInfo(user_id)
        display_name = str(user_id)
        if user_info and hasattr(user_info, 'changed_profiles'):
            fetched_name = user_info.changed_profiles.get(user_id, {}).get('zaloName')
            if fetched_name and fetched_name != 'không xác định':
                display_name = fetched_name
            else:
                display_name = user_info.changed_profiles.get(user_id, {}).get('displayName', display_name)
        welcome_message = f"🎉 Chào mừng {display_name} đã được mở khóa chat! Bạn đã có thể trò chuyện lại bình thường trong nhóm."
        client.sendMessage(Message(text=welcome_message), thread_id=thread_id, thread_type=ThreadType.GROUP, ttl=60000)
        print(f"Sent welcome message to {display_name} ({user_id}) in thread {thread_id}.")
    except Exception as e:
        print(f"Lỗi khi gửi tin nhắn chào mừng cho user {user_id} trong nhóm {thread_id}: {e}")

def check_expired_mutes(client):
    mute_list = load_mute_list()
    current_time = time.time()
    updated = False
    expired_users_to_notify = []

    for thread_id in list(mute_list.keys()):
        if isinstance(mute_list[thread_id], list):
            old_list = mute_list[thread_id]
            mute_list[thread_id] = {}
            for uid in old_list:
                mute_list[thread_id][uid] = {"expires_at": None}
            updated = True 

        for user_id in list(mute_list[thread_id].keys()):
            user_mute_info = mute_list[thread_id][user_id]
            expires_at = user_mute_info.get("expires_at")
            if expires_at is not None and expires_at <= current_time:
                expired_users_to_notify.append((user_id, thread_id))
                del mute_list[thread_id][user_id]
                updated = True
        
        if not mute_list[thread_id]:
            del mute_list[thread_id]
            updated = True

    if updated:
        save_mute_list(mute_list)
        
    for user_id, thread_id in expired_users_to_notify:
        welcome_unmuted_user(client, user_id, thread_id)

def start_expiry_checker(client):
    def check_loop_internal():
        while True:
            try:
                check_expired_mutes(client)
            except Exception as e:
                print(f"Lỗi khi kiểm tra mute hết hạn (background task): {e}")
            time.sleep(1)

    t = threading.Thread(target=check_loop_internal, daemon=True)
    t.start()

def format_time_remaining(expires_at):
    if not expires_at:
        return "vĩnh viễn"
    remaining = expires_at - time.time()
    if remaining <= 0:
        return "đã hết hạn"
    days, remainder = divmod(remaining, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if days > 0:
        parts.append(f"{int(days)} ngày")
    if hours > 0:
        parts.append(f"{int(hours)} giờ")
    if minutes > 0:
        parts.append(f"{int(minutes)} phút")
    if seconds > 0 and not parts:
        parts.append(f"{int(seconds)} giây")
    return " ".join(parts)

def smart_resize(img, target_w, target_h):
    w, h = img.size
    scale = min(target_w / w, target_h / h, 1.0)
    if scale < 1:
        return img.resize((int(w*scale), int(h*scale)), resample=Image.LANCZOS)
    return img

def auto_jpeg_save(img, quality=94):
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        img.convert("RGB").save(
            tf,
            "JPEG",
            quality=quality,
            dpi=(180,180),
            optimize=True,
            progressive=True,
            subsampling=0
        )
        return tf.name

def get_user_avatar_and_name(client, user_id, size=104):
    u = client.fetchUserInfo(user_id) or {}
    ud = u.get('changed_profiles', {}).get(user_id, {})
    av_url = ud.get('avatar')
    display_name = ud.get('zaloName') or ud.get('displayName') or ud.get('name') or u.get('displayName') or u.get('name') or str(user_id)
    if not display_name:
        display_name = str(user_id)
    try:
        if av_url:
            resp = requests.get(av_url, timeout=6)
            img = Image.open(BytesIO(resp.content)).convert("RGBA").resize((size, size))
        else:
            img = Image.new("RGBA", (size, size), (200, 200, 200, 255))
    except Exception:
        img = Image.new("RGBA", (size, size), (200, 200, 200, 255))
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    border = Image.new("RGBA", (size+16, size+16), (0,0,0,0))
    border_draw = ImageDraw.Draw(border)
    border_draw.ellipse((0,0,size+16,size+16), fill=(0,0,0,40))
    border_draw.ellipse((4,4,size+12,size+12), fill=(255,255,255,255))
    border.paste(img, (8,8), mask=img)
    return border, display_name

def wrap_text_auto(text, font, max_width):
    words = text.split()
    lines = []
    cur_line = ""
    for word in words:
        test_line = cur_line + (" " if cur_line else "") + word
        if font.getlength(test_line) <= max_width:
            cur_line = test_line
        else:
            if cur_line:
                lines.append(cur_line)
            cur_line = word
    if cur_line:
        lines.append(cur_line)
    return "\n".join(lines)

def gen_mute_menu_image(client, notify_text=None):
    WIDTH, HEIGHT = 950, 520
    PAD = 32
    CARD_RADIUS = 38
    BLACK = (28,28,28)
    WHITE = (255,255,255)
    GRADIENT_TOP = (245,245,245,255)
    GRADIENT_BOTTOM = (30,30,30,255)
    bg = Image.new("RGBA", (WIDTH, HEIGHT), WHITE)
    grad = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
    draw_grad = ImageDraw.Draw(grad)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(GRADIENT_TOP[0]*(1-ratio)+GRADIENT_BOTTOM[0]*ratio)
        g = int(GRADIENT_TOP[1]*(1-ratio)+GRADIENT_BOTTOM[1]*ratio)
        b = int(GRADIENT_TOP[2]*(1-ratio)+GRADIENT_BOTTOM[2]*ratio)
        a = int(GRADIENT_TOP[3]*(1-ratio)+GRADIENT_BOTTOM[3]*ratio)
        draw_grad.line([(0, y), (WIDTH, y)], fill=(r,g,b,a), width=1)
    bg = Image.alpha_composite(bg, grad)
    draw = ImageDraw.Draw(bg)
    draw.rounded_rectangle([PAD,PAD,WIDTH-PAD,HEIGHT-PAD], radius=CARD_RADIUS, fill=(255,255,255,241), outline=(140,140,140), width=2)
    icon_font = get_font(60)
    draw.text((PAD+32, PAD+24), "🔇", font=icon_font, fill=(120,120,120))
    title_font = get_font(44)
    draw.text((PAD+120, PAD+36), "QUẢN LÝ MUTE", font=title_font, fill=BLACK)
    info_font = get_font(25)
    if notify_text:
        notif_font = get_font(27)
        notif_x = PAD+120
        notif_y = PAD+36 + title_font.size + 16
        draw.text((notif_x, notif_y), notify_text, font=notif_font, fill=(210,30,30))
    body_x = PAD+32
    body_y = PAD+110
    lines = [
        f"Cú pháp: {PREFIX}mute @user [thời gian] hoặc trả lời tin nhắn",
        f"Thời gian: 10m, 1h, 1d → Không ghi = vĩnh viễn",
        f"Xem danh sách: {PREFIX}mute list",
        "Chỉ Admin hoặc ADM dùng được",
        "─────────────────────────────",
        f"{PREFIX}mute @user1 @user2 : cấm chat vĩnh viễn",
        f"{PREFIX}mute @user 10m : cấm 10 phút",
        f"{PREFIX}mute 1h @user : cấm 1 giờ",
        f"{PREFIX}unmute @user : mở khóa",
        f"{PREFIX}mute list : xem danh sách bị mute",
        "─────────────────────────────",
    ]
    cur_y = body_y
    for l in lines:
        wrap_lines = wrap_text_auto(l, info_font, WIDTH-PAD*2-30).split('\n')
        for w in wrap_lines:
            draw.text((body_x, cur_y), w, font=info_font, fill=BLACK)
            cur_y += info_font.size + 2
        cur_y += 1
    img = smart_resize(bg, WIDTH, HEIGHT)
    temp_path = auto_jpeg_save(img, quality=94)
    return temp_path

def gen_mute_result_image(client, user_id, admin_name, is_unmute, expires_at=None):
    WIDTH, HEIGHT = 630, 220
    PAD = 22
    AVT_SIZE = 104
    CARD_RADIUS = 32
    BLACK = (28,28,28)
    WHITE = (255,255,255)
    GRAD_TOP = (245,245,245,255)
    GRAD_BOT = (30,30,30,255)
    bg = Image.new("RGBA", (WIDTH, HEIGHT), WHITE)
    grad = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
    draw_grad = ImageDraw.Draw(grad)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(GRAD_TOP[0]*(1-ratio)+GRAD_BOT[0]*ratio)
        g = int(GRAD_TOP[1]*(1-ratio)+GRAD_BOT[1]*ratio)
        b = int(GRAD_TOP[2]*(1-ratio)+GRAD_BOT[2]*ratio)
        a = int(GRAD_TOP[3]*(1-ratio)+GRAD_BOT[3]*ratio)
        draw_grad.line([(0, y), (WIDTH, y)], fill=(r,g,b,a), width=1)
    bg = Image.alpha_composite(bg, grad)
    draw = ImageDraw.Draw(bg)
    draw.rounded_rectangle([PAD,PAD,WIDTH-PAD,HEIGHT-PAD], radius=CARD_RADIUS, fill=(255,255,255,241), outline=(140,140,140), width=2)
    avatar_img, display_name = get_user_avatar_and_name(client, user_id, AVT_SIZE-4)
    avatar_y = PAD+18+20
    avatar_x = PAD+8+10
    bg.alpha_composite(avatar_img, (avatar_x, avatar_y))
    main_font = get_font(30)
    sub_font = get_font(22)
    y_text = PAD+20+20
    x_text = PAD+AVT_SIZE+24+10
    if is_unmute:
        draw.text((x_text, y_text), f"Đã UNMUTE", font=main_font, fill=(0,120,0))
    else:
        draw.text((x_text, y_text), f"Đã MUTE", font=main_font, fill=(210,30,30))
    y_text += main_font.size + 6
    name_line = wrap_text_auto(f"Thành viên: {display_name}", sub_font, WIDTH-x_text-20).split('\n')
    for line in name_line:
        draw.text((x_text, y_text), line, font=sub_font, fill=BLACK)
        y_text += sub_font.size + 2
    if not is_unmute:
        draw.text((x_text, y_text), f"Thời hạn: {format_time_remaining(expires_at)}", font=sub_font, fill=(60,60,60))
        y_text += sub_font.size + 2
    draw.text((x_text, y_text), f"Admin: {admin_name}", font=sub_font, fill=(90,90,90))
    img = smart_resize(bg, WIDTH, HEIGHT)
    temp_path = auto_jpeg_save(img, quality=94)
    return temp_path

def gen_mute_list_image(client, thread_id):
    mute_list = load_mute_list()
    muted_users = mute_list.get(thread_id, {})
    
    if isinstance(muted_users, list):
        old_list = muted_users
        muted_users = {}
        for uid in old_list:
            muted_users[uid] = {"expires_at": None}

    user_data = []
    for idx, (user_id, mute_info) in enumerate(muted_users.items(), 1):
        try:
            user_info = client.fetchUserInfo(user_id)
            author_info = user_info.changed_profiles.get(user_id, {}) if user_info and user_info.changed_profiles else {}
            name = author_info.get('zaloName', 'Không xác định')
            avatar = author_info.get('avatar', None)
        except Exception:
            name = "Không xác định"
            avatar = None
        expires_at = mute_info.get("expires_at")
        user_data.append((f"🔇 MUTE {idx}", name, avatar, user_id, format_time_remaining(expires_at)))

    row_h = 170
    box_w = 960
    margin_top = 90
    margin_left = 80
    extra = 150 if len(user_data) else 230
    image_width = 1150
    image_height = margin_top + row_h * max(1, len(user_data)) + extra
    bg = Image.new("RGBA", (image_width, image_height), (38, 30, 75, 255))
    draw = ImageDraw.Draw(bg)
    font = get_font(28)
    emoji_font = get_emoji_font(38)
    id_font = get_font(22)
    
    draw_center_text(draw, "🌈🔇 DANH SÁCH NGƯỜI BỊ MUTE 🔇🌈", 32, get_font(38), emoji_font, image_width, (255,225,255), True, x_offset=0)
    
    if not user_data:
        draw_center_text(draw, "Chưa có ai bị mute trong nhóm này!", 200, font, emoji_font, image_width, (255,180,180), True)
    else:
        for i, (role, name, avatar_url, user_id, time_remaining) in enumerate(user_data):
            y = margin_top + i * row_h
            av = get_user_avatar_and_name(client, user_id, 80)[0]
            bg.alpha_composite(av, (margin_left, y + (row_h - 80)//2))
            role_x = margin_left + 100
            role_y = y + 14
            draw.text((role_x, role_y), role[0], font=emoji_font, fill=(240,245,180))
            draw.text((role_x + 48, role_y + 5), role[1:], font=font, fill=(240,245,180))
            name_show = name if len(name) <= 18 else name[:17] + "…"
            name_y = role_y + 43
            draw.text((role_x, name_y), f"Tên: {name_show}", font=font, fill=(200,255,255))
            id_y = name_y + 34
            draw.text((role_x, id_y), f"ID: {user_id}", font=id_font, fill=(180,220,255))
            draw.text((role_x, id_y + 24), f"Thời hạn: {time_remaining}", font=id_font, fill=(180,220,255))
            divider_y = y + row_h - 2
            draw.line((margin_left+2, divider_y, margin_left+box_w-2, divider_y), fill=(159,108,255), width=2)
    
    draw_center_text(draw, "🛡️ Dùng lệnh để quản lý mute: mute/unmute 🛡️", image_height-52, get_font(27), emoji_font, image_width, (255,210,255), True, x_offset=0)
    temp_path = auto_jpeg_save(bg, quality=94)
    return temp_path, image_width, image_height

def draw_center_text(draw, text, y, font, emoji_font, img_w, color, shadow=False, x_offset=0):
    import emoji as emoji_mod
    lines = wrap_text_auto(text, font, img_w - 60).split('\n')
    line_height = font.getbbox("Ay")[3] - font.getbbox("Ay")[1]
    for line in lines:
        width = 0
        for c in line:
            if emoji_mod.emoji_count(c):
                width += emoji_font.getlength(c)
            else:
                width += font.getlength(c)
        x = (img_w - width) // 2 + x_offset
        cur_x = x
        for c in line:
            if emoji_mod.emoji_count(c):
                if shadow:
                    draw.text((cur_x+2, y+2), c, font=emoji_font, fill=(0,0,0,180))
                draw.text((cur_x, y), c, font=emoji_font, fill=color)
                cur_x += emoji_font.getlength(c)
            else:
                if shadow:
                    draw.text((cur_x+2, y+2), c, font=font, fill=(0,0,0,180))
                draw.text((cur_x, y), c, font=font, fill=color)
                cur_x += font.getlength(c)
        y += line_height + 6

def send_text_message(client, message, message_object, thread_id, thread_type, ttl=12000):
    client.replyMessage(Message(text=message), message_object, thread_id, thread_type, ttl=ttl)

# === XỬ LÝ LỆNH MUTE MỚI ===
def handle_mute_command(message, message_object, thread_id, thread_type, author_id, client):
    if str(author_id) not in [ADMIN_ID] + ADM_IDS:
        send_text_message(client, "Bạn không có quyền sử dụng lệnh này!", message_object, thread_id, thread_type)
        client.sendReaction(message_object, "❌", thread_id, thread_type)
        return

    # Lệnh help
    if "help" in message.lower() or "menu" in message.lower():
        temp_path = gen_mute_menu_image(client)
        with Image.open(temp_path) as im:
            w, h = im.size
        client.sendLocalImage(temp_path, thread_id=thread_id, thread_type=thread_type, width=w, height=h, ttl=120000)
        os.remove(temp_path)
        client.sendReaction(message_object, "ℹ️", thread_id, thread_type)
        return

    # Lệnh list
    if "list" in message.lower():
        temp_path, width, height = gen_mute_list_image(client, thread_id)
        client.sendLocalImage(temp_path, thread_id=thread_id, thread_type=thread_type, width=width, height=height, ttl=120000)
        os.remove(temp_path)
        client.sendReaction(message_object, "✅", thread_id, thread_type)
        return

    # Lấy danh sách user từ mention hoặc quote
    user_ids = []
    if message_object.mentions:
        for mention in message_object.mentions:
            user_ids.append(str(mention.uid))
    elif message_object.quote:
        user_ids.append(str(message_object.quote.ownerId))

    if not user_ids:
        send_text_message(client, "Vui lòng tag hoặc trả lời tin nhắn người cần mute!", message_object, thread_id, thread_type)
        client.sendReaction(message_object, "❌", thread_id, thread_type)
        return

    # Lấy thời gian từ nội dung tin nhắn
    duration_secs = None
    raw_text = message.strip()
    words = raw_text.split()
    time_str = None
    for word in words:
        if parse_time_duration(word) is not None:
            time_str = word
            duration_secs = parse_time_duration(word)
            break

    if time_str:
        raw_text = raw_text.replace(time_str, "").strip()

    # Kiểm tra ADM không mute ADMIN
    if str(author_id) in ADM_IDS and ADMIN_ID in user_ids:
        send_text_message(client, "ADM không thể mute Quản trị viên Bot!", message_object, thread_id, thread_type)
        client.sendReaction(message_object, "❌", thread_id, thread_type)
        return

    # Load danh sách mute
    mute_list = load_mute_list()
    if thread_id not in mute_list:
        mute_list[thread_id] = {}
    elif isinstance(mute_list[thread_id], list):
        old_list = mute_list[thread_id]
        mute_list[thread_id] = {}
        for uid in old_list:
            mute_list[thread_id][uid] = {"expires_at": None}

    # Lấy tên admin
    admin_name = "Quản trị viên"
    try:
        admin_info = client.fetchUserInfo(author_id)
        if admin_info and admin_info.changed_profiles:
            admin_name = admin_info.changed_profiles.get(author_id, {}).get('zaloName', admin_name)
    except:
        pass

    expires_at = time.time() + duration_secs if duration_secs else None

    # Xử lý từng user
    for user_id in user_ids:
        if user_id in mute_list[thread_id]:
            send_text_message(client, f"Thành viên <@{user_id}> đã bị mute trước đó!", message_object, thread_id, thread_type)
            continue

        mute_list[thread_id][user_id] = {"expires_at": expires_at}
        save_mute_list(mute_list)

        temp_path = gen_mute_result_image(client, user_id, admin_name, is_unmute=False, expires_at=expires_at)
        with Image.open(temp_path) as im:
            w, h = im.size
        client.sendLocalImage(temp_path, thread_id=thread_id, thread_type=thread_type, width=w, height=h, ttl=22000)
        os.remove(temp_path)

    client.sendReaction(message_object, "✅", thread_id, thread_type)

def handle_unmute_command(message, message_object, thread_id, thread_type, author_id, client):
    if str(author_id) not in [ADMIN_ID] + ADM_IDS:
        send_text_message(client, "Bạn không có quyền sử dụng lệnh này!", message_object, thread_id, thread_type)
        client.sendReaction(message_object, "❌", thread_id, thread_type)
        return

    user_ids = []
    if message_object.mentions:
        for mention in message_object.mentions:
            user_ids.append(str(mention.uid))
    elif message_object.quote:
        user_ids.append(str(message_object.quote.ownerId))

    if not user_ids:
        send_text_message(client, "Vui lòng tag hoặc trả lời người cần unmute!", message_object, thread_id, thread_type)
        client.sendReaction(message_object, "❌", thread_id, thread_type)
        return

    mute_list = load_mute_list()
    if thread_id not in mute_list:
        mute_list[thread_id] = {}

    admin_name = "Quản trị viên"
    try:
        admin_info = client.fetchUserInfo(author_id)
        if admin_info and admin_info.changed_profiles:
            admin_name = admin_info.changed_profiles.get(author_id, {}).get('zaloName', admin_name)
    except:
        pass

    for user_id in user_ids:
        if user_id not in mute_list[thread_id]:
            send_text_message(client, f"Thành viên <@{user_id}> chưa bị mute!", message_object, thread_id, thread_type)
            continue

        del mute_list[thread_id][user_id]
        if not mute_list[thread_id]:
            del mute_list[thread_id]
        save_mute_list(mute_list)

        temp_path = gen_mute_result_image(client, user_id, admin_name, is_unmute=True)
        with Image.open(temp_path) as im:
            w, h = im.size
        client.sendLocalImage(temp_path, thread_id=thread_id, thread_type=thread_type, width=w, height=h, ttl=120000)
        os.remove(temp_path)

    client.sendReaction(message_object, "✅", thread_id, thread_type)

def TQD():
    return {
        'mute': handle_mute_command,
        'unmute': handle_unmute_command
    }