from zlapi.models import Message
import json
import urllib.parse
import os
import requests
from gtts import gTTS

des = {
    'version': "1.0.2",
    'credits': "Latte",
    'description': "Chuyển đổi văn bản thành voice",
    'power': "Thành viên"
}

def convert_text_to_aac(text):
    try:
        tts = gTTS(text=text, lang='vi')
        aac_file = 'NGSONVOICE.aac'
        tts.save(aac_file)
        return aac_file
    except Exception as e:
        print(f"Lỗi {str(e)}")
        return None

def upload_to_host(file_name):
    try:
        with open(file_name, 'rb') as file:
            files = {'files[]': file}
            response = requests.post('https://uguu.se/upload', files=files).json()
            if response['success']:
                return response['files'][0]['url']
            return False
    except Exception as e:
        print(f"Error in upload_to_host: {e}")
        return False

def handle_voice_command(message, message_object, thread_id, thread_type, author_id, client):
    content = message_object.content.strip()
    command_parts = content.split(maxsplit=1)
    text = command_parts[1].strip() if len(command_parts) > 1 else ""

    if not text:
        send_error_message(thread_id, thread_type, client, "Vui lòng nhập nội dung.")
        return

    aac_file = convert_text_to_aac(text)
    if aac_file:
        voice_url = upload_to_host(aac_file)
        if voice_url:
            file_size = os.path.getsize(aac_file)
            client.sendRemoteVoice(voice_url, thread_id, thread_type, fileSize=file_size)
        else:
            send_error_message(thread_id, thread_type, client, "Không thể tải âm thanh.")
    else:
        send_error_message(thread_id, thread_type, client, "Không thể tạo voice.")

def send_error_message(thread_id, thread_type, client, error_message="lỗi."):
    client.send(Message(text=error_message), thread_id=thread_id, thread_type=thread_type)

def process_message(message_object, thread_id, thread_type, author_id, client):
    content = message_object.content.strip()
    command_parts = content.split(maxsplit=1)
    command = command_parts[0].lower()
    commands = get_xbzl()
    
    if command in commands:
        commands[command](message_object, thread_id, thread_type, author_id, client)
    else:
        send_error_message(thread_id, thread_type, client, "Lệnh không hợp lệ.")

def TQD():
    return {
        'voice': handle_voice_command
    }