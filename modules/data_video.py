from zlapi.models import Message
import json
import urllib.parse
import os
from config import ADMIN  # Import danh sách ADMIN từ config

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Lưu link hình/video file",
    'power': "Admin"
}

# ==== Biến toàn cục ====
pending_files = {}
pending_message_objects = {}

# ==== Lệnh chính ====
def handle_save_command(message, message_object, thread_id, thread_type, author_id, client):
    # Kiểm tra quyền admin
    if author_id not in ADMIN:
        client.send(Message(text="❌ Admin tao không cho dùng."), thread_id, thread_type, ttl=60000)
        return

    parts = message.strip().split()

    # ⚙️ Nếu chỉ nhập 'dt' -> lưu mặc định
    if len(parts) == 1:
        handle_default_save(message_object, thread_id, thread_type, author_id, client)
        return

    # ⚙️ Có thêm từ khóa -> tìm file trong modules/cache
    keyword = parts[1]
    base_folder = "modules/cache"
    file_list = []

    for root, dirs, files in os.walk(base_folder):
        for f in files:
            if f.lower().startswith(keyword.lower()):
                file_list.append(os.path.join(root, f))

    if not file_list:
        client.send(Message(text=f"⚠️ Không tìm thấy file nào bắt đầu với '{keyword}' trong '{base_folder}/'"),
                    thread_id, thread_type, ttl=60000)
        return

    # ⚙️ Nếu chỉ có 1 file -> lưu ngay
    if len(file_list) == 1:
        selected_file = file_list[0]
        link = extract_media_link(message_object)
        if link:
            save_link_to_file(link, selected_file)
            client.send(Message(text=f"✅ Đã lưu vào {os.path.basename(selected_file)}"),
                        thread_id, thread_type, ttl=60000)
        else:
            client.send(Message(text="❌ Không tìm thấy hình/video trong tin nhắn."), thread_id, thread_type, ttl=60000)
        return

    # ⚙️ Nếu nhiều file -> cho chọn
    file_options = "\n".join([f"{i+1}. {os.path.basename(f)}" for i, f in enumerate(file_list)])
    client.send(Message(
        text=f"📁 Các file tìm thấy:\n{file_options}\n\n➡️ Nhập số thứ tự để lưu link vào file tương ứng."
    ), thread_id, thread_type, ttl=60000)

    # Ghi nhớ message gốc để khi nhập số sẽ dùng link từ tin này
    pending_files[author_id] = file_list
    pending_message_objects[author_id] = message_object


# ==== Khi người dùng nhập số file ====
def handle_file_selection(message, thread_id, thread_type, author_id, client):
    # Kiểm tra quyền admin
    if author_id not in ADMIN:
        client.send(Message(text="❌ Bạn không có quyền sử dụng lệnh này! Chỉ admin mới được phép."), thread_id, thread_type, ttl=60000)
        return False

    if author_id not in pending_files or author_id not in pending_message_objects:
        return False

    choice = message.strip()
    if not choice.isdigit():
        client.send(Message(text="❌ Vui lòng nhập số hợp lệ!"), thread_id, thread_type, ttl=60000)
        return True

    index = int(choice) - 1
    file_list = pending_files[author_id]
    if index < 0 or index >= len(file_list):
        client.send(Message(text="⚠️ Số bạn chọn không tồn tại."), thread_id, thread_type, ttl=60000)
        return True

    selected_file = file_list[index]
    msg_obj = pending_message_objects[author_id]
    link = extract_media_link(msg_obj)

    if not link:
        client.send(Message(text="❌ Không tìm thấy hình/video trong tin nhắn trước đó."), thread_id, thread_type, ttl=60000)
        del pending_files[author_id]
        del pending_message_objects[author_id]
        return True

    save_link_to_file(link, selected_file)
    client.send(Message(text=f"✅ Đã lưu link vào {os.path.basename(selected_file)}"),
                thread_id, thread_type, ttl=60000)

    # Xóa trạng thái
    del pending_files[author_id]
    del pending_message_objects[author_id]
    return True


# ==== Lưu mặc định ====
def handle_default_save(message_object, thread_id, thread_type, author_id, client):
    # Kiểm tra quyền admin
    if author_id not in ADMIN:
        client.send(Message(text="❌ Bạn không có quyền sử dụng lệnh này! Chỉ admin mới được phép."), thread_id, thread_type, ttl=60000)
        return

    link = extract_media_link(message_object)
    if not link:
        client.send(Message(text="❌ Vui lòng reply hình ảnh, video hoặc file để lấy link."), thread_id, thread_type, ttl=60000)
        return
    os.makedirs("data", exist_ok=True)
    save_link_to_file(link, "data/vdgai.txt")
    client.send(Message(text="[✅ Đã lưu vào file vdgai.txt]"), thread_id, thread_type, ttl=60000)


# ==== Tách link từ tin nhắn ====
def extract_media_link(msg_obj):
    try:
        if msg_obj.msgType == "chat.photo":
            return urllib.parse.unquote(msg_obj.content.href.replace("\\/", "/"))
        elif msg_obj.quote and msg_obj.quote.attach:
            attach_data = json.loads(msg_obj.quote.attach)
            return attach_data.get('hdUrl') or attach_data.get('href')
    except:
        return None
    return None


# ==== Lưu link vào file ====
def save_link_to_file(link, file_path):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if file_path.endswith(".json"):
            data = []
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except:
                    data = []
            data.append(link)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        else:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(link + "\n")
        print(f"Đã lưu link: {link} vào {file_path}")
    except Exception as e:
        print(f"Lỗi khi lưu link: {str(e)}")


# ==== Đăng ký lệnh ====
def TQD():
    return {
        "dt": handle_save_command
    }