import requests
import logging
from zlapi.models import Message, Mention, MultiMsgStyle, MessageStyle
from config import GEMINI_API_KEY
des = {
    'version': "2.0.2",
    'credits': "Latte",
    'description': "Chat cùng Gemini",
    'power': "Thành viên"
}




# Lưu lịch sử hội thoại cho từng thread
conversation_states = {}

# Style màu xanh, in đậm, font size 8
success_styles = MultiMsgStyle([
    MessageStyle(offset=0, length=10000, style="color", color="#15a85f", auto_format=False),
    MessageStyle(offset=0, length=10000, style="font", size="8", auto_format=False),
    MessageStyle(offset=0, length=10000, style="bold", auto_format=False)
])

def sanitize_gemini_text(text: str) -> str:
    """
    Xóa toàn bộ dấu '*' trong text Gemini trả về
    """
    if not text:
        return text
    return text.replace("*", "").strip()

def handle_chat_command(message, message_object, thread_id, thread_type, author_id, client):
    # Lấy câu hỏi sau prefix (!gpt ...)
    user_question = " ".join(message.strip().split()[1:]).strip()
    if not user_question:
        client.replyMessage(
            Message(
                text="@member bạn chưa nhập câu hỏi!",
                mention=Mention(author_id, length=len("@member"), offset=0)
            ),
            message_object, thread_id, thread_type, ttl=12000
        )
        return

    # Gọi Gemini API
    chat_response = get_chat_response(user_question, thread_id)

    if chat_response:
        clean = sanitize_gemini_text(chat_response)
        send_success_message(
            f"@member\n\n{clean}",
            message_object, thread_id, thread_type, client, author_id, ttl=720000
        )
    else:
        send_error_message(
            "⚠️ Gemini không phản hồi",
            message_object, thread_id, thread_type, client, ttl=12000
        )

def get_chat_response(user_question, thread_id):
    # Model mới: gemini-2.0-flash
    model = "models/gemini-2.0-flash"
    api_url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={GEMINI_API_KEY}"
    headers = {'content-type': 'application/json'}

    # Lấy hoặc tạo lịch sử hội thoại
    conversation_state = conversation_states.get(thread_id, {'history': []}) 
    conversation_state['history'].append({"role": "user", "parts": [{"text": user_question}]})

    data = {
        "contents": conversation_state['history'][-10:]  # chỉ giữ 10 lượt gần nhất
    }

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()

        if "candidates" in result and result["candidates"]:
            for candidate in result["candidates"]:
                if "content" in candidate and "parts" in candidate["content"]:
                    for part in candidate["content"]["parts"]:
                        if "text" in part:
                            bot_reply = part["text"]
                            # Lưu hội thoại
                            conversation_state['history'].append(
                                {"role": "model", "parts": [{"text": bot_reply}]}
                            )
                            conversation_states[thread_id] = conversation_state
                            return bot_reply
        return None
    except Exception as e:
        logging.error(f"Gemini error: {e}")
        return None

def send_success_message(message, message_object, thread_id, thread_type, client, author_id, ttl):
    client.replyMessage(
        Message(
            text=message,
            mention=Mention(author_id, length=len("@member"), offset=0),
            style=success_styles  # <-- style màu xanh, in đậm
        ),
        message_object, thread_id, thread_type, ttl=ttl
    )

def send_error_message(message, message_object, thread_id, thread_type, client, ttl):
    client.replyMessage(
        Message(text=message),
        message_object, thread_id, thread_type, ttl=ttl
    )

def TQD():
    return {
        'gem': handle_chat_command
    }
