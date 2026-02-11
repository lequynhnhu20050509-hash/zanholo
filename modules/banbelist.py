import json
import math
import requests
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from io import BytesIO
from zlapi.models import Message, ZaloAPIException
from config import ADMIN

des = {
    'version': "5.3.1",
    'credits': "Latte",
    'description': "Lấy danh sách bạn bè",
    'power': "Admin",
}

# Cấu hình hiển thị
FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
PADDING = 20       
PAGE_SIZE = 30    # 50 bạn / page

# ==================== HÀM HỖ TRỢ ====================
def get_text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


# ==================== FETCH FRIENDS ====================
def fetchAllFriends(self):
    params = {
        "params": self._encode({
            "incInvalid": 0,
            "page": 1,
            "count": 20000,
            "avatar_size": 120,
            "actiontime": 0
        }),
        "zpw_ver": 641,
        "zpw_type": 30,
        "nretry": 0
    }
    try:
        response = self._get("https://profile-wpa.chat.zalo.me/api/social/friend/getfriends", params=params)
        data = response.json()
        if data.get("error_code") != 0:
            raise ZaloAPIException(f"Error #{data.get('error_code')}: {data.get('error_message') or data.get('data')}")
        encoded_data = data.get("data")
        if not encoded_data:
            return []
        results = self._decode(encoded_data)
        friends_data = results.get("data") if isinstance(results, dict) else results
        friends = []
        for f in friends_data or []:
            if isinstance(f, dict):
                friends.append(f)
            else:
                friends.append(f.__dict__)
        return friends
    except Exception as e:
        print(f"❌ [fetchAllFriends Exception] {e}")
        return []


# ==================== DRAW IMAGE ====================
def draw_friends_image_page(client, page_friends, page_idx, total_friends, total_pages):
    COLUMNS = 3
    CARD_HEIGHT = 80
    CARD_WIDTH = 400
    AVATAR_SIZE = 60
    PADDING = 15
    CIRCLE_RADIUS = 20  # số thứ tự lớn hơn

    rows = math.ceil(len(page_friends) / COLUMNS)
    W = COLUMNS * (CARD_WIDTH + PADDING) + PADDING
    H = rows * (CARD_HEIGHT + PADDING) + 150

    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Tiêu đề
    try:
        font_title = ImageFont.truetype(FONT_PATH, 36)
    except:
        font_title = ImageFont.load_default()
    title_text = f"🌟 Danh sách bạn bè (Trang {page_idx+1})"
    title_w, title_h = get_text_size(draw, title_text, font_title)
    draw.text(((W-title_w)/2, 20), title_text, fill=(0,0,0), font=font_title)

    # Font tên
    try:
        font_name = ImageFont.truetype(FONT_PATH, 15)
    except:
        font_name = ImageFont.load_default()

    y_start = 80
    for idx, f in enumerate(page_friends):
        col_idx = idx % COLUMNS
        row_idx = idx // COLUMNS
        x = PADDING + col_idx * (CARD_WIDTH + PADDING)
        y = y_start + row_idx * (CARD_HEIGHT + PADDING)

        # Card chữ nhật bo tròn
        radius = 15
        card_box = [x, y, x + CARD_WIDTH, y + CARD_HEIGHT]
        draw.rounded_rectangle(card_box, radius=radius, fill=(245,245,245), outline=(200,200,200), width=2)

        # Số thứ tự trong vòng tròn
        num_text = str(idx + 1 + page_idx * PAGE_SIZE)
        circle_x = x + CIRCLE_RADIUS + 5
        circle_y = y + CARD_HEIGHT // 2
        draw.ellipse(
            (circle_x - CIRCLE_RADIUS, circle_y - CIRCLE_RADIUS,
             circle_x + CIRCLE_RADIUS, circle_y + CIRCLE_RADIUS),
            fill=(255, 99, 71), outline=(255, 255, 255), width=2
        )
        num_w, num_h = get_text_size(draw, num_text, font_name)
        draw.text((circle_x - num_w/2, circle_y - num_h/2), num_text, fill=(255,255,255), font=font_name)

        # Avatar bên trái, cách vòng tròn
        avatar_x = circle_x + CIRCLE_RADIUS + 10
        avatar_y = y + (CARD_HEIGHT - AVATAR_SIZE)//2

        uid = f.get("uid") or f.get("user_id") or f.get("userId") or "0"
        avatar_url = None
        try:
            info = client.fetchUserInfo(uid)
            profile = info.changed_profiles.get(uid, {})
            avatar_url = profile.get("avatar", None)
        except:
            avatar_url = None

        if avatar_url:
            try:
                resp = requests.get(avatar_url)
                avatar = Image.open(BytesIO(resp.content)).convert("RGBA")
                avatar = avatar.resize((AVATAR_SIZE, AVATAR_SIZE))
                mask = Image.new("L", (AVATAR_SIZE, AVATAR_SIZE), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0,0,AVATAR_SIZE,AVATAR_SIZE), fill=255)
                img.paste(avatar, (avatar_x, avatar_y), mask)
            except Exception as e:
                print(f"⚠️ Lỗi tải avatar {uid}: {e}")

        # Tên căn giữa bên phải avatar
        name = f.get("name") or f.get("zaloName") or "Không rõ tên"
        name_x = avatar_x + AVATAR_SIZE + 15
        name_y = y + (CARD_HEIGHT - get_text_size(draw, name, font_name)[1])//2
        draw.text((name_x, name_y), name, fill=(0,0,0), font=font_name)

    # Tổng số bạn bè
    total_text = f"Tổng số bạn bè: {total_friends}"
    total_w, total_h = get_text_size(draw, total_text, font_title)
    draw.text(((W-total_w)/2, H-60), total_text, fill=(0,0,0), font=font_title)

    # Lưu ảnh
    Path("data").mkdir(exist_ok=True)
    out_path = Path(f"data/friends_list_page{page_idx+1}.png")
    img.save(out_path)
    return out_path, W, H

