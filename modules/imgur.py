import requests
from zlapi.models import Message, ThreadType
import json
import urllib.parse
import ffmpeg
import os

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Upload ảnh hoặc video lêm imgur",
    'power': "Thành viên"
}


PROXY_API = "https://keyherlyswar.x10.mx/Apidocs/imgur.php?url="

def handle_upload_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
               
        
        if hasattr(message_object, 'msgType') and message_object.msgType in ["chat.photo", "chat.video"]:
            media_url = message_object.content.get('href', '').replace("\\/", "/")
            if not media_url:
                return send_error_message("❌ Không tìm thấy liên kết ảnh/video.", thread_id, thread_type, client, ttl=60000)

            print(f"📤 Đang upload {message_object.msgType} từ: {media_url}")
            imgur_link = upload_to_imgur(media_url)
            if not imgur_link:
                return send_error_message("⚠️ Lỗi khi upload ảnh/video lên Imgur.", thread_id, thread_type, client, ttl=60000)

            print(f"✅ Upload thành công → {imgur_link}")
            handle_media_send(client, imgur_link, thread_id, thread_type)
            return

  
        elif getattr(message_object, 'quote', None):
            attach = getattr(message_object.quote, 'attach', None)
            if not attach:
                return send_error_message("❌ Không có file đính kèm.", thread_id, thread_type, client, ttl=60000)

            try:
                attach_data = json.loads(attach)
            except json.JSONDecodeError:
                return send_error_message("❌ Lỗi phân tích JSON của file đính kèm.", thread_id, thread_type, client, ttl)

            media_url = attach_data.get('hdUrl') or attach_data.get('href')
            if not media_url:
                return send_error_message("❌ Không tìm thấy URL trong file đính kèm.", thread_id, thread_type, client, ttl=60000)

            print(f"📤 Đang upload file từ phản hồi: {media_url}")
            imgur_link = upload_to_imgur(media_url)
            if not imgur_link:
                return send_error_message("⚠️ Lỗi upload qua proxy.", thread_id, thread_type, client, ttl=60000)

            print(f"✅ Upload phản hồi thành công → {imgur_link}")
            handle_media_send(client, imgur_link, thread_id, thread_type)
            return

        # Nếu không có gì để upload
        else:
            send_error_message("📸 Gửi ảnh/video hoặc phản hồi tin có file để upload.", thread_id, thread_type, client, ttl=60000)

    except Exception as e:
        print(f"[LỖI] Khi xử lý upload: {e}")
        send_error_message("⚠️ Đã xảy ra lỗi khi xử lý lệnh upload.", thread_id, thread_type, client, ttl=60000)



def handle_media_send(client, media_link, thread_id, thread_type):
    """Tự động gửi lại ảnh hoặc video sau khi upload thành công"""
    try:
        if media_link.endswith(".mp4"):
            # Video
            try:
                duration, width, height = get_video_info(media_link)
            except Exception as e:
                print(f"⚠️ Không lấy được thông tin video: {e}")
                duration, width, height = 15000, 720, 1280  # fallback

            print(f"🎬 Gửi video {width}x{height}, {duration:.0f}ms → {media_link}")
            
            client.sendRemoteVideo(
                media_link,
                media_link,
                duration=duration,
                message=Message(text="🎬 Video đã upload thành công!"),
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=60000 * 2
            )
        else:
            
            print(f"🖼 Gửi ảnh: {media_link}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
            }

    
            image_response = requests.get(media_link, headers=headers, timeout=10)
            image_response.raise_for_status()

            
            temp_image_path = "modules/cache/temp_image1.jpeg"
            with open(temp_image_path, "wb") as f:
                f.write(image_response.content)

     
            if os.path.exists(temp_image_path):                
                print(f"Ảnh được gửi: {media_link}")
                client.sendLocalImage(
                    temp_image_path,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    ttl=60000 * 2,
                    width=1200,
                    height=1600
                )
                os.remove(temp_image_path)
    except Exception as e:
        print(f"❌ Lỗi khi gửi media: {e}")
        send_error_message("⚠️ Lỗi khi gửi ảnh/video sau khi upload.", thread_id, thread_type, client, ttl=60000)


def upload_to_imgur(media_url):
    """Gọi proxy upload ảnh/video lên Imgur"""
    try:
        encoded_url = urllib.parse.quote(media_url, safe='')
        proxy_url = f"{PROXY_API}{encoded_url}"
        response = requests.get(proxy_url, timeout=20)

        if response.status_code != 200:
            print(f"❌ Proxy lỗi {response.status_code}: {response.text}")
            return None

        result = response.json()
        print(f"📡 Proxy phản hồi: {result}")

        link = result.get('data', {}).get('link')
        if not link:
            print("⚠️ Proxy không trả về link hợp lệ.")
        else:
            print(f"✅ Link Imgur nhận được: {link}")
        return link
    except Exception as e:
        print(f"❌ Lỗi khi gọi API proxy: {e}")
        return None


def get_video_info(video_url):
    """Lấy thông tin video từ URL bằng ffmpeg."""
    print(f"🔍 Đang lấy thông tin video từ: {video_url}")
    try:
        probe = ffmpeg.probe(video_url)
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        if not video_stream:
            raise ValueError("Không tìm thấy luồng video!")

        duration = float(video_stream.get('duration', 0)) * 1000
        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
        print(f"📏 Video info → duration: {duration:.0f}ms, size: {width}x{height}")
        return duration, width, height
    except ffmpeg.Error as e:
        err = e.stderr.decode('utf-8') if e.stderr else str(e)
        print(f"❌ Lỗi FFmpeg: {err}")
        raise
    except Exception as e:
        print(f"❌ Lỗi khi lấy thông tin video: {str(e)}")
        raise



def send_success_message(message, thread_id, thread_type, client, ttl=60000):
    print(f"✅ Gửi tin nhắn thành công: {message}")
    try:
        client.send(Message(text=message), thread_id, thread_type, ttl=ttl)
    except Exception as e:
        print(f"⚠️ Lỗi khi gửi tin nhắn thành công: {str(e)}")


def send_error_message(message, thread_id, thread_type, client, ttl=60000):
    print(f"❗ Gửi tin nhắn lỗi: {message}")
    try:
        client.send(Message(text=message), thread_id, thread_type, ttl=ttl)
    except Exception as e:
        print(f"⚠️ Lỗi khi gửi tin nhắn lỗi: {str(e)}")

def TQD():
    return {
        'imgur': handle_upload_command
    }
