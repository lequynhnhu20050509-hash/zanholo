import requests
import os
from zlapi.models import Message, Mention
import logging
import datetime
import time

GEMINI_API_KEY = "AIzaSyCdcXwfWBzg492rooDiIC7XJvaBy7S4JUM"

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Tạo caption TikTok",
    'power': "Thành viên"
}

def handle_caption_command(message, message_object, thread_id, thread_type, author_id, client):
    user_input = " ".join(message.strip().split()[1:]).strip()
    if not user_input:
        client.replyMessage(
            Message(text="Nhập nội dung để tui tạo caption TikTok nè!"),
            message_object, thread_id, thread_type, ttl=12000
        )
        return

    caption_response = get_caption_response(user_input)

    if caption_response:
        client.replyMessage(
            Message(
                text=f"@Member {caption_response}",
                mention=Mention(author_id, length=len("@Member"), offset=0)
            ),
            message_object, thread_id, thread_type, ttl=1800000
        )
    else:
        client.replyMessage(
            Message(
                text="Hic, tui chưa tìm được cảm hứng, thử lại nha! :(",
                mention=Mention(author_id, length=len("@Member"), offset=0)
            ),
            message_object, thread_id, thread_type, ttl=1800000
        )

def get_caption_response(user_input, max_retries=3):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    prompt = (
        f"Bạn là một nhà thơ và người kể chuyện TikTok, được tạo bởi Dương , hiện tại là {current_time}. "
        f"Nhiệm vụ: Tạo một caption TikTok tự sự, cảm xúc, sâu lắng (dưới 60 ký tự) cho video '{user_input}'. "
        f"Yêu cầu: \n"
        f"- Bắt chước phong cách, giọng điệu, và cấu trúc tự sự của các ví dụ sau: \n"
        f"  1. 'Con từng là người sống rất coi trọng tình cảm nhưng bây giờ con chỉ quan tâm tới Tiền, vì những ngày tháng con không có tiền họ đối xử tệ với con quá...' \n"
        f"  2. 'Có người vì buồn mới nhớ em. Có người vì nhớ em mới buồn...' \n"
        f"  3. 'Khi ai đó không yêu em theo cách em muốn, không có nghĩa là họ không thực sự yêu em...' \n"
        f"  4. 'Cho đến khi mình giật mình vào nửa đêm và khóc như một đứa trẻ, lúc ấy mình đã hiểu trái tim này đã thật sự quá tải rồi.' \n"
        f"- Tạo caption dạng văn ngắn (1-2 câu) hoặc thơ ngắn (2-3 dòng, tối đa 30 ký tự), phản ánh trải nghiệm cá nhân, sự thay đổi cảm xúc, hoặc nhận ra chân lý. \n"
        f"- Sử dụng ngôn ngữ đời thường, tinh tế, gần gũi Gen Z, không dùng emoji, không dùng hashtag. \n"
        f"- Tránh các cụm từ sáo rỗng như 'lạnh lẽo', 'vắng tanh', 'trái tim đau', 'một mình', 'mưa rơi'. \n"
        f"- Đảm bảo caption độc đáo, cảm xúc mãnh liệt, dễ gây đồng cảm, tăng khả năng viral. \n"
        f"- Không dùng lịch sử trò chuyện, mỗi caption phải hoàn toàn mới. \n"
        f"- Lấy cảm hứng từ nhạc buồn TikTok và câu chuyện Gen Z để tăng sự chân thật. \n"
        f"User: {user_input}\n"
        f"> "
    )

    data = {"contents": [{"parts": [{"text": prompt}]}]}

    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()

            if 'candidates' in result and result['candidates']:
                for candidate in result['candidates']:
                    if 'content' in candidate and 'parts' in candidate['content']:
                        for part in candidate['content']['parts']:
                            if 'text' in part:
                                return part['text']
            else:
                logging.error(f"Gemini response is empty or doesn't contain valid 'candidates'. Response: {result}")
                return None
            logging.error(f"Gemini response doesn't have valid text. Response: {result}")
            return None

        except requests.exceptions.RequestException as e:
            status_code = response.status_code if 'response' in locals() else 'N/A'
            logging.error(f"Request Exception (Attempt {attempt + 1}): {e}, Status Code: {status_code}, Response: {response.text if 'response' in locals() else 'N/A'}")
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return None
        except Exception as e:
            logging.error(f"General Exception (Attempt {attempt + 1}): {e}")
            return None

def TQD():
    return {
        'caption': handle_caption_command
    }