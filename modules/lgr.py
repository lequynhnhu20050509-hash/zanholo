import os
import json
import math
import requests
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from zlapi.models import Message, ZaloAPIException
from config import ADMIN

des = {
    'version': '2.1.0',
    'credits': "Latte",
    'description': 'Lấy danh sách box Zalo (listbox)',
    'power': "Admin",
}

# ==================== CẤU HÌNH ====================
FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
AVATAR_SIZE = 90
CARD_HEIGHT = 120
CARD_WIDTH = 500
PADDING = 20
COLUMNS = 3
PAGE_SIZE = 12  # số nhóm / page

# ==================== HỖ TRỢ ====================
def is_admin(author_id):
    return author_id in ADMIN

def load_duyetbox_data():
    path = 'modules/cache/duyetboxdata.json'
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            return data if isinstance(data, list) else []
        except:
            return []

def get_text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2]-bbox[0], bbox[3]-bbox[1]

# ==================== VẼ ẢNH ====================
def draw_groups_image_page(client, page_groups, page_idx, total_groups, total_pages):
    rows = math.ceil(len(page_groups) / COLUMNS)
    W = COLUMNS * (CARD_WIDTH + PADDING) + PADDING
    H = rows * (CARD_HEIGHT + PADDING) + 150

    img = Image.new("RGB", (W, H), (255,255,255))
    draw = ImageDraw.Draw(img)

    # Tiêu đề
    try:
        font_title = ImageFont.truetype(FONT_PATH, 48)
    except:
        font_title = ImageFont.load_default()
    title_text = f"🌟 Danh sách nhóm (Trang {page_idx+1}/{total_pages})"
    tw, th = get_text_size(draw, title_text, font_title)
    draw.text(((W-tw)/2, 20), title_text, fill=(0,0,0), font=font_title)

    # Font tên nhóm
    try:
        font_name = ImageFont.truetype(FONT_PATH, 20)
    except:
        font_name = ImageFont.load_default()

    y_start = 100
    for idx, g in enumerate(page_groups):
        col_idx = idx % COLUMNS
        row_idx = idx // COLUMNS
        x = PADDING + col_idx * (CARD_WIDTH + PADDING)
        y = y_start + row_idx * (CARD_HEIGHT + PADDING)

        # Card
        draw.rounded_rectangle([x, y, x+CARD_WIDTH, y+CARD_HEIGHT], radius=20, fill=(245,245,245), outline=(200,200,200), width=2)

        # Số thứ tự
        num_text = str(idx + 1 + page_idx * PAGE_SIZE)
        circle_x = x + 30
        circle_y = y + CARD_HEIGHT//2
        draw.ellipse([circle_x-30, circle_y-30, circle_x+30, circle_y+30], fill=(255,99,71), outline=(255,255,255), width=2)
        nw, nh = get_text_size(draw, num_text, font_name)
        draw.text((circle_x-nw/2, circle_y-nh/2), num_text, fill=(255,255,255), font=font_name)

        # Avatar
        avatar_x = circle_x + 40
        avatar_y = y + (CARD_HEIGHT - AVATAR_SIZE)//2
        avatar_url = g.get("avatar_url")
        if avatar_url:
            try:
                resp = requests.get(avatar_url)
                avatar = Image.open(BytesIO(resp.content)).convert("RGBA").resize((AVATAR_SIZE, AVATAR_SIZE))
                mask = Image.new("L", (AVATAR_SIZE, AVATAR_SIZE), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0,0,AVATAR_SIZE,AVATAR_SIZE), fill=255)
                img.paste(avatar, (avatar_x, avatar_y), mask)
            except:
                pass

        # Tên nhóm
        name = g.get("name", "Không rõ tên")
        name_x = avatar_x + AVATAR_SIZE + 10
        name_y = y + (CARD_HEIGHT - get_text_size(draw, name, font_name)[1])//2
        draw.text((name_x, name_y), name, fill=(0,0,0), font=font_name)

    # Tổng số nhóm
    total_text = f"Tổng số nhóm: {total_groups}"
    tw, th = get_text_size(draw, total_text, font_title)
    draw.text(((W-tw)/2, H-60), total_text, fill=(0,0,0), font=font_title)

    Path("data").mkdir(exist_ok=True)
    out_path = Path(f"data/groups_list_page{page_idx+1}.png")
    img.save(out_path)
    return out_path, W, H

# ==================== LỆNH ====================
def handle_lgr_command(message, message_object, thread_id, thread_type, author_id, client):
    if not is_admin(author_id):
        client.replyMessage(Message(text="⚠️ Bạn không có quyền sử dụng lệnh này. Chỉ có admin Latte mới được sử dụng lệnh này"), message_object, thread_id, thread_type)
        return

    client.replyMessage(Message(text="⏳ Đang lấy danh sách nhóm Zalo của bạn, vui lòng đợi..."), message_object, thread_id, thread_type, ttl=60000)

    # Load data nhóm có key
    data = load_duyetbox_data()
    all_groups = client.fetchAllGroups().gridVerMap.keys()
    excluded_group_id = "4009464343109121790"

    if not all_groups:
        client.replyMessage(Message(text="• Không tìm thấy nhóm nào."), message_object, thread_id, thread_type, ttl=60000)
        return

    # Chuẩn bị danh sách group
    groups_list = []
    for idx, group_id in enumerate(all_groups, 1):
        if group_id == excluded_group_id:
            continue
        info = client.fetchGroupInfo(group_id).gridInfoMap.get(group_id, {})
        name = info.get('name', 'Unknown')
        avatar_url = getattr(info, "fullAvt", None) or info.get("avatar", None)
        line = {"name": name, "group_id": group_id, "avatar_url": avatar_url}
        groups_list.append(line)

    total_groups = len(groups_list)
    total_pages = math.ceil(total_groups / PAGE_SIZE)

    # Lấy số trang từ lệnh
    try:
        parts = message.strip().split()
        page_number = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
        if page_number < 1: page_number = 1
        if page_number > total_pages: page_number = total_pages
    except:
        page_number = 1

    start_idx = (page_number-1)*PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    page_groups = groups_list[start_idx:end_idx]

    if not page_groups:
        client.replyMessage(Message(text=f"⚠️ Page {page_number} không có nhóm."), message_object, thread_id, thread_type, ttl=60000)
        return

    # Vẽ và gửi ảnh
    out_path, W, H = draw_groups_image_page(client, page_groups, page_number-1, total_groups, total_pages)
    client.sendLocalImage(str(out_path), thread_id, thread_type, ttl=60000*5, width=W, height=H)
    out_path.unlink(missing_ok=True)

# ==================== MODULE ====================
def TQD():
    return {
        'listbox': handle_lgr_command
    }
