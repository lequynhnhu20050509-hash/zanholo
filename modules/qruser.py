import os
import requests
from zlapi.models import Message, Mention

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Lấy QR code zalo người dùng hoặc người được tag",
    'power': "Thành viên"
}

def handle_qruser_command(message, message_object, thread_id, thread_type, author_id, client):
    mentions = message_object.mentions
    target_id = mentions[0]['uid'] if mentions else author_id
    qr_data = client.getQRLink(target_id)

    if qr_data:
        qr_url = qr_data.get(str(target_id), "")
        if qr_url:
            img_path = "qr_code.jpg"
            try:
                # Tải ảnh QR
                response = requests.get(qr_url, stream=True, timeout=10)
                response.raise_for_status()
                with open(img_path, "wb") as file:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)

                # Gửi ảnh QR
                client.sendLocalImage(
                    img_path,
                    message=Message(
                        text="@Member Đây là mã QR code",
                        mention=Mention(author_id, length=len("@Member"), offset=0)
                    ),
                    thread_id=thread_id,
                    thread_type=thread_type
                )

            except requests.exceptions.RequestException as e:
                client.sendMessage(Message(text=f"Lỗi tải ảnh QR: {e}"), thread_id=thread_id, thread_type=thread_type)

            except Exception as e:
                client.sendMessage(Message(text=f"Lỗi không xác định: {e}"), thread_id=thread_id, thread_type=thread_type)

            finally:
                # Dù có lỗi hay không vẫn xóa file
                if os.path.exists(img_path):
                    try:
                        os.remove(img_path)
                    except Exception as e:
                        client.sendMessage(Message(text=f"Lỗi khi xóa file tạm: {e}"), thread_id=thread_id, thread_type=thread_type)

        else:
            client.sendMessage(Message(text="Không tìm thấy URL ảnh QR."), thread_id=thread_id, thread_type=thread_type)
    else:
        client.sendMessage(Message(text="Không thể lấy mã QR của người dùng."), thread_id=thread_id, thread_type=thread_type)


def TQD():
    return {
        'qruser': handle_qruser_command
    }
