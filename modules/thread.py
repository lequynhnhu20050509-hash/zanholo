import json
import os
import time
import requests
from io import BytesIO
from zlapi.models import *
from PIL import Image, ImageDraw, ImageFont
from config import PREFIX
from config import ADMIN

FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
if not os.path.exists(FONT_PATH):
    print(f"Lỗi: Không tìm thấy file font tại {FONT_PATH}. Vui lòng kiểm tra đường dẫn hoặc cài đặt font.")
    pass


CACHE_DIR = "modules/cache/thread_menu_temp"
os.makedirs(CACHE_DIR, exist_ok=True)

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Thread",
    'power': "Quản trị viên Bot"
}

def is_admin(author_id):
    return str(author_id) == str(ADMIN)

def get_user_name(client, author_id):
    try:
        user_info = client.fetchUserInfo(author_id)
        author_info = getattr(user_info, 'changed_profiles', {}).get(author_id, {}) if user_info else {}
        return author_info.get('zaloName', 'Không xác định')
    except Exception as e:
        return 'Không xác định'

def send_styled_message(client, name, rest_text, message_object, thread_id, thread_type, ttl=30000):
    msg = f"{name}\n➜{rest_text}"
    styles = MultiMsgStyle([
        MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
        MessageStyle(offset=0, length=len(name), style="bold", auto_format=False),
    ])
    client.replyMessage(
        Message(text=msg, style=styles),
        message_object, thread_id, thread_type, ttl=ttl
    )

def load_duyetbox_data():
    file_path = 'modules/cache/duyetboxdata.json'
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

def save_duyetbox_data(data):
    file_path = 'modules/cache/duyetboxdata.json'
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except IOError:
        print(f"Warning: Custom font not found at {FONT_PATH}. Using default font.")
        return ImageFont.load_default()
    except Exception as e:
        print(f"Error loading font: {e}. Using default font.")
        return ImageFont.load_default()

def draw_box(draw, x, y, w, h, radius=22, fill=(40,40,40), outline=(255,255,255), outline_width=4):
    draw.rounded_rectangle([x, y, x+w, y+h], radius=radius, fill=fill, outline=outline, width=outline_width)

def text_wrap(text, font, max_width):
    lines = []
    line = ""
    words = text.split()
    for word in words:
        test_line = f"{line} {word}".strip()
        try:
            w_test, h_test = font.getbbox(test_line)[2], font.getbbox(test_line)[3] - font.getbbox(test_line)[1]
        except Exception:
            w_test = font.getlength(test_line)

        if w_test > max_width and line:
            lines.append(line)
            line = word
        else:
            line = test_line
    if line:
        lines.append(line)
    return lines

def calc_box_height(lines, font, w):
    try:
        line_height_base = font.getbbox("Ay")[3] - font.getbbox("Ay")[1]
    except Exception:
        line_height_base = 25

    title_h = line_height_base + 32
    
    content_h = 0
    for line_text in lines:
        wrapped = text_wrap(line_text, font, w - 38)
        content_h += len(wrapped) * (line_height_base + 6)
    
    y_bot = 28
    return title_h + content_h + y_bot

def draw_menu_box(draw, x, y, w, title, lines, font, color, title_color=(245,245,245)):
    box_h = calc_box_height(lines, font, w)
    draw_box(draw, x, y, w, box_h, 22, (38,38,38,230), color, 4)
    draw.text((x+24, y+22), title, font=font, fill=title_color)
    content_x = x+38
    
    try:
        title_bbox = font.getbbox(title)
        y_text = y + (title_bbox[3] - title_bbox[1]) + 42
        line_height = (font.getbbox("Ay")[3] - font.getbbox("Ay")[1]) + 6
    except Exception:
        y_text = y + 25 + 42
        line_height = 25 + 6

    for line_text in lines:
        line_lines = text_wrap(line_text, font, w-38)
        for l_wrapped in line_lines:
            draw.text((content_x, y_text), l_wrapped, font=font, fill=(220,220,220))
            y_text += line_height
    draw.line((x+22, y+box_h-17, x+w-22, y+box_h-17), fill=(130,130,130), width=2)
    return box_h

