import time
import requests
import urllib.parse
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from zlapi.models import *
from config import PREFIX

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Tìm ảnh Pinterest",
    'power': "Thành viên"
}

# Style màu xanh và in đậm
success_styles = MultiMsgStyle([
    MessageStyle(offset=0, length=10000, style="color", color="#15a85f", auto_format=False),
    MessageStyle(offset=0, length=10000, style="font", size="8", auto_format=False),
    MessageStyle(offset=0, length=10000, style="bold", size="8", auto_format=False)
])

def download_image(url, index):
    """Hàm tải ảnh từ URL và lưu vào file tạm."""
    try:
        img = requests.get(url, timeout=10)
        img.raise_for_status()
        path = f"modules/cache/pin_{index}_{int(time.time())}.jpg"
        with open(path, "wb") as f:
            f.write(img.content)
        return path
    except Exception:
        return None

def get_pinterest_images(query, limit=5):
    encoded_query = urllib.parse.quote(query)
    search_url = "https://www.pinterest.com/resource/BaseSearchResource/get/"
    
    data = {
        "options": {
            "query": query,
            "page_size": limit,
            "scope": "pins",
            "rs": "typed",
            "redux_normalize_feed": True,
            "source_url": f"/search/pins/?q={encoded_query}&rs=typed",
        },
        "context": {}
    }

    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://www.pinterest.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "x-app-version": "9237374",
        "x-pinterest-appstate": "active",
        "x-pinterest-pws-handler": "www/search/[scope].js",
        "x-pinterest-source-url": f"/search/pins/?q={encoded_query}&rs=typed",
        "x-requested-with": "XMLHttpRequest",
    }

    params = {
        "source_url": f"/search/pins/?q={encoded_query}&rs=typed",
        "data": json.dumps(data),
        "_": int(time.time() * 1000),
    }

    response = requests.get(search_url, headers=headers, params=params, timeout=15)
    response.raise_for_status()

    res_json = response.json()
    results = res_json.get("resource_response", {}).get("data", {}).get("results", [])
    image_urls = []

    for pin in results:
        if not pin or not pin.get("images"):
            continue
        img = pin["images"]
        url = (
            img.get("orig", {}).get("url")
            or img.get("1200x", {}).get("url")
            or img.get("736x", {}).get("url")
            or img.get("600x", {}).get("url")
            or img.get("474x", {}).get("url")
        )
        if url and url not in image_urls:
            image_urls.append(url)
        if len(image_urls) >= limit:
            break

    return image_urls

def handle_pin_command(message, message_object, thread_id, thread_type, author_id, client):
    text = message.strip().split()

    if len(text) < 2:
        msg = Message(text=f"❌ Cú pháp sai.\nVí dụ: {PREFIX}pin mèo hoặc {PREFIX}pin mèo 10 ✅")
        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=30000)
        return

    num_images = 5
    if text[-1].isdigit():
        num_images = int(text[-1])
        query = " ".join(text[1:-1])
    else:
        query = " ".join(text[1:])

    if not (1 <= num_images <= 15):
        msg = Message(text="❌ Số lượng ảnh phải nằm trong khoảng 1 - 15.")
        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=30000)
        return

    if not query.strip():
        msg = Message(text="❌ Vui lòng nhập từ khóa tìm kiếm ảnh.")
        client.replyMessage(msg, message_object, thread_id, thread_type, ttl=30000)
        return

    try:
        client.sendReaction(message_object, "⏳", thread_id, thread_type, reactionType=75)
        urls = get_pinterest_images(query, num_images)

        if not urls:
            msg = Message(text=f"Không tìm thấy ảnh nào cho '{query}'. 🚫")
            client.sendMessage(msg, thread_id, thread_type, ttl=30000)
            return

        os.makedirs("modules/cache", exist_ok=True)
        image_paths = []

        # Tải ảnh song song
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(download_image, url, i): url for i, url in enumerate(urls)}
            for future in as_completed(future_to_url):
                path = future.result()
                if path:
                    image_paths.append(path)

        if not image_paths:
            msg = Message(text="❌ Không thể tải ảnh nào.")
            client.sendMessage(msg, thread_id, thread_type, ttl=30000)
            return

        # --- Lấy username người dùng từ author_id ---
        try:
            user_info = client.fetchUserInfo(author_id)
            username = user_info.changed_profiles.get(author_id, {}).get('zaloName', 'không xác định')
        except:
            username = "bạn"

        # --- Tạo message tag người dùng ---
        tag = f"@{username} "
        message_content = f"{tag} 👉 Đây là kết quả tìm kiếm ảnh với từ khóa: [{query}]"

        offset = message_content.index(tag)
        length = len(tag) 
        
        msg_intro = Message(
            text=message_content,                        
            mention=Mention(author_id, length=length, offset=offset),
            style=success_styles
        )

        client.replyMessage(
                                 msg_intro,
                                 message_object,
                                 thread_id,
                                 thread_type,
                                 ttl=60000*10
                             )                 
       
        # Gửi ảnh
        client.sendMultiLocalImage(
            imagePathList=image_paths,            
            thread_id=thread_id,
            thread_type=thread_type,
            width=1600,
            height=1600,
            ttl=60000*10
        )

    except requests.exceptions.RequestException as e:
        msg = Message(text=f"⚠️ Lỗi khi gọi Pinterest: {str(e)}")
        client.sendMessage(msg, thread_id, thread_type, ttl=30000)
    except Exception as e:
        msg = Message(text=f"⚠️ Lỗi không xác định: {str(e)}")
        client.sendMessage(msg, thread_id, thread_type, ttl=30000)
    finally:
        # Xóa ảnh song song
        def delete_file(path):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(delete_file, image_paths)

def TQD():
    return {
        'pin': handle_pin_command
    }
