import os
import time
import threading
import random
import requests
import json
import urllib.parse
from io import BytesIO
from PIL import Image
from zlapi.models import Message, ThreadType
from config import ADMIN

des = {
    'version': "4.0.1",
    'credits': "Latte",
    'description': "War ảnh + text (update hỗ trợ text tùy chỉnh)",
    'power': "Admin"
}

IMAGE_DIR = "treoanh_img"
GROUP_FILE = "running_groups.json"

words = [
    "ngu", "vl", "đừng tưởng", "tao không biết", "cười", "chọc",
    "ẩn", "thoát", "hết thuốc", "khỏi nói", "giờ thì", "xong", "chửi tiếp"
]
emojis = ["😡", "🔥", "🤬", "💀", "🐧", "🤯", "😤", "👀", "💢"]

delay_time = 5

# --- Khởi tạo file running_groups.json nếu chưa có ---
if not os.path.exists(GROUP_FILE):
    with open(GROUP_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=4)

# --- Load JSON an toàn ---
def load_running_groups_safe():
    if not os.path.exists(GROUP_FILE):
        return []
    try:
        data = json.load(open(GROUP_FILE, "r", encoding="utf-8"))
        if not isinstance(data, list):
            return []
        safe_list = []
        for item in data:
            if isinstance(item, dict) and "thread_id" in item and "thread_type" in item:
                safe_list.append(item)
        return safe_list
    except Exception as e:
        print(f"[load_running_groups_safe] Lỗi đọc JSON: {e}")
        return []

def save_running_groups(groups):
    with open(GROUP_FILE, "w", encoding="utf-8") as f:
        json.dump(groups, f, ensure_ascii=False, indent=4)

running_groups = load_running_groups_safe()

# --- Helper Functions ---
def make_sentence():
    n = random.randint(6, 7)
    sentence_words = random.sample(words, n)
    pos = random.randint(0, n)
    sentence_words.insert(pos, "mày")
    emoji = random.choice(emojis)
    return " ".join(sentence_words) + " " + emoji

def convert_image_to_webp(image_url, temp_webp="temp.webp"):
    try:
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        img.save(temp_webp, format="WEBP", quality=85)
        return temp_webp
    except Exception as e:
        print(f"[convert_image_to_webp] Lỗi: {e}")
        return None

def upload_to_uguu(file_path):
    try:
        with open(file_path, 'rb') as file:
            response = requests.post("https://uguu.se/upload", files={'files[]': file})
            response.raise_for_status()
            data = response.json()
            return data['files'][0]['url']
    except Exception as e:
        print(f"[upload_to_uguu] Lỗi: {e}")
        return None

def download_image(image_url, save_path):
    try:
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"[download_image] Lỗi: {e}")
        return False

def process_image_pipeline(image_url):
    print(f"🔗 Bắt đầu xử lý ảnh từ: {image_url}")
    os.makedirs(IMAGE_DIR, exist_ok=True)
    temp_webp = convert_image_to_webp(image_url)
    if not temp_webp:
        return False, "❌ Lỗi khi convert ảnh sang webp."

    uguu_link = upload_to_uguu(temp_webp)
    os.remove(temp_webp)
    if not uguu_link:
        return False, "❌ Lỗi upload lên Uguu."

    existing_files = [f for f in os.listdir(IMAGE_DIR) if f.endswith(".jpg")]
    next_index = len(existing_files) + 1
    file_path = os.path.join(IMAGE_DIR, f"{next_index}.jpg")

    success = download_image(uguu_link, file_path)
    if not success:
        return False, "⚠️ Không tải được ảnh từ link Uguu."

    return True, f"✅ Ảnh #{next_index} đã được thêm vào bộ WAR!"