def fetch_group_avatar(client, group_id, size=72):
    try:
        group_info = client.fetchGroupInfo(group_id)
        info = getattr(group_info, 'gridInfoMap', {}).get(str(group_id), {})
        url = info.get('fullAvt', None) or info.get('avatar', None)
        if url:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content)).convert("RGBA").resize((size, size))
            mask = Image.new('L', (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            img.putalpha(mask)
            return img
    except Exception:
        pass
    img = Image.new("RGBA", (size, size), (60, 60, 60, 255))
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return img

def draw_group_list_box_image(client, group_ids, title="DANH SÁCH NHÓM", color_box=(255,255,255), page=1, total_pages=1):
    font_title = get_font(34)
    font_name = get_font(25)
    font_id = get_font(19)
    avatar_size = 70
    margin_left = 60
    margin_top = 110
    row_h = 98
    box_w = 1050
    groups_per_page = 12
    
    if not group_ids:
        total_pages = 1
        current_groups = []
        n = 0
    else:
        total_pages = (len(group_ids) + groups_per_page - 1) // groups_per_page
        start_idx = (page - 1) * groups_per_page
        end_idx = min(start_idx + groups_per_page, len(group_ids))
        current_groups = group_ids[start_idx:end_idx]
        n = len(current_groups)

    h = margin_top + n * row_h + 120
    image_width, image_height = box_w, h
    bg = Image.new("RGBA", (image_width, image_height), (28,28,28))
    draw = ImageDraw.Draw(bg)
    
    title_text = f"{title} (Trang {page}/{total_pages})"
    try:
        tw = font_title.getlength(title_text)
    except Exception:
        tw = draw.textlength(title_text, font=font_title)

    draw.text(((image_width-tw)//2, 36), title_text, font=font_title, fill=(255,255,255))
    box_x = margin_left
    box_w_group = 880
    
    for idx, gid in enumerate(current_groups):
        y = margin_top + idx * row_h
        av = fetch_group_avatar(client, gid, avatar_size)
        draw_box(draw, box_x, y, box_w_group, row_h-10, 22, (40,40,40), color_box, 2)
        bg.alpha_composite(av, (box_x+12, y + (row_h-avatar_size)//2))
        try:
            info = client.fetchGroupInfo(gid)
            group_info = getattr(info, 'gridInfoMap', {}).get(str(gid), {})
            name = group_info.get('name', 'Không xác định')
        except Exception:
            name = "Không xác định"
        
        name_show = name if len(name) <= 22 else name[:20] + "…"
        draw.text((box_x+avatar_size+32, y+18), name_show, font=font_name, fill=(245,245,245))
        draw.text((box_x+avatar_size+32, y+18+32), f"ID: {gid}", font=font_id, fill=(200,200,200))
    
    footer_text = f"Tổng số: {len(group_ids)}"
    try:
        footer_text_width = font_title.getlength(footer_text)
    except Exception:
        footer_text_width = draw.textlength(footer_text, font=font_title)

    draw.text(((image_width-footer_text_width)//2, image_height-44), footer_text, font=font_title, fill=(180,180,180))
    outname = os.path.join(CACHE_DIR, f"thread_list_{os.getpid()}_{int(time.time())}.jpg")
    bg = bg.convert("RGB")
    bg.save(outname, "JPEG", quality=100, optimize=True)
    return outname, image_width, image_height

def show_menu_image():
    image_width, image_height = 1100, 900
    margin_x = 62
    bg = Image.new("RGBA", (image_width, image_height), (25,25,25))
    draw = ImageDraw.Draw(bg)
    font = get_font(25)
    font_title = get_font(36)
    draw_box(draw, margin_x, 28, image_width-margin_x*2, 80, 30, (40,40,40), (255,255,255), 4)
    
    try:
        title_width = font_title.getlength("QUẢN LÝ NHÓM")
    except Exception:
        title_width = draw.textlength("QUẢN LÝ NHÓM", font=font_title)

    draw.text((image_width//2 - title_width//2, 53), "QUẢN LÝ NHÓM", font=font_title, fill=(255,255,255))
    y = 130
    card_w = image_width-2*margin_x-6
    user_lines = [
        f"• {PREFIX}thread duyet: Duyệt nhóm hiện tại",
        f"• {PREFIX}thread ban: Ban nhóm hiện tại",
        f"• {PREFIX}thread duyetid <ID>: Duyệt nhóm theo ID",
        f"• {PREFIX}thread banid <ID>: Ban nhóm theo ID",
        f"• {PREFIX}thread duyetall: Duyệt tất cả nhóm",
        f"• {PREFIX}thread banall: Ban tất cả nhóm",
        f"• {PREFIX}thread list [page]: Xem danh sách nhóm đã duyệt",
        f"• {PREFIX}thread cd [page]: Xem danh sách nhóm chưa duyệt"
    ]
    rule_lines = [
        "Chỉ quản trị viên bot được sử dụng.",
        "Lưu ý: Nhập đúng ID nhóm khi sử dụng duyetid hoặc banid."
    ]
    sys_lines = [
        f"Phiên bản: {des['version']}",
        f"Tác giả: {des['credits']}",
        f"Quyền: {des['power']}"
    ]
    color_white = (255,255,255)
    color_gray = (150,150,150)
    box_h = draw_menu_box(draw, margin_x+3, y, card_w, "🌐 DANH SÁCH LỆNH", user_lines, font, color_white)
    y += box_h + 10
    box_h = draw_menu_box(draw, margin_x+3, y, card_w, "📜 LƯU Ý", rule_lines, font, color_gray, (220,220,220))
    y += box_h + 10
    box_h = draw_menu_box(draw, margin_x+3, y, card_w, "ℹ️ THÔNG TIN", sys_lines, font, (180,180,180), (220,220,220))
    outname = os.path.join(CACHE_DIR, f"thread_menu_{os.getpid()}_{int(time.time())}.jpg")
    bg = bg.convert("RGB")
    bg.save(outname, "JPEG", quality=100, optimize=True)
    return outname

def handle_duyetbox_command(message, message_object, thread_id, thread_type, author_id, client):
    if not client.is_allowed_author(author_id):
        img_path = show_menu_image()
        with Image.open(img_path) as img:
            width, height = img.size
        client.sendLocalImage(
            img_path,
            thread_id=thread_id,
            thread_type=thread_type,
            width=width,
            height=height,
            ttl=120000
        )
        if os.path.exists(img_path):
            os.remove(img_path)
        return

    name = get_user_name(client, author_id)
    text = message.split()

    if len(text) < 2 or text[1].lower() == "help":
        img_path = show_menu_image()
        with Image.open(img_path) as img:
            width, height = img.size
        client.sendLocalImage(
            img_path,
            thread_id=thread_id,
            thread_type=thread_type,
            width=width,
            height=height,
            ttl=120000
        )
        if os.path.exists(img_path):
            os.remove(img_path)
        return

    action = text[1].lower()
    data = load_duyetbox_data()
    groups_per_page = 12

    if action == "duyet":
        if thread_id not in data:
            data.append(thread_id)
            save_duyetbox_data(data)
            client.reload_duyetbox_data()
            rest_text = " đã duyệt nhóm này thành công! ✅"
            send_styled_message(client, name, rest_text, message_object, thread_id, thread_type)
            img_path, width, height = draw_group_list_box_image(client, [thread_id], title="NHÓM ĐÃ DUYỆT", color_box=(255,255,255))
            client.sendLocalImage(
                img_path,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=90000
            )
            if os.path.exists(img_path): os.remove(img_path)
        else:
            rest_text = " nhóm này đã được duyệt từ trước rồi! 🔄"
            send_styled_message(client, name, rest_text, message_object, thread_id, thread_type)
        

    elif action == "duyetid" and len(text) > 2:
        target_group_id = text[2]
        if target_group_id not in data:
            data.append(target_group_id)
            save_duyetbox_data(data)
            client.reload_duyetbox_data()
            rest_text = f" đã duyệt nhóm ID: {target_group_id} thành công! ✅"
            send_styled_message(client, name, rest_text, message_object, thread_id, thread_type)
            img_path, width, height = draw_group_list_box_image(client, [target_group_id], title="NHÓM ĐÃ DUYỆT", color_box=(255,255,255))
            client.sendLocalImage(
                img_path,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=90000
            )
            if os.path.exists(img_path): os.remove(img_path)
        else:
            rest_text = f" nhóm ID: {target_group_id} đã được duyệt từ trước! 🔄"
            send_styled_message(client, name, rest_text, message_object, thread_id, thread_type)
        

    elif action == "ban":
        if thread_id in data:
            data.remove(thread_id)
            save_duyetbox_data(data)
            client.reload_duyetbox_data()
            rest_text = " đã ban nhóm này! ❌"
            send_styled_message(client, name, rest_text, message_object, thread_id, thread_type)
            img_path, width, height = draw_group_list_box_image(client, [thread_id], title="NHÓM BỊ BAN", color_box=(255,255,255))
            client.sendLocalImage(
                img_path,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=90000
            )
            if os.path.exists(img_path): os.remove(img_path)
        else:
            rest_text = " nhóm này chưa được duyệt nên không thể ban! 🚫"
            send_styled_message(client, name, rest_text, message_object, thread_id, thread_type)
        

    elif action == "banid" and len(text) > 2:
        target_group_id = text[2]
        if target_group_id in data:
            data.remove(target_group_id)
            save_duyetbox_data(data)
            client.reload_duyetbox_data()
            rest_text = f" đã ban nhóm ID: {target_group_id}! ❌"
            send_styled_message(client, name, rest_text, message_object, thread_id, thread_type)
            img_path, width, height = draw_group_list_box_image(client, [target_group_id], title="NHÓM BỊ BAN", color_box=(255,255,255))
            client.sendLocalImage(
                img_path,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=90000
            )
            if os.path.exists(img_path): os.remove(img_path)
        else:
            rest_text = f" nhóm ID: {target_group_id} chưa được duyệt nên không thể ban! 🚫"
            send_styled_message(client, name, rest_text, message_object, thread_id, thread_type)
        

    elif action == "duyetall":
        all_group_ids = list(client.fetchAllGroups().gridVerMap.keys())
        newly_approved_groups = [group_id for group_id in all_group_ids if group_id not in data]
        if newly_approved_groups:
            data.extend(newly_approved_groups)
            save_duyetbox_data(data)
            client.reload_duyetbox_data()
            rest_text = f" đã duyệt tất cả {len(newly_approved_groups)} nhóm! 🎉"
            send_styled_message(client, name, rest_text, message_object, thread_id, thread_type)
            
            total_pages = (len(newly_approved_groups) + groups_per_page - 1) // groups_per_page
            for page in range(1, total_pages + 1):
                img_path, width, height = draw_group_list_box_image(client, newly_approved_groups, title="DUYỆT TẤT CẢ NHÓM", color_box=(255,255,255), page=page, total_pages=total_pages)
                client.sendLocalImage(
                    img_path,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=width,
                    height=height,
                    ttl=90000
                )
                if os.path.exists(img_path): os.remove(img_path)
        else:
            send_styled_message(client, name, " không có nhóm nào mới để duyệt! 🔄", message_object, thread_id, thread_type)


    elif action == "banall":
        banned_groups = [group_id for group_id in data]
        if banned_groups:
            data.clear()
            save_duyetbox_data(data)
            client.reload_duyetbox_data()
            rest_text = f" đã ban tất cả {len(banned_groups)} nhóm! 💥"
            send_styled_message(client, name, rest_text, message_object, thread_id, thread_type)
            
            total_pages = (len(banned_groups) + groups_per_page - 1) // groups_per_page
            for page in range(1, total_pages + 1):
                img_path, width, height = draw_group_list_box_image(client, banned_groups, title="BAN TẤT CẢ NHÓM", color_box=(255,255,255), page=page, total_pages=total_pages)
                client.sendLocalImage(
                    img_path,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=width,
                    height=height,
                    ttl=90000
                )
                if os.path.exists(img_path): os.remove(img_path)
        else:
            send_styled_message(client, name, " không có nhóm nào để ban! 🚫", message_object, thread_id, thread_type)

    elif action == "list":
        approved_groups = load_duyetbox_data()
        total_pages = (len(approved_groups) + groups_per_page - 1) // groups_per_page
        page = 1
        if len(text) > 2 and text[2].isdigit():
            page = int(text[2])
            if page < 1 or (total_pages > 0 and page > total_pages):
                rest_text = f" Trang {page} không hợp lệ! Vui lòng chọn trang từ 1 đến {total_pages if total_pages > 0 else 1}. ❓"
                send_styled_message(client, name, rest_text, message_object, thread_id, thread_type)
                return
        
        rest_text = f" đang xem danh sách {len(approved_groups)} nhóm đã duyệt! 📋 (Trang {page}/{total_pages if total_pages > 0 else 1})"
        send_styled_message(client, name, rest_text, message_object, thread_id, thread_type)
        
        if approved_groups:
            img_path, width, height = draw_group_list_box_image(client, approved_groups, title="DANH SÁCH NHÓM ĐÃ DUYỆT", color_box=(255,255,255), page=page, total_pages=total_pages)
            client.sendLocalImage(
                img_path,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000
            )
            if os.path.exists(img_path): os.remove(img_path)
        else:
            send_styled_message(client, name, " chưa có nhóm nào được duyệt cả bro, buồn vcl 😔", message_object, thread_id, thread_type)


    elif action == "cd":
        all_group_ids_map = client.fetchAllGroups().gridVerMap
        all_group_ids = list(all_group_ids_map.keys())
        approved_groups = load_duyetbox_data()
        unapproved_groups = [group_id for group_id in all_group_ids if group_id not in approved_groups]
        
        total_pages = (len(unapproved_groups) + groups_per_page - 1) // groups_per_page
        page = 1
        if len(text) > 2 and text[2].isdigit():
            page = int(text[2])
            if page < 1 or (total_pages > 0 and page > total_pages):
                rest_text = f" Trang {page} không hợp lệ! Vui lòng chọn trang từ 1 đến {total_pages if total_pages > 0 else 1}. ❓"
                send_styled_message(client, name, rest_text, message_object, thread_id, thread_type)
                return
        
        rest_text = f" đang xem danh sách {len(unapproved_groups)} nhóm chưa duyệt! 📋 (Trang {page}/{total_pages if total_pages > 0 else 1})"
        send_styled_message(client, name, rest_text, message_object, thread_id, thread_type)
        
        if unapproved_groups:
            img_path, width, height = draw_group_list_box_image(client, unapproved_groups, title="DANH SÁCH NHÓM CHƯA DUYỆT", color_box=(255,255,255), page=page, total_pages=total_pages)
            client.sendLocalImage(
                img_path,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=120000
            )
            if os.path.exists(img_path): os.remove(img_path)
        else:
            rest_text = " không có nhóm nào chưa duyệt! ✅"
            send_styled_message(client, name, rest_text, message_object, thread_id, thread_type)

    else:
        rest_text = " đã nhập sai lệnh rồi! Xem lại menu nhé! ❓"
        send_styled_message(client, name, rest_text, message_object, thread_id, thread_type)
        img_path = show_menu_image()
        with Image.open(img_path) as img:
            width, height = img.size
        client.sendLocalImage(
            img_path,
            thread_id=thread_id,
            thread_type=thread_type,
            width=width,
            height=height,
            ttl=120000
        )
        if os.path.exists(img_path):
            os.remove(img_path)

def TQD():
    return {
        'thread': handle_duyetbox_command
    }