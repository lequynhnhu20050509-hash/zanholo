from zlapi.models import Message
import time
import os
import requests

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Chụp ảnh trang web (cap web)",
    "power": "Thành viên",
}

def handle_cap_command(message, message_object, thread_id, thread_type, author_id, client):
    content = message.strip().split()

    if len(content) < 2:
        error_message = Message(text="🚨 Lỗi: Vui lòng nhập link cần cap. Hãy thử lại nhé! 🔍")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return

    url_to_capture = content[1].strip()

    # 🔧 Tự động thêm https:// nếu thiếu
    if not url_to_capture.startswith("http://") and not url_to_capture.startswith("https://"):
        url_to_capture = "https://" + url_to_capture

    if not validate_url(url_to_capture):
        error_message = Message(text="❌ Lỗi: Link không hợp lệ! Hãy nhập một URL hợp lệ nhé! 🌐")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=60000)
        return

    try:
        capture_url = f"https://image.thum.io/get/width/1920/crop/400/fullpage/noanimate/{url_to_capture}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }

        image_response = requests.get(capture_url, headers=headers)
        image_response.raise_for_status()
        
        # 🖼️ Lưu ảnh tạm
        image_path = 'modules/cache/temp_image9.jpeg'
        with open(image_path, 'wb') as f:
            f.write(image_response.content)

        success_message = f"🎉 Thành công: Đã chụp trang web 🖼️: {url_to_capture} ✅"
        message_to_send = Message(text=success_message)
        client.sendLocalImage(
            image_path,
            message=message_to_send,
            thread_id=thread_id,
            thread_type=thread_type,
            ttl=60000
        )

        os.remove(image_path)

    except requests.exceptions.RequestException as e:
        error_message = Message(text=f"❌ Lỗi khi gọi API: {str(e)} 🚫. Vui lòng thử lại sau.")
        client.sendMessage(error_message, thread_id, thread_type, ttl=60000)
    except Exception as e:
        error_message = Message(text=f"⚠️ Lỗi hệ thống: {str(e)}. Hãy thử lại nhé! 🔧")
        client.sendMessage(error_message, thread_id, thread_type, ttl=60000)


def validate_url(url):
    """Kiểm tra xem URL có hợp lệ không."""
    parsed = requests.utils.urlparse(url)
    return parsed.scheme in ('http', 'https') and parsed.netloc != ''


def TQD():
    return {
        'cap': handle_cap_command
    }
