import os
import json
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from zlapi.models import Message
from config import ADMIN


CACHE_DIR = "modules/cache/topchat_temp"
FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
EMOJI_FONT_PATH = "modules/cache/font/NotoEmoji-Bold.ttf"
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
TOPCHAT_FILE = DATA_DIR / "topchat.json"


GROUP_DATA_DIR = Path("topchat")
GROUP_DATA_DIR.mkdir(exist_ok=True)

os.makedirs(CACHE_DIR, exist_ok=True)


def get_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except:
        return ImageFont.load_default()

def get_emoji_font(size):
    try:
        return ImageFont.truetype(EMOJI_FONT_PATH, size)
    except:
        return ImageFont.load_default()


def is_emoji(ch):
    return (
        '\U0001F600' <= ch <= '\U0001F64F' or
        '\U0001F300' <= ch <= '\U0001F5FF' or
        '\U0001F680' <= ch <= '\U0001F6FF' or
        '\U0001F1E0' <= ch <= '\U0001F1FF' or
        '\U00002700' <= ch <= '\U000027BF' or
        '\U0001F900' <= ch <= '\U0001F9FF' or
        '\U00002000' <= ch <= '\U00002064'
    )

def draw_text_mixed(draw, x, y, text, font_text, font_emoji, fill):
    cursor = x
    for ch in text:
        if is_emoji(ch):
            bbox = font_emoji.getbbox(ch)
            w = bbox[2] - bbox[0]
            draw.text((cursor, y), ch, font=font_emoji, fill=fill)
            cursor += w
        else:
            bbox = font_text.getbbox(ch)
            w = bbox[2] - bbox[0]
            draw.text((cursor, y), ch, font=font_text, fill=fill)
            cursor += w

# ---------------- Tên người dùng ----------------
def get_user_name(client, user_id, cache_data=None):
    try:
        info = client.fetchUserInfo(user_id)
        if info and hasattr(info, 'changed_profiles') and user_id in info.changed_profiles:
            profile = info.changed_profiles[user_id]
            name = getattr(profile, 'zaloName', None)
            if name:
                return name
    except: pass
    if cache_data:
        for u in cache_data:
            if u.get("UserID") == user_id and u.get("UserName"):
                return u["UserName"]
    return "Người dùng ẩn danh"

# ---------------- Lấy tên nhóm ----------------
def get_group_name(client, thread_id):
    try:
        group_info = client.fetchGroupInfo(thread_id)
        group_data = group_info.gridInfoMap.get(thread_id)
        return group_data.name if group_data and getattr(group_data, 'name', None) else str(thread_id)
    except Exception as e:
        print("Lỗi khi lấy tên nhóm:", e)
        return str(thread_id)

des = {
  'version': "2.1.3",
  'credits': "Latte",
  'description': "Xem số tin nhắn nhóm theo ngày hoặc tổng hợp",
  'power': "Thành viên / Quản trị viên"
}


def get_group_path(thread_id):
    return GROUP_DATA_DIR / f"{thread_id}.json"

def read_group_data(thread_id):
    path = get_group_path(thread_id)
    if not path.exists() or path.stat().st_size == 0:
        return {"daily": {}, "total": {"users": []}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"daily": {}, "total": {"users": []}}

