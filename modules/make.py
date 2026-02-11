from zlapi.models import Message, Mention
import os
import requests
from PIL import Image
import uuid
from config import PREFIX

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Vẽ ảnh theo yêu cầu",
    'power': "Thành viên"
}

def handle_make_command(message, message_object, thread_id, thread_type, author_id, client):
    content = " ".join(message.strip().split()[1:]).strip()
    if not content:
        response_message = f"Vui lòng nhập nội dung để vẽ ảnh (ví dụ: {PREFIX}make một con mèo đáng yêu)"
        message_to_send = Message(text=response_message)
        client.replyMessage(message_to_send, message_object, thread_id, thread_type)
        return

    try:
        image_url = f"https://image.pollinations.ai/prompt/{content}"
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        image_name = f"{uuid.uuid4()}.jpg"
        image_path = os.path.join(os.getcwd(), image_name)
        with open(image_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        img = Image.open(image_path)
        width, height = img.size
        client.sendLocalImage(image_path, thread_id=thread_id, thread_type=thread_type, message=Message(text=f"[@Member] [{content}]", mention=Mention(author_id, length=len("@Member"), offset=1)), width=width, height=height, ttl=86400000)
        os.remove(image_path)
    except requests.exceptions.RequestException as e:
        response_message = f"Lỗi khi tạo ảnh: {e}"
        message_to_send = Message(text=response_message)
        client.replyMessage(message_to_send, message_object, thread_id, thread_type)
    except Exception as e:
        response_message = f"Lỗi không xác định: {e}"
        message_to_send = Message(text=response_message)
        client.replyMessage(message_to_send, message_object, thread_id, thread_type)

def TQD():
    return {
        'make': handle_make_command
    }