import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
from datetime import datetime
from urllib.parse import quote_plus
import random
from zlapi.models import Message
from config import PREFIX
des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Tạo QR chuyển khoản",
    'power': "Quản trị viên Bot"
}


# --- ĐƯỜNG DẪN FONT ---
FONT_BOLD_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"

# --- HỖ TRỢ TẢI ẢNH ---
def fetch_image(url, size=None):
    if not url:
        return None
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGBA")
        if size:
            img = img.resize(size, Image.LANCZOS)
        return img
    except Exception as e:
        print(f"Lỗi tải ảnh: {e}")
        return None


# --- TẠO AVATAR TRÒN CÓ VIỀN ---
def make_circle_avatar_with_border(img, size, inner_border=4, outer_border=2):
    img = img.convert("RGBA").resize(size, Image.LANCZOS)
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size[0], size[1]), fill=255)

    total_border = inner_border + outer_border
    border_size = (size[0] + total_border * 2, size[1] + total_border * 2)
    bordered = Image.new("RGBA", border_size, (0, 0, 0, 0))
    draw_border = ImageDraw.Draw(bordered)

    # Viền đen ngoài
    draw_border.ellipse([0, 0, border_size[0]-1, border_size[1]-1], outline=(0, 0, 0), width=outer_border)
    # Viền trắng trong
    inner_offset = outer_border
    draw_border.ellipse([inner_offset, inner_offset, border_size[0]-inner_offset-1, border_size[1]-inner_offset-1],
                        outline=(255, 255, 255), width=inner_border)

    # Dán ảnh
    bordered.paste(img, (total_border, total_border), mask)

    # Áp mask tròn
    final_mask = Image.new("L", border_size, 0)
    draw_final = ImageDraw.Draw(final_mask)
    draw_final.ellipse((0, 0, border_size[0]-1, border_size[1]-1), fill=255)
    bordered.putalpha(final_mask)
    return bordered


# --- LOAD FONT ---
def load_font(path, size):
    try:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    except Exception as e:
        print(f"Font lỗi: {path} - {e}")
    try:
        return ImageFont.truetype("arialbd.ttf" if "Bold" in path else "arial.ttf", size)
    except:
        return ImageFont.load_default()