def save_group_data(thread_id, data):
    path = get_group_path(thread_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_topchat():
    try:
        if not TOPCHAT_FILE.exists() or TOPCHAT_FILE.stat().st_size == 0:
            return []
        with open(TOPCHAT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception as e:
        print(f"Lỗi đọc topchat.json ({e}), reset file.")
        TOPCHAT_FILE.write_text("[]", encoding="utf-8")
        return []

def save_topchat(enabled_groups):
    try:
        with open(TOPCHAT_FILE, "w", encoding="utf-8") as f:
            json.dump(enabled_groups, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Lỗi ghi topchat.json ({e}), reset file.")
        TOPCHAT_FILE.write_text("[]", encoding="utf-8")

def is_topchat_enabled(thread_id):
    enabled_groups = read_topchat()
    return str(thread_id) in enabled_groups

def set_topchat_status(thread_id, enabled: bool):
    enabled_groups = read_topchat()
    thread_id_str = str(thread_id)
    if enabled:
        if thread_id_str not in enabled_groups:
            enabled_groups.append(thread_id_str)
    else:
        if thread_id_str in enabled_groups:
            enabled_groups.remove(thread_id_str)
    save_topchat(enabled_groups)

# ===== Cập nhật tin nhắn =====
def update_user_rank(client, thread_id, author_id):
    # Nếu nhóm không bật -> bỏ qua
    if not is_topchat_enabled(thread_id):
        return
    
    # Nếu file nhóm chưa tồn tại -> tạo file mới
    path = get_group_path(thread_id)
    if not path.exists() or path.stat().st_size == 0:
        save_group_data(thread_id, {"daily": {}, "total": {"users": []}})

    # Đọc dữ liệu nhóm
    data = read_group_data(thread_id)

    today = datetime.now().strftime("%Y-%m-%d")
    daily_data = data["daily"].setdefault(today, {"users": []})
    total_users = data["total"]["users"]

    user_name = get_user_name(client, author_id)
    now = datetime.now().isoformat()

    # --- DAILY ---
    for user in daily_data["users"]:
        if user["UserID"] == author_id:
            user["Rank"] += 1
            user["UserName"] = user_name
            user["LastActive"] = now
            break
    else:
        daily_data["users"].append({
            "UserID": author_id,
            "UserName": user_name,
            "Rank": 1,
            "LastActive": now
        })

    # --- TOTAL ---
    for user in total_users:
        if user["UserID"] == author_id:
            user["Rank"] += 1
            user["UserName"] = user_name
            user["LastActive"] = now
            break
    else:
        total_users.append({
            "UserID": author_id,
            "UserName": user_name,
            "Rank": 1,
            "LastActive": now
        })

    save_group_data(thread_id, data)
             

# ===== PIL Avatar =====
def fetch_avatar(url, size):
    try:
        response = requests.get(url, timeout=3)
        img = Image.open(BytesIO(response.content)).convert("RGBA").resize((size, size))
    except:
        img = Image.new("RGBA", (size, size), (180,180,180,255))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0,0,size,size), fill=255)
    img.putalpha(mask)
    return img

# ===== PIL TopChat =====
def draw_topchat_image(users_list, client, title, group_name="", page=1):
    WIDTH, HEIGHT = 1080, 1440
    PADDING, CARD_HEIGHT, CARD_SPACING, AVATAR_SIZE = 50, 100, 15, 80
    TOP_COUNT, USERS_PER_PAGE = 3, 10

    font_header, font_label, font_small = get_font(46), get_font(32), get_font(24)
    if not users_list:
        return None, None, None

    sorted_users = sorted(users_list, key=lambda x: x["Rank"], reverse=True)
    start_idx, end_idx = (page-1)*USERS_PER_PAGE, page*USERS_PER_PAGE
    page_users = sorted_users[start_idx:end_idx]

    bg = Image.new("RGBA", (WIDTH, HEIGHT), (32, 40, 60, 255))
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (255,255,255,0))
    draw = ImageDraw.Draw(overlay)

    # ===== Tiêu đề =====
    bbox_title = draw.textbbox((0,0), title, font=font_header)
    title_x = (WIDTH - (bbox_title[2]-bbox_title[0]))/2
    title_y = 40
    draw.text((title_x, title_y), title, font=font_header, fill=(255,235,80))

    # ===== VẼ TÊN NHÓM (BE PRO + EMOJI) =====
    if group_name:
        font_text = font_label
        font_emoji = get_emoji_font(font_label.size)

        # Tính chiều rộng thực tế
        total_width = 0
        for ch in group_name:
            if is_emoji(ch):
                bbox = font_emoji.getbbox(ch)
            else:
                bbox = font_text.getbbox(ch)
            total_width += (bbox[2] - bbox[0])

        group_x = (WIDTH - total_width) / 2
        group_y = title_y + (bbox_title[3] - bbox_title[1]) + 25

        draw_text_mixed(draw, group_x, group_y, group_name, font_text, font_emoji, (180,180,255))

    # ===== Vẽ danh sách =====
    for idx, user in enumerate(page_users, start=start_idx+1):
        current_y = 120 + idx* (CARD_HEIGHT + CARD_SPACING) - start_idx*(CARD_HEIGHT + CARD_SPACING)
        draw.rounded_rectangle((PADDING,current_y, WIDTH-PADDING, current_y+CARD_HEIGHT), radius=20, fill=(36,60,120,230))
        avatar_url = None
        try:
            info = client.fetchUserInfo(user["UserID"])
            profile = info.changed_profiles.get(user["UserID"], {})
            avatar_url = profile.get("avatar", None)
        except: pass
        av = fetch_avatar(avatar_url, AVATAR_SIZE)
        overlay.alpha_composite(av, (PADDING+10, current_y + (CARD_HEIGHT-AVATAR_SIZE)//2))

        rank_color = (255,215,0) if idx-start_idx <= TOP_COUNT else (255,255,255)
        draw.text((PADDING+AVATAR_SIZE+30, current_y+30), str(idx), font=font_label, fill=rank_color)
        name = user.get("UserName","Người dùng ẩn danh")
        draw.text((PADDING+AVATAR_SIZE+90, current_y+30), name, font=font_label, fill=(255,255,255))
        if idx-start_idx <= TOP_COUNT:
            draw.text((PADDING+AVATAR_SIZE+90+font_label.getlength(name)+10, current_y+10), "👑", font=font_label, fill=(255,215,0))

        rank_num = user.get('Rank',0)
        cx, cy = WIDTH-PADDING-250, current_y + CARD_HEIGHT//2
        txt_num = str(rank_num)
        txt_w = font_label.getlength(txt_num)
        txt_h = font_label.getbbox("Ay")[3] - font_label.getbbox("Ay")[1]
        draw.text((cx - txt_w/2, cy - txt_h/2), txt_num, font=font_label, fill=(80,220,120))
        draw.text((cx - txt_w/2 + txt_w + 10, cy - txt_h/2), "tin nhắn", font=font_label, fill=(255,255,255))

    # ===== Credit =====
    credit_text = "Danh sách top nhắn tin"
    bbox2 = draw.textbbox((0,0), credit_text, font=font_small)
    draw.text(((WIDTH-(bbox2[2]-bbox2[0]))/2, HEIGHT-40), credit_text, font=font_small, fill=(180,180,180))

    final = Image.alpha_composite(bg, overlay).convert("RGB")
    path_temp = os.path.join(CACHE_DIR, f"topchat_{datetime.now().timestamp()}.jpg")
    final.save(path_temp, "JPEG", quality=95, optimize=True)
    return path_temp, WIDTH, HEIGHT

# ===== Hiển thị TopChat =====
def show_topchat(thread_id, thread_type, author_id, client, mode="today"):
    if not is_topchat_enabled(thread_id):
        client.sendMessage(Message(text="⚠️ Tính năng TopChat chưa bật cho nhóm này.\n\nDùng: -topchat on"), thread_id, thread_type, ttl=20000)
        return

    group_data = read_group_data(thread_id)

    group_name = get_group_name(client, thread_id)
    if mode=="today":
        today = datetime.now().strftime("%Y-%m-%d")
        users_list = group_data.get("daily", {}).get(today, {}).get("users", [])
        title = "🏆 TƯƠNG TÁC HÔM NAY"
    else:
        users_list = group_data.get("total", {}).get("users", [])
        title = "🏆 TƯƠNG TÁC TỪ TRƯỚC ĐẾN NAY"

    if not users_list:
        user_name = get_user_name(client, author_id)
        msg = f"📭 Chưa có dữ liệu {('hôm nay' if mode=='today' else 'tổng hợp')}.\n\n[Ask by: {user_name}]"
        client.sendMessage(Message(text=msg), thread_id, thread_type, ttl=20000)
        return

    img_path, w, h = draw_topchat_image(users_list, client, title, group_name=group_name)
    if img_path:
        client.sendLocalImage(img_path, thread_id=thread_id, thread_type=thread_type, ttl=60000*5, width=w, height=h)
        if os.path.exists(img_path):
            os.remove(img_path)

# ===== Xử lý lệnh TopChat =====
def handle_rank_command(message, message_object, thread_id, thread_type, author_id, client):
    parts = message.strip().lower().split()
    arg = parts[1] if len(parts)>1 else ""
    group_name = get_group_name(client, thread_id)
    if arg in ["on","off","rs"]:
        if author_id not in ADMIN:
            client.sendMessage(Message(text="⛔ Lệnh này chỉ dành cho ADMIN."), thread_id, thread_type, ttl=15000)
            return
        if arg=="on":
            set_topchat_status(thread_id, True)           
            if not get_group_path(thread_id).exists():
                save_group_data(thread_id, {"daily": {}, "total": {"users": []}})
            client.sendMessage(Message(text=f"✅ Đã bật thống kê TopChat cho nhóm {group_name}"), thread_id, thread_type, ttl=20000)
        elif arg=="off":
            set_topchat_status(thread_id, False)            
            path = get_group_path(thread_id)
            if path.exists():
                path.unlink()
            client.sendMessage(Message(text=f"🛑 Đã tắt thống kê TopChat cho nhóm {group_name}"), thread_id, thread_type, ttl=20000)
        elif arg=="rs":
            save_group_data(thread_id, {"daily": {}, "total": {"users": []}})
            client.sendMessage(Message(
                text=f"♻️ Đã reset dữ liệu TopChat nhóm {group_name}"
            ), thread_id, thread_type, ttl=20000)
        return

    if arg=="total":
        show_topchat(thread_id, thread_type, author_id, client, mode="total")
    else:
        show_topchat(thread_id, thread_type, author_id, client, mode="today")

# ===== Export module =====
def TQD():
    return {"topchat": handle_rank_command}
