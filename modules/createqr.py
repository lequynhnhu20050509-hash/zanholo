from zlapi.models import Message
import requests
import urllib.parse
import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import tempfile
from config import PREFIX
des = {
    'version': "5.2.0",
    'credits': "Latte",
    'description': "Tạo QR",
    'power': "Thành viên",
}

FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
CARD_W, CARD_H = 180, 180
PADDING = 28
MAX_ITEMS = 9

# ===== FONT =====
def get_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except:
        return ImageFont.load_default()

# ===== VẼ DANH SÁCH NỀN =====
def draw_background_list_image(background_files):
    cols = 3
    rows = (len(background_files) + cols - 1) // cols
    WIDTH = CARD_W * cols + PADDING * (cols + 1)
    HEIGHT = CARD_H * rows + PADDING * (rows + 1) + 60

    img = Image.new("RGBA", (WIDTH, HEIGHT), (25, 25, 45))
    draw = ImageDraw.Draw(img)

    # tiêu đề
    font_title = get_font(36)
    text = "CHỌN NỀN QR SIÊU ĐẸP"
    tw = font_title.getlength(text)
    draw.text(((WIDTH - tw) / 2, 12), text, font=font_title, fill=(255, 255, 255))

    font_index = get_font(28)

    for idx, file_path in enumerate(background_files):
        row = idx // cols
        col = idx % cols
        cx = PADDING + col * (CARD_W + PADDING)
        cy = 60 + PADDING + row * (CARD_H + PADDING)

        # khung nền bo góc + bóng
        shadow = Image.new("RGBA", (CARD_W + 12, CARD_H + 12), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle([6, 6, CARD_W + 6, CARD_H + 6], radius=22, fill=(0, 0, 0, 110))
        img.alpha_composite(shadow, (cx - 6, cy - 6))

        draw.rounded_rectangle([cx, cy, cx + CARD_W, cy + CARD_H], radius=22, fill=(255, 255, 255, 40))

        # ảnh nền
        try:
            cover = Image.open(file_path).convert("RGBA")
            cover.thumbnail((CARD_W - 4, CARD_H - 4))
            img.paste(cover, (cx + 2, cy + 2), cover)
        except:
            draw.rounded_rectangle([cx, cy, cx + CARD_W, cy + CARD_H], radius=22, fill=(180, 180, 180))

        # số thứ tự
        idx_box_w, idx_box_h = 44, 44
        idx_x = cx + CARD_W - idx_box_w - 10
        idx_y = cy + 10
        draw.rounded_rectangle([idx_x, idx_y, idx_x + idx_box_w, idx_y + idx_box_h], radius=14, fill=(220, 220, 255))
        t = str(idx + 1)
        tx = idx_x + (idx_box_w - font_index.getlength(t)) / 2
        draw.text((tx, idx_y + 6), t, font=font_index, fill=(60, 60, 180))

    # footer hướng dẫn
    font_footer = get_font(22)
    footer = "➜ Nhập: chon <số> để chọn nền QR của bạn"
    draw.text(((WIDTH - font_footer.getlength(footer)) / 2, HEIGHT - 40),
              footer, font=font_footer, fill=(200, 200, 240))

    out_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
    img.convert("RGB").save(out_path, "PNG")
    return out_path

# ===== LỆNH TẠO QR =====
def handle_qrcode_command(message, message_object, thread_id, thread_type, author_id, client):
    text = message.strip().split()
    if len(text) < 2:
        client.replyMessage(Message(text=f"❌ Vui lòng nhập nội dung QR.\nVí dụ: {PREFIX}qrcode Hello World"), message_object, thread_id, thread_type,ttl=60000)
        return

    content = " ".join(text[1:])
    client.next_step = getattr(client, 'next_step', {})
    client.next_step[author_id] = {'content': content, 'step': 'choose_background'}

    background_folder = 'modules/nen'
    valid_ext = ['.jpg', '.jpeg', '.png']
    background_files = [os.path.join(background_folder, f) for f in os.listdir(background_folder)
                        if any(f.lower().endswith(ext) for ext in valid_ext)]

    if not background_files:
        client.replyMessage(Message(text="❌ Không tìm thấy nền nào trong thư mục modules/nen"), message_object, thread_id, thread_type,ttl=60000)
        return

    background_files = background_files[:MAX_ITEMS]
    client.next_step[author_id]['background_files'] = background_files

    img_path = draw_background_list_image(background_files)
    with Image.open(img_path) as im:
        w, h = im.size
    client.sendLocalImage(img_path, thread_id=thread_id, thread_type=thread_type,
                          width=w, height=h,
                          message=Message(text=f"✨ Chọn nền bạn thích và nhập: {PREFIX}kieuqr <số>"))
    os.remove(img_path)

# ===== LỆNH CHỌN NỀN =====
def handle_select_qr_background(message, message_object, thread_id, thread_type, author_id, client):
    client.next_step = getattr(client, 'next_step', {})
    if author_id not in client.next_step:
        return

    step_data = client.next_step[author_id]
    if step_data.get('step') != 'choose_background':
        return

    parts = message.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        client.replyMessage(Message(text="❌ Cú pháp: chon <số> (vd: chon 2)"), message_object, thread_id, thread_type,ttl=60000)
        return

    sel = int(parts[1])
    backgrounds = step_data['background_files']
    if sel < 1 or sel > len(backgrounds):
        client.replyMessage(Message(text=f"❌ Số chọn không hợp lệ. Chọn từ 1 đến {len(backgrounds)}"), message_object, thread_id, thread_type,ttl=60000)
        return

    background_path = backgrounds[sel - 1]
    content = step_data['content']

    try:
        api_qr = f'https://api.qrserver.com/v1/create-qr-code/?size=600x600&data={urllib.parse.quote(content)}&format=png'
        r = requests.get(api_qr)
        qr_image_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        with open(qr_image_path, 'wb') as f:
            f.write(r.content)

        qr_image = Image.open(qr_image_path).convert("RGBA")

        # loại bỏ nền trắng QR
        qr_data = qr_image.load()
        for x in range(qr_image.width):
            for y in range(qr_image.height):
                r, g, b, a = qr_data[x, y]
                if r > 240 and g > 240 and b > 240:
                    qr_data[x, y] = (255, 255, 255, 0)

        background = Image.open(background_path).convert("RGBA").resize((qr_image.width + 200, qr_image.height + 200))
        bx = (background.width - qr_image.width) // 2
        by = (background.height - qr_image.height) // 2
        background.paste(qr_image, (bx, by), qr_image)

        final_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        background.save(final_path, "PNG")

        client.sendLocalImage(final_path, thread_id=thread_id, thread_type=thread_type,ttl=60000*10,
                              width=1080, height=1080,
                              message=Message(text="✅ QR của bạn đã sẵn sàng!"))

        os.remove(final_path)
        os.remove(qr_image_path)
        del client.next_step[author_id]

    except Exception as e:
        client.replyMessage(Message(text=f"⚠️ Lỗi tạo QR: {str(e)}"), message_object, thread_id, thread_type,ttl=60000)

# ===== ĐĂNG KÝ LỆNH =====
def TQD():
    return {
        'qrcode': handle_qrcode_command,
        'kieuqr': handle_select_qr_background
    }