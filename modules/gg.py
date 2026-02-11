import os
import tempfile
import requests
from zlapi.models import Message, ZaloAPIException, MultiMsgStyle, MessageStyle
from config import ADMIN, IMEI
from serpapi import GoogleSearch
from config import PREFIX

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Lệnh tìm kiếm thông tin trên Google",
    'power': "Thành Viên"
}

API_KEY = "d8a6a73837b09b219a7092f62d1fd9d59c9e2274e8770fd0e0037b31717ff290"

SEARCH_CACHE = {}  

def send_message(client, text, message_object, thread_id, thread_type, ttl=86400000):
    styles = MultiMsgStyle([
         MessageStyle(offset=0, length=10000, style="color", color="#15a85f", auto_format=False),
         MessageStyle(offset=0, length=10000, style="font", size="8", auto_format=False),
         MessageStyle(offset=0, length=10000, style="bold", auto_format=False)
    ])
    client.replyMessage(
        Message(text=text, style=styles),
        message_object,
        thread_id,
        thread_type,
        ttl=ttl
    )

def send_image(client, url, message_object, thread_id, thread_type, ttl=86400000):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            print(f"⚠️ Không tải được ảnh từ: {url}")
            return
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(r.content)
            tmp_path = tmp.name

        client.sendLocalImage(
            imagePath=tmp_path,
            thread_id=thread_id,
            thread_type=thread_type,
            message=Message(text=""),
            ttl=ttl
        )
        os.remove(tmp_path)
    except Exception as e:
        print(f"⚠️ Không gửi được ảnh: {e}")

def handle_search_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        send_message(client, "❌ Bạn không có quyền sử dụng lệnh này!",
                     message_object, thread_id, thread_type, ttl=60000)
        return

    try:
        parts = message.split(" ", 2)
        if len(parts) < 2:
            send_message(client, "⚠️ Nhập từ khóa tìm kiếm!\nVí dụ: ,gg mèo dễ thương",
                         message_object, thread_id, thread_type)
            return

        if parts[1] == "down":
            if thread_id not in SEARCH_CACHE:
                send_message(client, "⚠️ Bạn chưa tìm kiếm gì để tải chi tiết.", message_object, thread_id, thread_type)
                return

            if len(parts) < 3 or not parts[2].isdigit():
                send_message(client, "⚠️ Vui lòng nhập số thứ tự kết quả.\nVí dụ: ,gg down 2",
                             message_object, thread_id, thread_type)
                return

            idx = int(parts[2]) - 1
            results = SEARCH_CACHE[thread_id]

            if idx < 0 or idx >= len(results):
                send_message(client, f"⚠️ Chỉ có {len(results)} kết quả trong cache.",
                             message_object, thread_id, thread_type)
                return

            item = results[idx]

            title = item.get("title", "Không có tiêu đề")
            link = item.get("link", "Không có link")
            snippet = item.get("snippet", "Không có mô tả")
            displayed_link = item.get("displayed_link", "")
            source = item.get("source", "")
            date = item.get("date", "")
            pos = item.get("position", "")
            extra = item.get("extra", {}) 
            msg = f"""📖 Chi tiết kết quả {idx+1}:

📝 Tiêu đề: {title}
🔗 Link: {link}
🌍 Hiển thị: {displayed_link}
🏷️ Nguồn: {source}
📅 Ngày: {date}
📌 Mô tả: {snippet}
📊 Thứ hạng Google: {pos}
"""

            for k, v in extra.items():
                msg += f"{k}: {v}\n"

            send_message(client, msg, message_object, thread_id, thread_type)
            return

        search_query = " ".join(parts[1:]).strip()
        search_results = search_google(search_query)

        if search_results:
            SEARCH_CACHE[thread_id] = search_results

            formatted_results = "\n".join(
                [f"{i+1}. {item.get('title','[Không tiêu đề]')}\n{item.get('link','')}\n"
                 for i, item in enumerate(search_results)]
            )
            msg = f"🔎 Kết quả tìm kiếm cho '{search_query}':\n\n{formatted_results}\n\n👉 Dùng {PREFIX}gg down <số> để xem chi tiết."
        else:
            msg = f"Không tìm thấy kết quả cho '{search_query}'."

        send_message(client, msg, message_object, thread_id, thread_type)

    except Exception as e:
        send_message(client, f"⚠️ Lỗi không xác định: {e}",
                     message_object, thread_id, thread_type)

def search_google(query):
    params = {
        "q": query,
        "hl": "vi",
        "gl": "vn",
        "google_domain": "google.com",
        "api_key": API_KEY
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
    except Exception as e:
        print(f"Lỗi gọi api: {e}")
        return None

    output = []
    for item in results.get("organic_results", [])[:7]:
        data = {
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet"),
            "thumbnail": item.get("thumbnail"),
            "favicon": item.get("favicon"),
            "displayed_link": item.get("displayed_link"),
            "source": item.get("source"),
            "date": item.get("date"),
            "position": item.get("position")
        }
        output.append(data)
    return output

def TQD():
    return {
        'gg': handle_search_command
    }