# ==================== HANDLE COMMAND ====================
def handle_fetch_all_friends_image(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        client.replyMessage(
            Message(text="🚫 Bạn không có quyền sử dụng lệnh này! Chỉ có admin Latte mới được sử dụng lệnh này"),
            message_object, thread_id, thread_type, ttl=20000
        )
        return

    # Lấy số trang từ lệnh: listbb <page_number>
    try:
        parts = message.strip().split()
        page_number = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
        if page_number < 1:
            page_number = 1
    except:
        page_number = 1

    try:
        if not hasattr(client, "fetchAllFriends"):
            client.fetchAllFriends = fetchAllFriends.__get__(client)

        friends_list = client.fetchAllFriends()
        total_friends = len(friends_list)
        if total_friends == 0:
            client.replyMessage(
                Message(text="⚠️ Không tìm thấy bạn bè hoặc lỗi khi lấy dữ liệu."),
                message_object, thread_id, thread_type, ttl=20000
            )
            return

        total_pages = (total_friends + PAGE_SIZE - 1) // PAGE_SIZE
        if page_number > total_pages:
            page_number = total_pages

        start_idx = (page_number - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        page_friends = friends_list[start_idx:end_idx]

        if not page_friends:
            client.replyMessage(
                Message(text=f"⚠️ Page {page_number} không có bạn bè."),
                message_object, thread_id, thread_type, ttl=20000
            )
            return

        # Vẽ và gửi ảnh page
        out_path, W, H = draw_friends_image_page(client, page_friends, page_number-1, total_friends, total_pages)
        client.sendLocalImage(str(out_path), thread_id, thread_type,ttl=60000*5, width=W, height=H)  # sendLocalImage chỉ cần path
        out_path.unlink(missing_ok=True)

    except Exception as e:
        print(f"❌ Lỗi handle_fetch_all_friends_image: {e}")
        client.replyMessage(
            Message(text=f"❌ Lỗi không xác định: {e}"),
            message_object, thread_id, thread_type, ttl=20000
        )


# ==================== MODULE ====================
def TQD():
    return {
        'listbb': handle_fetch_all_friends_image
    }


