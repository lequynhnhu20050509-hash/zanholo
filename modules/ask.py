import requests
import logging
import datetime
import random
from zlapi.models import Message, Mention

des = {
    'version': "3.0.0",
    'credits': "Dương",
    'description': "Vợ ảo Simsimi (đa ngôn ngữ + DTW dễ thương)",
    'power': "Thành viên"
}

SIMSIMI_API_KEY = "GZyOSYF-1Pr5bDnMZ-ng2bNQVbkvtH1OeJyNBjoi"
SIMSIMI_API_URL = "https://wsapi.simsimi.com/190410/talk"
conversation_states = {}

# --- Bộ lọc dễ thương (DTW) ---
cute_suffixes = ["🥰", "😊", "❤️", "hihi", "nè", "anh ơi", "😚", "🙈", "💖"]

def make_cute(text: str) -> str:
    """Thêm chút dễ thương vào câu trả lời"""
    suffix = random.choice(cute_suffixes)
    return f"{text.strip()} {suffix}"

# --- Ngôn ngữ tự động ---
def detect_language(text: str) -> str:
    vietnamese_chars = "ăâđêôơưáàảãạéèẻẽẹíìỉĩịóòỏõọúùủũụýỳỷỹỵ"
    if any(ch in text.lower() for ch in vietnamese_chars):
        return "vn"
    elif any(ch in text for ch in "あいうえおかきくけこさしすせそ"):
        return "ja"
    else:
        return "en"

def handle_simsimi_command(message, message_object, thread_id, thread_type, author_id, client):
    user_question = " ".join(message.strip().split()[1:]).strip()
    if not user_question:
        client.replyMessage(
            Message(text="• Anh ơi, hỏi em gì đi nè! 😊"),
            message_object, thread_id, thread_type, ttl=12000
        )
        return

    conversation_state = conversation_states.get(thread_id, {'history': []})
    simsimi_response = get_simsimi_response(user_question, conversation_state, thread_id)

    if simsimi_response:
        client.replyMessage(
            Message(
                text=f"Sim (DTW): {simsimi_response}",
                mention=Mention(author_id, length=len("Sim (DTW):"), offset=0)
            ),
            message_object, thread_id, thread_type, ttl=1800000
        )
    else:
        client.replyMessage(
            Message(
                text="• Hic, em không hiểu gì hết á, anh hỏi lại nha! 🥺",
                mention=Mention(author_id, length=len("Sim (DTW):"), offset=0)
            ),
            message_object, thread_id, thread_type, ttl=1800000
        )

def get_simsimi_response(user_question, conversation_state, thread_id):
    headers = {
        "Content-Type": "application/json",
        "x-api-key": SIMSIMI_API_KEY
    }

    lang = detect_language(user_question)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "utext": user_question,
        "lang": lang,
        "atext_bad_prob_max": 0.7
    }

    try:
        response = requests.post(SIMSIMI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        simsimi_reply = result.get("atext")
        if simsimi_reply:
            # thêm dễ thương
            simsimi_reply = make_cute(simsimi_reply)

            # lưu lịch sử hội thoại
            conversation_state['history'].append({'role': 'chồng', 'text': user_question})
            conversation_state['history'].append({'role': 'Sim', 'text': simsimi_reply})
            conversation_states[thread_id] = conversation_state
            return simsimi_reply
        else:
            logging.error(f"Simsimi response invalid: {result}")
            return None

    except requests.exceptions.RequestException as e:
        status_code = response.status_code if 'response' in locals() else 'N/A'
        logging.error(f"Request Exception: {e}, Status Code: {status_code}, Response: {response.text if 'response' in locals() else 'N/A'}")
        return None
    except Exception as e:
        logging.error(f"General Exception: {e}")
        return None

def TQD():
    return {
        'ask': handle_gemini_command
    }