import requests
import os
import logging
import json
from zlapi.models import Message, Mention

des = {
    'version': "1.0.0",
    'credits': "Latte",
    'description': "Hỏi code Python",
    'power': "Thành viên"
}

gemini_api_key = "AIzaSyCdcXwfWBzg492rooDiIC7XJvaBy7S4JUM"
conversation_states = {}

# Hàm lấy tên người dùng
def get_user_name_by_id(bot, user_id):
    try:
        info = bot.fetchUserInfo(user_id)
        if hasattr(info, "changed_profiles") and user_id in info.changed_profiles:
            profile = info.changed_profiles[user_id]
            return getattr(profile, "zaloName", None) or getattr(profile, "displayName", "Unknown User")
        return "Unknown User"
    except Exception:
        return "Unknown User"

# Load prompt
try:
    with open('data/aipy_prompt.json', 'r', encoding='utf-8') as f:
        prompts = json.load(f)
    base_prompt = prompts.get('prompt', {}).get('base', (
        'Tao là coder xịn trả lời gọn vừa vibe Gen Z dùng từ lóng tục nhẹ và ít emoji cho giống người. '
        'Chỉ nói về ngôn ngữ lập trình không dài dòng không nói tiếng Anh không dùng dấu chấm phẩy ngoặc kép '
        'hoặc dấu sao không chửi ai biệt danh TKD và Dương là tên của T K D. Trả lời như bạn thân nói chuyện tự nhiên hơi bựa. '
        'Ví dụ: Bro muốn sort list thì list.sort hoặc sorted cmm dễ vcl'
    ))
    history_prefix = prompts.get('prompt', {}).get('hisprf', 'lịch sử code')
    user_prefix = prompts.get('prompt', {}).get('prf', 'coder hỏi')
    postfix = prompts.get('prompt', {}).get('postfix', 'Trả lời đúng trọng tâm vibe Gen Z tự nhiên không lạc đề')
except Exception as e:
    logging.error(f"Lỗi load prompts: {e}")
    exit()

def handle_aipy_command(message, message_object, thread_id, thread_type, author_id, client):
    extra_text = " ".join(message.strip().split()[1:]).strip()

    # Lấy nội dung message gốc nếu reply (quote)
    if hasattr(message_object, 'quote') and message_object.quote:
        question = message_object.quote.msg.strip()
        if extra_text:
            question = f"{extra_text} {question}"
    else:
        question = extra_text

    # Nếu không có câu hỏi → trả lời cứng
    if not question:
        client.replyMessage(
            Message(
                text="@member Hỏi code Python đi bro 😎",
                mention=Mention(author_id, length=len("@member"), offset=0)
            ),
            message_object, thread_id, thread_type, ttl=12000
        )
        return

    # Lấy history thread
    conversation_state = conversation_states.get(thread_id, {'history': [], 'user_id': author_id})

    # Kiểm tra nếu người gửi là Duong → trả lời lịch sự
    user_name = get_user_name_by_id(client, author_id)
    if user_name.lower() == 'Dương':
        custom_base_prompt = (
            'Tao là coder xịn trả lời gọn, lịch sự và tôn trọng người tạo ra, '
            'không tục tĩu, chỉ tập trung giải thích ngắn gọn dễ hiểu về code Python.'
        )
        custom_postfix = 'Trả lời chính xác, lịch sự và dễ hiểu cho người tạo ra.'
        code_response = get_code_response(question, conversation_state, thread_id, author_id,
                                          base_prompt=custom_base_prompt, postfix=custom_postfix)
    else:
        code_response = get_code_response(question, conversation_state, thread_id, author_id)

    if code_response:
        send_success_message(
            f"@member {code_response}", message_object, thread_id, thread_type, client, author_id, ttl=720000
        )
    else:
        send_error_message(
            "Code gì mà căng vcl tui bí mẹ rồi 😵", message_object, thread_id, thread_type, client, ttl=12000
        )

def get_code_response(user_question, conversation_state, thread_id, author_id, base_prompt=None, postfix=None):
    base_prompt = base_prompt or globals().get('base_prompt')
    postfix = postfix or globals().get('postfix')

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_api_key}"
    headers = {'content-type': 'application/json'}

    prompt = base_prompt
    if not conversation_state['history']:
        conversation_state['history'].append({'role': 'system', 'text': 'Yo bro hỏi code Python gì tui giải ngay 😈'})
    prompt += history_prefix + "\n"
    for item in conversation_state['history'][-10:]:
        prompt += f"{item['role']} {item['text']}\n"

    prompt += f"{user_prefix} {user_question}\n"
    prompt += postfix
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()

        if 'candidates' in result and result['candidates']:
            for candidate in result['candidates']:
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        if 'text' in part:
                            # lưu lịch sử thread
                            conversation_state['history'].append({'role': 'user', 'text': user_question})
                            conversation_state['history'].append({'role': 'bot', 'text': part['text']})
                            conversation_states[thread_id] = conversation_state
                            return part['text']
        return None
    except Exception as e:
        logging.error(f"Lỗi gọi API: {e}")
        return None

def send_success_message(message, message_object, thread_id, thread_type, client, author_id, ttl):
    client.replyMessage(
        Message(text=message, mention=Mention(author_id, length=len("@member"), offset=0)),
        message_object, thread_id, thread_type, ttl=ttl
    )

def send_error_message(message, message_object, thread_id, thread_type, client, ttl):
    client.replyMessage(
        Message(text=message), message_object, thread_id, thread_type, ttl=ttl
    )

def TQD():
    return {
        'aipy': handle_aipy_command
    }
