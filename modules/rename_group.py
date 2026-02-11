import threading
from zlapi.models import Message, Group
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random, os

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Đổi tên group",
    'power': "Quản trị viên Bot"
}



# --- Cấu hình ---
idadmin = ["7376495146241444949"]  # ID admin
EMOJI_LIST = ["😍", "🥀", "👻", "💤", "😂", "🔥", "💖", "🤡", "🦋", "✨"]
FONT_PATH = "modules/cache/font/2.ttf"


# --- Gửi reaction ngẫu nhiên ---
def send_random_reactions(client, message_object, thread_id, thread_type):
    for emoji in random.sample(EMOJI_LIST, 6):
        try:
            client.sendReaction(message_object, emoji, thread_id, thread_type, reactionType=75)
        except Exception as e:
            print(f"Lỗi khi gửi reaction {emoji}: {e}")



FONT_PATH = "modules/cache/font/arial.ttf"  # thay bằng font bạn có

def create_group_rename_image(new_name):
    width, height = 1200, 600
    bg = Image.new("RGB", (width, height), (10, 10, 30))
    draw = ImageDraw.Draw(bg)

    # --- Nền sao ---
    for _ in range(400):
        x, y = random.randint(0, width - 1), random.randint(0, height - 1)
        s = random.randint(2, 5)
        draw.ellipse((x, y, x + s, y + s), fill="white")

    # --- Text ---
    font_title = ImageFont.truetype(FONT_PATH, 60)
    font_name = ImageFont.truetype(FONT_PATH, 70)

    text1 = "Đổi Tên Nhóm Thành Công!"
    text2 = f"{new_name}"

    t1_w, t1_h = draw.textbbox((0, 0), text1, font=font_title)[2:]
    t2_w, t2_h = draw.textbbox((0, 0), text2, font=font_name)[2:]

    t1_x, t1_y = (width - t1_w) // 2, height // 3
    t2_x, t2_y = (width - t2_w) // 2, t1_y + 120

    # --- Vẽ khung mờ bo góc cho tên nhóm ---
    rect_padding_x = 50
    rect_padding_y = 20
    rect_x1 = t2_x - rect_padding_x
    rect_y1 = t2_y - rect_padding_y
    rect_x2 = t2_x + t2_w + rect_padding_x
    rect_y2 = t2_y + t2_h + rect_padding_y
    radius = 30

    # Tạo mặt nạ bo góc
    rect = Image.new("L", (width, height), 0)
    rect_draw = ImageDraw.Draw(rect)
    rect_draw.rounded_rectangle(
        (rect_x1, rect_y1, rect_x2, rect_y2),
        radius=radius,
        fill=180
    )

    # Làm mờ vùng khung và pha trộn để tạo cảm giác “trong như nước”
    blur_bg = bg.filter(ImageFilter.GaussianBlur(8))
    bg.paste(blur_bg, mask=rect)

    # Vẽ khung viền trắng nhẹ
    draw.rounded_rectangle(
        (rect_x1, rect_y1, rect_x2, rect_y2),
        radius=radius,
        outline=(255, 255, 255, 200),
        width=3
    )

    # --- Vẽ chữ ---
    draw.text((t1_x, t1_y), text1, font=font_title, fill="white")
    draw.text((t2_x, t2_y), text2, font=font_name, fill="white")

    # --- Lưu ảnh ---
    path = "group_rename_success.jpg"
    bg.save(path, quality=95)
    return path


# --- Lệnh chính ---
def handle_group_rename(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Kiểm tra quyền admin
        if str(author_id) not in idadmin:
            client.replyMessage(
                Message(text="🚫 Bạn không có quyền sử dụng lệnh này. Chỉ có admin Latte mới được sử dụng lệnh này"),
                message_object, thread_id, thread_type, ttl=60000
            )
            return

        # Cắt bỏ phần lệnh “rngr” để lấy tên nhóm thật
        parts = message.strip().split(maxsplit=1)
        if len(parts) < 2:
            client.replyMessage(
                Message(text="🚫 Bạn cần nhập tên nhóm mới. Ví dụ: rngr Chill Zone"),
                message_object, thread_id, thread_type, ttl=60000
            )
            return

        new_name = parts[1]

        send_random_reactions(client, message_object, thread_id, thread_type)
        client.replyMessage(
            Message(text="🔄 Đang đổi tên nhóm, vui lòng chờ... ☘️"),
            message_object, thread_id, thread_type, ttl=60000
        )

        def rename_task():
            try:
                result = client.changeGroupName(new_name, thread_id)
                if result and isinstance(result, Group):
                    img = create_group_rename_image(new_name)
                    client.sendLocalImage(img, thread_id, thread_type, ttl=60000, width=1200, height=600)
                    client.replyMessage(
                        Message(text=f"✅ Đã đổi tên nhóm thành: {new_name}"),
                        message_object, thread_id, thread_type, ttl=60000
                    )
                    os.remove(img)
                else:
                    client.replyMessage(
                        Message(text="🚫 Có lỗi khi đổi tên nhóm."),
                        message_object, thread_id, thread_type, ttl=60000
                    )
            except Exception as e:
                client.replyMessage(
                    Message(text=f"🚦 Lỗi khi đổi tên nhóm: {e}"),
                    message_object, thread_id, thread_type, ttl=60000
                )

        threading.Thread(target=rename_task).start()

    except Exception as e:
        client.replyMessage(
            Message(text=f"❌ Lỗi không xác định: {e}"),
            message_object, thread_id, thread_type, ttl=60000
        )



# --- Đăng ký lệnh ---
def TQD():
    return {
        'rngr': handle_group_rename
    }
