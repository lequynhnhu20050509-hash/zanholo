import json
from zlapi.models import Message
from config import PREFIX
from PIL import Image, ImageDraw, ImageFont
import tempfile
import requests
from io import BytesIO
import os
from datetime import datetime

with open('seting.json', 'r') as f:
    settings = json.load(f)

ADMIN_ID = settings.get('admin')
ADM_IDS = settings.get('adm', [])
AUTHORIZED_IDS = [ADMIN_ID] + ADM_IDS

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Block thành viên trong nhóm",
    'power': "Quản trị viên Bot"
}

FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"

def get_font(size):
    return ImageFont.truetype(FONT_PATH, size)

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

def gen_ban_menu_image():
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
    draw.text((PAD+32, PAD+24), "🚫", font=icon_font, fill=(220,70,70))
    title_font = get_font(44)
    draw.text((PAD+120, PAD+36), "BLOCK THÀNH VIÊN", font=title_font, fill=BLACK)
    info_font = get_font(25)
    body_x = PAD+32
    body_y = PAD+110
    lines = [
        f"Cú pháp: {PREFIX}ban @user1 @user2 ... hoặc trả lời tin nhắn",
        "Chỉ Đại ca (Quản trị viên Bot), Admin Latte mới dùng được 😎",
        "─────────────────────────────",
        f"{PREFIX}ban @user1 @user2 ...: Block thành viên khỏi nhóm",
        "─────────────────────────────",
        f"Phiên bản: {des['version']}   •   Tác giả: {des['credits']}",
        f"Quyền: {des['power']}  •  {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "─────────────────────────────",
        "⚠️ Nhập đúng @user hoặc trả lời tin nhắn kẻo lộn nha Đại ca!"
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

def gen_ban_result_image(client, user_id, admin_name):
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
    draw.text((x_text, y_text), f"Đã BLOCK", font=main_font, fill=(210,30,30))
    y_text += main_font.size + 6
    name_line = wrap_text_auto(f"Thành viên: {display_name}", sub_font, WIDTH-x_text-20).split('\n')
    for line in name_line:
        draw.text((x_text, y_text), line, font=sub_font, fill=BLACK)
        y_text += sub_font.size + 2
    draw.text((x_text, y_text), f"Admin: {admin_name}", font=sub_font, fill=(90,90,90))
    img = smart_resize(bg, WIDTH, HEIGHT)
    temp_path = auto_jpeg_save(img, quality=94)
    return temp_path

def send_text_message(client, message, message_object, thread_id, thread_type, ttl=12000):
    client.replyMessage(Message(text=message), message_object, thread_id, thread_type, ttl=ttl)

def handle_ban_command(message, message_object, thread_id, thread_type, author_id, client):
    if str(author_id) not in AUTHORIZED_IDS:
        send_text_message(client, "• Bạn không có quyền sử dụng lệnh này.", message_object, thread_id, thread_type)
        return

    command_parts = message.strip().split()
    if len(command_parts) < 2 or command_parts[1].lower() == "help":
        temp_path = gen_ban_menu_image()
        with Image.open(temp_path) as im:
            w, h = im.size
        client.sendLocalImage(temp_path, thread_id=thread_id, thread_type=thread_type, width=w, height=h, ttl=120000)
        os.remove(temp_path)
        client.sendReaction(message_object, "ℹ️", thread_id, thread_type)
        return

    user_ids_to_ban = []
    if message_object.mentions:
        user_ids_to_ban.extend([str(mention.uid) for mention in message_object.mentions])
    elif message_object.quote:
        user_ids_to_ban.append(str(message_object.quote.ownerId))

    if not user_ids_to_ban:
        send_text_message(client, "• Tag ít nhất một người cần Block hoặc trả lời tin nhắn.", message_object, thread_id, thread_type)
        client.sendReaction(message_object, "❌", thread_id, thread_type)
        return

    group_data = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
    admins = group_data.adminIds
    owners = group_data.creatorId

    if client.uid not in admins and client.uid != owners:
        send_text_message(client, "• Latte không có quyền quản trị.", message_object, thread_id, thread_type)
        client.sendReaction(message_object, "❌", thread_id, thread_type)
        return

    admin_name = "Quản trị viên"
    try:
        admin_info = client.fetchUserInfo(author_id)
        admin_name = admin_info.get(author_id, {}).get('name', "Quản trị viên")
    except:
        pass

    success = []
    fail = []

    for user_id in user_ids_to_ban:
        if user_id == ADMIN_ID:
            fail.append(f"Không thể block admin chính.")
            continue
        if user_id in ADM_IDS and str(author_id) != ADMIN_ID:
            fail.append(f"Bạn không có quyền block ADM.")
            continue
        if user_id == owners:
            fail.append(f"Không thể block chủ nhóm.")
            continue
        if user_id in admins and str(author_id) != owners:
            fail.append(f"Bạn không có quyền block admin nhóm.")
            continue

        try:
            client.blockUsersInGroup(user_id, thread_id)
            success.append(user_id)
        except Exception as e:
            fail.append(f"Lỗi khi block {user_id}: {str(e)}")

    for user_id in success:
        temp_path = gen_ban_result_image(client, user_id, admin_name)
        with Image.open(temp_path) as im:
            w, h = im.size
        client.sendLocalImage(temp_path, thread_id=thread_id, thread_type=thread_type, width=w, height=h, ttl=120000)
        os.remove(temp_path)

    if fail:
        send_text_message(client, "\n".join(fail), message_object, thread_id, thread_type)
        client.sendReaction(message_object, "❌", thread_id, thread_type)
    elif not success:
        send_text_message(client, "• Không có thành viên nào được block.", message_object, thread_id, thread_type)
        client.sendReaction(message_object, "❌", thread_id, thread_type)
    else:
        client.sendReaction(message_object, "✅", thread_id, thread_type)

def TQD():
    return {
        'ban': handle_ban_command
    }