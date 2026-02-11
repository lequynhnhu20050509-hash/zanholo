from zlapi.models import *
import requests
import random
import os
import json
from PIL import Image

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Gửi ảnh gái",
    'power': "Thành viên"
}


def handle_girl_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Đường dẫn file chứa danh sách ảnh
        image_list_path = "modules/cache/anhgai.json"

        if not os.path.exists(image_list_path):
            raise Exception("Không tìm thấy file ảnh (anhgai.json)")

        # Đọc danh sách ảnh từ file JSON
        with open(image_list_path, "r", encoding="utf-8") as f:
            image_urls = json.load(f)

        if not isinstance(image_urls, list) or not image_urls:
            raise Exception("Danh sách ảnh rỗng hoặc không hợp lệ")

        # Chọn ngẫu nhiên 1 ảnh
        image_url = random.choice(image_urls)

        headers = {
            'User-Agent': 'Mozilla/5.0'
        }

        # Tải ảnh
        image_response = requests.get(image_url, headers=headers, timeout=10)
        image_response.raise_for_status()

        # Lưu tạm
        temp_image_path = "modules/cache/temp_image1.jpeg"
        with open(temp_image_path, "wb") as f:
            f.write(image_response.content)

        # 📌 Lấy kích thước ảnh thật
        try:
            with Image.open(temp_image_path) as img:
                w, h = img.size
        except:
            w, h = 1200, 1600  # fallback nếu ảnh lỗi

        # Gửi ảnh
        if os.path.exists(temp_image_path):
            print(f"[GIRL] Ảnh được gửi: {image_url} | Kích thước: {w}x{h}")

            client.sendLocalImage(
                temp_image_path,
                thread_id=thread_id,
                thread_type=thread_type,
                ttl=60000*2,
                width=w,
                height=h
            )

            os.remove(temp_image_path)
        else:
            raise Exception("Không thể lưu ảnh tạm")

    except Exception as e:
        client.sendMessage(Message(text=f"Đã xảy ra lỗi: {str(e)}"), thread_id, thread_type)



def TQD():
    return {
        'girl': handle_girl_command
    }