def extract_reply_image_url(message_object):
    try:
        if not hasattr(message_object, "quote") or not message_object.quote:
            return None
        quote = message_object.quote
        if "attach" not in quote:
            return None
        attach_data = json.loads(quote["attach"])
        photo_url = attach_data.get("hdUrl") or attach_data.get("href")
        if photo_url:
            photo_url = urllib.parse.unquote(photo_url.replace("\\/", "/"))
            if "jxl" in photo_url:
                photo_url = photo_url.replace("jxl", "jpg")
            return photo_url
    except Exception as e:
        print(f"[extract_reply_image_url] Lỗi: {e}")
    return None

# --- WAR Loop ---
def war_loop(client, thread_id, thread_type):
    print(f"[WAR LOOP] Khởi chạy cho thread_id={thread_id}, type={thread_type}")
    global delay_time
    if not os.path.exists("onetag.txt"):
        print("❌ Không tìm thấy onetag.txt")
        return
    with open("onetag.txt", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    if not lines:
        print("❌ onetag.txt trống")
        return
    while any(g["thread_id"] == thread_id for g in running_groups):
        for line in lines:
            if not any(g["thread_id"] == thread_id for g in running_groups):
                break
            try:
                img_list = [os.path.join(IMAGE_DIR, f) for f in os.listdir(IMAGE_DIR) if f.endswith(".jpg")]
                if not img_list:
                    continue
                img_path = random.choice(img_list)
                client.sendLocalImage(
                    img_path,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    message=Message(text=line.upper()),
                    ttl=120000
                )
            except Exception as e:
                print(f"Lỗi gửi: {e}")
            time.sleep(delay_time)

def stop_war(client, message_object, thread_id, thread_type):
    global running_groups
    running_groups = [g for g in running_groups if g["thread_id"] != thread_id]
    save_running_groups(running_groups)
    client.replyMessage(Message(text="🐧 WAR ĐÃ DỪNG."), message_object, thread_id, thread_type, ttl=60000)

# --- Command Handler ---
def handle_war_command(message, message_object, thread_id, thread_type, author_id, client):
    global delay_time, running_groups

    if author_id not in ADMIN:
        client.replyMessage(Message(text="🚫 Bạn không có quyền dùng lệnh này."),
                            message_object, thread_id, thread_type, ttl=60000)
        return

    parts = message.strip().split()
    if len(parts) < 2:
        client.replyMessage(Message(text="⚙️ Dùng: treoanh on / stop / set / text / info / img [link hoặc reply ảnh]"),
                            message_object, thread_id, thread_type, ttl=60000)
        return

    action = parts[1].lower()
    args = parts[2:]

    # --- SET DELAY ---
    if action == "set":
        if len(args) < 1 or not args[0].isdigit():
            client.replyMessage(Message(text="❗ Cú pháp: treoanh set <số giây>"),
                                message_object, thread_id, thread_type, ttl=60000)
            return
        delay_time = int(args[0])
        client.replyMessage(Message(text=f"✅ Delay mỗi lần gửi: {delay_time}s."),
                            message_object, thread_id, thread_type, ttl=60000)
        return

    # --- TEXT COMMAND ---
    if action == "text":
        if len(args) < 1:
            client.replyMessage(Message(text="❗ Cú pháp: treoanh text <số_lượng_câu> hoặc treoanh text <nội_dung_tự_nhập>"),
                                message_object, thread_id, thread_type, ttl=60000)
            return

        # Xoá file cũ nếu có
        if os.path.exists("onetag.txt"):
            try:
                os.remove("onetag.txt")
                print("🗑️ Đã xoá file onetag.txt cũ.")
            except Exception as e:
                print(f"[treoanh text] Lỗi khi xoá file cũ: {e}")

        # Nếu nhập số → random câu
        if args[0].isdigit():
            num_sentences = int(args[0])
            with open("onetag.txt", "w", encoding="utf-8") as f:
                for _ in range(num_sentences):
                    f.write(make_sentence() + "\n")
            client.replyMessage(Message(text=f"✅ Đã tạo {num_sentences} câu ngẫu nhiên trong file."),
                                message_object, thread_id, thread_type, ttl=60000)
            return

        # Nếu nhập text → lưu nội dung tùy chỉnh
        user_text = " ".join(args)
        with open("onetag.txt", "w", encoding="utf-8") as f:
            f.write(user_text.strip() + "\n")

        client.replyMessage(Message(text=f"✅ Đã lưu nội dung tùy chỉnh vào file:\n“{user_text.strip()}”"),
                            message_object, thread_id, thread_type, ttl=60000)
        return

    # --- INFO ---
    if action == "info":
        status = "🟢 Đang chạy" if any(g["thread_id"] == thread_id for g in running_groups) else "🔴 Đang tắt"
        num_sentences = 0
        if os.path.exists("onetag.txt"):
            with open("onetag.txt", "r", encoding="utf-8") as f:
                num_sentences = len([line for line in f if line.strip()])
        img_count = len([f for f in os.listdir(IMAGE_DIR) if f.endswith(".jpg")]) if os.path.exists(IMAGE_DIR) else 0
        info_text = (
            f"📊 Thông tin WAR:\n"
            f"• Trạng thái: {status}\n"
            f"• Delay: {delay_time}s\n"
            f"• Câu trong file war: {num_sentences}\n"
            f"• Ảnh trong bộ WAR: {img_count}"
        )
        client.replyMessage(Message(text=info_text),
                            message_object, thread_id, thread_type, ttl=60000)
        return

    # --- IMG ---
    if action == "img":
        image_url = args[0] if len(args) >= 1 else extract_reply_image_url(message_object)
        if not image_url:
            client.replyMessage(Message(text="❌ Vui lòng nhập link hoặc reply 1 ảnh."),
                                message_object, thread_id, thread_type, ttl=60000)
            return
        ok, msg = process_image_pipeline(image_url)
        client.replyMessage(Message(text=msg),
                            message_object, thread_id, thread_type, ttl=60000)
        return

    # --- STOP ---
    if action == "stop":
        if not any(g["thread_id"] == thread_id for g in running_groups):
            client.replyMessage(Message(text="⚠️ Hiện không có WAR nào đang chạy."),
                                message_object, thread_id, thread_type, ttl=60000)
        else:
            stop_war(client, message_object, thread_id, thread_type)
        return

    # --- ON ---
    if action == "on":
        if not os.path.exists("onetag.txt"):
            client.replyMessage(Message(text="❌ Không tìm thấy onetag.txt."),
                                message_object, thread_id, thread_type, ttl=60000)
            return
        if not os.path.exists(IMAGE_DIR) or not os.listdir(IMAGE_DIR):
            client.replyMessage(Message(text=f"⚠️ Chưa có ảnh trong thư mục {IMAGE_DIR}. Dùng treoanh img để thêm."),
                                message_object, thread_id, thread_type, ttl=60000)
            return

        # Xoá nhóm cũ, tạo mới nhóm hiện tại
        running_groups.clear()
        running_groups.append({"thread_id": thread_id, "thread_type": str(thread_type)})
        save_running_groups(running_groups)

        client.replyMessage(Message(text=f"🔥 Bắt đầu WAR ảnh (random) với delay {delay_time}s..."),
                            message_object, thread_id, thread_type, ttl=60000)
        threading.Thread(target=war_loop, args=(client, thread_id, thread_type)).start()
        return

    # --- Mặc định ---
    client.replyMessage(
        Message(text="⚙️ Dùng: treoanh on / stop / set / text / info / img [link hoặc reply ảnh]"),
        message_object, thread_id, thread_type, ttl=60000
    )

# --- Auto restart WAR cho nhóm cũ ---
def auto_restart_war(client):
    print("[AUTO WAR ẢNH] Bắt đầu WAR ẢNH cho các nhóm cũ...")
    for g in running_groups.copy():
        thread_type_obj = ThreadType[g["thread_type"].split(".")[-1]]
        threading.Thread(target=war_loop, args=(client, g["thread_id"], thread_type_obj)).start()

# --- Export ---
def TQD():
    return {'treoanh': handle_war_command}
