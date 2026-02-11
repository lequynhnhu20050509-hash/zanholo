import logging
from openai import OpenAI
from zlapi.models import Message, Mention, MultiMsgStyle, MessageStyle

des = {
    'version': "2.0.2",
    'credits': "Latte",
    'description': "Chat cùng AI",
    'power': "Thành viên"
}

# 🔑 API key OpenAI
openai_api_key = "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"
client_openai = OpenAI(api_key=openai_api_key)

# Lưu lịch sử hội thoại cho từng thread
conversation_states = {}

# Style màu xanh, in đậm, font size 8
success_styles = MultiMsgStyle([
    MessageStyle(offset=0, length=10000, style="color", color="#15a85f", auto_format=False),
    MessageStyle(offset=0, length=10000, style="font", size="8", auto_format=False),
    MessageStyle(offset=0, length=10000, style="bold", auto_format=False)
])

def sanitize_openai_text(text: str) -> str:
    """
    Xóa toàn bộ dấu '*' trong text OpenAI trả về
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

    # Gọi OpenAI API
    chat_response = get_chat_response(user_question, thread_id)

    if chat_response:
        clean = sanitize_openai_text(chat_response)
        send_success_message(
            f"@member\n\n{clean}",
            message_object, thread_id, thread_type, client, author_id, ttl=720000
        )
    else:
        send_error_message(
            "⚠️ OpenAI không phản hồi",
            message_object, thread_id, thread_type, client, ttl=12000
        )

def get_chat_response(user_question, thread_id):
    """
    Gửi câu hỏi tới OpenAI, lưu và duy trì lịch sử hội thoại
    """
    # Lấy hoặc tạo lịch sử hội thoại cho thread
    conversation_state = conversation_states.get(thread_id, {
        'history': [
            {"role": "system", "content": "Bạn là trợ lý AI hữu ích, trả lời tiếng Việt."}
        ]
    })
    conversation_state['history'].append({"role": "user", "content": user_question})

    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation_state['history'][-15:]  # chỉ giữ 15 lượt gần nhất
        )

        if response.choices:
            bot_reply = response.choices[0].message.content
            if bot_reply:
                conversation_state['history'].append({"role": "assistant", "content": bot_reply})
                conversation_states[thread_id] = conversation_state
                return bot_reply
        return None
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
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
        'gpt': handle_chat_command
    }