# --- TẠO QR BANK IMAGE ---
def create_qrbank_image(avatar_url, qr_url, account_name, bank_name, account_number, amount, add_info):
    W, H = 800, 850

    # NỀN GRADIENT
    bg = Image.new("RGBA", (W, H))
    grad = ImageDraw.Draw(bg)
    top_color = (232, 247, 255)
    bottom_color = (255, 255, 255)
    for i in range(H):
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * (i / H))
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * (i / H))
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * (i / H))
        grad.line([(0, i), (W, i)], fill=(r, g, b))

    # HIỆU ỨNG BOKEH
    for _ in range(10):
        bx, by = random.randint(0, W), random.randint(0, H)
        br = random.randint(60, 160)
        alpha = random.randint(25, 60)
        dot = Image.new("RGBA", (br * 2, br * 2), (255, 255, 255, 0))
        d = ImageDraw.Draw(dot)
        d.ellipse((0, 0, br * 2, br * 2), fill=(255, 255, 255, alpha))
        dot = dot.filter(ImageFilter.GaussianBlur(70))
        bg.paste(dot, (bx - br, by - br), dot)

    draw = ImageDraw.Draw(bg)

    # FONT
    font_title = load_font(FONT_BOLD_PATH, 62)
    font_time = load_font(FONT_BOLD_PATH, 36)

    # HEADER
    header = "QR CHUYỂN KHOẢN"
    tw = draw.textlength(header, font=font_title)
    draw.text(((W - tw)//2, 40), header, font=font_title, fill=(10, 50, 110))
    draw.line([(W*0.2, 115), (W*0.8, 115)], fill=(10, 50, 110, 150), width=5)

    # QR & AVATAR
    qr_raw = fetch_image(qr_url, size=(500, 500))
    if not qr_raw:
        return None

    qr_base = Image.new("RGBA", (540, 540), (255, 255, 255, 255))
    qr_resized = qr_raw.resize((500, 500), Image.LANCZOS)
    qr_base.paste(qr_resized, (20, 20))

    avatar_size = 80
    avatar = fetch_image(avatar_url, size=(avatar_size, avatar_size))
    if avatar:
        avatar_circ = make_circle_avatar_with_border(avatar, (avatar_size, avatar_size), 6, 3)
        cx, cy = 270, 270
        qr_base.paste(avatar_circ, (cx - avatar_size//2, cy - avatar_size//2), avatar_circ)

    # Bóng đổ QR
    shadow = Image.new("RGBA", (560, 560), (0, 0, 0, 0))
    d = ImageDraw.Draw(shadow)
    d.rounded_rectangle([15, 15, 545, 545], radius=30, fill=(0, 0, 0, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(25))
    bg.paste(shadow, (W//2 - 280, 150), shadow)
    bg.paste(qr_base, (W//2 - 270, 160), qr_base)

    # THỜI GIAN DƯỚI QR
    time_text = datetime.now().strftime("%H:%M - %d/%m/%Y")
    tw = draw.textlength(time_text, font=font_time)
    draw.text(((W - tw)//2, 720), time_text, font=font_time, fill=(80, 80, 80))

    # KHỐI THÔNG TIN (Glassmorphism)
    info_box = Image.new("RGBA", (W - 120, 500), (255, 255, 255, 140))
    info_box = info_box.filter(ImageFilter.GaussianBlur(10))
    bg.paste(info_box, (60, 780), info_box)

    # VIỀN NGOÀI
    final = Image.new("RGBA", (W + 60, H + 60), (255, 255, 255, 255))
    d = ImageDraw.Draw(final)
    d.rounded_rectangle([0, 0, W + 60, H + 60], radius=40, fill=(255, 255, 255),
                        outline=(220, 220, 220), width=2)
    final.paste(bg, (30, 30))

    return final.convert("RGB")


# --- PARSER LỆNH ---
def parse_qrbank_command(message: str):
    parts = message.strip().split()
    
    if len(parts) < 4 or not parts[0].startswith(f"{PREFIX}qrbank"):
        raise ValueError(f"Cú pháp không hợp lệ. Cú pháp: {PREFIX}qrbank <stk> <ngân_hàng> <số_tiền> <tên> [to <nội_dung>]")

    account_number = parts[1]
    bank_code = parts[2].lower()
    amount = parts[3]

    # Xác định vị trí từ 'to' (không phân biệt hoa thường)
    lower_parts = [p.lower() for p in parts]
    if "to" in lower_parts[4:]:
        idx = lower_parts.index("to")
        account_name = " ".join(parts[4:idx]).strip()
        add_info = " ".join(parts[idx+1:]).strip()
    else:
        account_name = " ".join(parts[4:]).strip()
        add_info = ""

    return {
        "account_number": account_number,
        "bank_code": bank_code,
        "amount": amount,
        "account_name": account_name,
        "add_info": add_info
    }


# --- HANDLER ---
def handle_qrbank_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        try:
            data = parse_qrbank_command(message)
        except ValueError as ve:
            client.sendMessage(Message(text=str(ve)), thread_id, thread_type,ttl=60000)
            return

        bank_codes = {
            "vcb": {"bin": "970436", "name": "VIETCOMBANK"},
            "vietcombank": {"bin": "970436", "name": "VIETCOMBANK"},
            "tcb": {"bin": "970407", "name": "TECHCOMBANK"},
            "techcombank": {"bin": "970407", "name": "TECHCOMBANK"},
            "mb": {"bin": "970422", "name": "MB BANK"},
            "mbbank": {"bin": "970422", "name": "MB BANK"},
            "acb": {"bin": "970416", "name": "ACB"},
            "vib": {"bin": "970441", "name": "VIB"},
            "bidv": {"bin": "970418", "name": "BIDV"},
            "vietinbank": {"bin": "970415", "name": "VIETINBANK"},
            "vtb": {"bin": "970415", "name": "VIETINBANK"},
            "tpbank": {"bin": "970423", "name": "TPBANK"},
            "vpbank": {"bin": "970432", "name": "VPBANK"},
            "agribank": {"bin": "970405", "name": "AGRIBANK"},
            "sacombank": {"bin": "970403", "name": "SACOMBANK"},
            "scb": {"bin": "970429", "name": "SCB"},
            "hdbank": {"bin": "970437", "name": "HDBANK"},
            "ocb": {"bin": "970448", "name": "OCB"},
            "msb": {"bin": "970426", "name": "MSB"},
            "maritimebank": {"bin": "970426", "name": "MSB"},
            "shb": {"bin": "970443", "name": "SHB"},
            "eximbank": {"bin": "970431", "name": "EXIMBANK"},
            "exim": {"bin": "970431", "name": "EXIMBANK"},
            "dongabank": {"bin": "970406", "name": "DONGABANK"},
            "dab": {"bin": "970406", "name": "DONGABANK"},
            "pvcombank": {"bin": "970412", "name": "PVCOMBANK"},
            "gpbank": {"bin": "970408", "name": "GPBANK"},
            "oceanbank": {"bin": "970414", "name": "OCEANBANK"},
            "namabank": {"bin": "970428", "name": "NAMABANK"},
            "seabank": {"bin": "970444", "name": "SEABANK"},
            "vietabank": {"bin": "970425", "name": "VIETABANK"},
            "vietcapitalbank": {"bin": "970425", "name": "VIETABANK"},
            "abbank": {"bin": "970420", "name": "ABBANK"},
            "baovietbank": {"bin": "970427", "name": "BAOVIETBANK"},
            # ... bo sung them neu can
        }

        bank_code = data['bank_code']
        if bank_code not in bank_codes:
            client.sendMessage(Message(text=f"Ngân hàng '{bank_code}' chưa hỗ trợ."), thread_id, thread_type,ttl=60000)
            return

        bin_code = bank_codes[bank_code]["bin"]
        full_bank_name = bank_codes[bank_code]["name"]

        # Lấy avatar và tên người gửi
        user_info = client.fetchUserInfo(author_id) or {}
        uid = user_info.get('uid', author_id)
        changed_profiles = user_info.get('changed_profiles', {})
        profile = changed_profiles.get(uid, {}) or changed_profiles.get(author_id, {}) or {}
        avatar_url = profile.get('avatar')
        author_name = profile.get('zaloName') or user_info.get('zaloName') or data['account_name'] or "Người nhận"

        # Tạo URL QR
        encoded_account_name = quote_plus(data['account_name'])
        encoded_add_info = quote_plus(data['add_info'])
        qr_url = f"https://img.vietqr.io/image/{bin_code}-{data['account_number']}-qr_only.jpg?accountName={encoded_account_name}&amount={data['amount']}&addInfo={encoded_add_info}"

        # Tạo ảnh QR
        image = create_qrbank_image(avatar_url, qr_url, author_name, full_bank_name,
                                    data['account_number'], data['amount'], data['add_info'])
        
        path_save = "qrbank_result.jpg"
        image.save(path_save, quality=95)
        client.sendLocalImage(path_save, thread_id=thread_id, thread_type=thread_type,ttl=60000*10,
                              width=image.width, height=image.height)
        if os.path.exists(path_save):
            os.remove(path_save)

    except Exception as e:
        pass

# --- EXPORT MODULE ---
def TQD():
    return {'qrbank': handle_qrbank_command}
