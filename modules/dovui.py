import json
import os
import time
import threading
import logging
from zlapi.models import Message, Mention
import requests
from config import PREFIX

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Chơi câu đố vui",
    'power': "Thành viên"
}

question_cache = {}
gemini_api_key = "AIzaSyCdcXwfWBzg492rooDiIC7XJvaBy7S4JUM" 
gemini_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
headers = {'content-type': 'application/json'}
leaderboard_file = "leaderboard_dovui.json"
used_riddles_file = "used_riddles.json"

def get_user_name(client, uid):
    try:
        user_info = client.fetchUserInfo(uid)
        user = user_info.changed_profiles.get(uid)
        return user.displayName if user and user.displayName else "Người dùng không xác định"
    except Exception:
        return "Người dùng không xác định"

def load_used_riddles():
    try:
        with open(used_riddles_file, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()
    except json.JSONDecodeError:
        logger.error("Lỗi đọc file used_riddles")
        return set()

def save_used_riddles(used_riddles):
    try:
        with open(used_riddles_file, "w") as f:
            json.dump(list(used_riddles), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Lỗi lưu file used_riddles: {str(e)}")

def load_leaderboard():
    try:
        with open(leaderboard_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        logger.error("Lỗi đọc file leaderboard")
        return {}

def save_leaderboard(leaderboard):
    try:
        with open(leaderboard_file, "w") as f:
            json.dump(leaderboard, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Lỗi lưu file leaderboard: {str(e)}")

def update_leaderboard(client, author_id, points):
    user_name = get_user_name(client, author_id)
    leaderboard = load_leaderboard()
    if author_id not in leaderboard:
        leaderboard[author_id] = {"name": user_name, "points": 0}
    leaderboard[author_id]["points"] += points
    leaderboard[author_id]["name"] = user_name
    save_leaderboard(leaderboard)

def get_leaderboard():
    leaderboard = load_leaderboard()
    sorted_leaderboard = sorted(leaderboard.items(), key=lambda x: x[1]["points"], reverse=True)
    return sorted_leaderboard

def reset_leaderboard():
    try:
        save_leaderboard({})
        save_used_riddles(set())
        return True
    except Exception as e:
        logger.error(f"Lỗi khi reset leaderboard hoặc used_riddles: {str(e)}")
        return False

def handle_dovui_command(message, message_object, thread_id, thread_type, author_id, client):
    if thread_id in question_cache:
        client.sendMessage(
            Message(text="Đang có câu hỏi đang hoạt động. Vui lòng trả lời hoặc chờ hết 30 giây."),
            thread_id, thread_type, ttl=30000
        )
        return
    
    used_riddles = load_used_riddles()
    
    try:
        prompt = {
            "contents": [{
                "parts": [{
                    "text": (
                        f"Tạo một câu đố vui bằng tiếng Việt với định dạng JSON. Câu đố phải có một câu hỏi, bốn lựa chọn đáp án (mỗi đáp án là một chuỗi), và một đáp án đúng (là văn bản của đáp án đúng). "
                        f"Đáp án đúng phải khớp chính xác với một trong bốn lựa chọn. Câu đố nên đơn giản, vui nhộn, phù hợp với mọi lứa tuổi. Có thể đố hài, đố vui, đố mẹo, hoặc đố giải trí. "
                        f"Không được trùng với các câu hỏi sau: {', '.join(used_riddles) if used_riddles else 'Không có câu hỏi cũ'}. "
                        f"Định dạng JSON như sau:\n"
                        "{\n"
                        "  \"question\": \"Câu hỏi ở đây\",\n"
                        "  \"options\": [\"Lựa chọn 1\", \"Lựa chọn 2\", \"Lựa chọn 3\", \"Lựa chọn 4\"],\n"
                        "  \"correct\": \"Lựa chọn đúng\"\n"
                        "}"
                    )
                }]
            }]
        }
        
        response = requests.post(gemini_api_url, headers=headers, json=prompt, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        riddle_text = data["candidates"][0]["content"]["parts"][0]["text"]
        if riddle_text.startswith("```json") or riddle_text.startswith("```"):
            riddle_text = riddle_text.strip("```json").strip("```").strip()
        riddle_data = json.loads(riddle_text)
        
        question = riddle_data["question"].strip()
        options = riddle_data["options"]
        correct_answer = riddle_data["correct"].strip().lower()
        
        if len(options) != 4 or correct_answer not in [opt.strip().lower() for opt in options]:
            raise ValueError("Đáp án hoặc lựa chọn không hợp lệ từ API.")
        
        if question in used_riddles:
            client.sendMessage(
                Message(text="Câu đố trùng lặp. Vui lòng thử lại."),
                thread_id, thread_type, ttl=30000
            )
            return
        
        used_riddles.add(question)
        save_used_riddles(used_riddles)
        
        abcd = ["a", "b", "c", "d"]
        option_strs = [f"{abcd[idx]}. {opt}" for idx, opt in enumerate(options)]
        options_display = "\n".join(option_strs)
        
        question_cache[thread_id] = {
            "true_answer": correct_answer,
            "options": options,
            "option_labels": abcd,
            "timestamp": time.time(),
            "answered": False,
            "timer": None
        }
        
        reply_message = f"{question}\n\n{options_display}\n\nDùng {PREFIX}da <a/b/c/d> để trả lời trong 30 giây."
        client.sendMessage(
            Message(text=reply_message),
            thread_id, thread_type, ttl=30000
        )
        
        def check_timeout():
            if thread_id in question_cache and not question_cache[thread_id]["answered"]:
                client.sendMessage(
                    Message(text=f"Hết thời gian. Không ai trả lời. Dùng {PREFIX}dovui để chơi lại."),
                    thread_id, thread_type, ttl=30000
                )
                del question_cache[thread_id]
        
        timer = threading.Timer(30, check_timeout)
        question_cache[thread_id]["timer"] = timer
        timer.start()
        
    except requests.exceptions.Timeout:
        client.sendMessage(
            Message(text="Yêu cầu API hết thời gian. Vui lòng thử lại."),
            thread_id, thread_type, ttl=30000
        )
    except requests.exceptions.HTTPError as e:
        logger.error(f"Lỗi HTTP từ Gemini API: {str(e)}")
        client.sendMessage(
            Message(text="Lỗi API: Không thể kết nối."),
            thread_id, thread_type, ttl=12000
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Lỗi kết nối với Gemini API: {str(e)}")
        client.sendMessage(
            Message(text="Lỗi kết nối với API AI."),
            thread_id, thread_type, ttl=12000
        )
    except Exception as e:
        logger.error(f"Lỗi không xác định trong handle_dovui_command: {str(e)}")
        client.sendMessage(
            Message(text=f"Lỗi không xác định: {str(e)}"),
            thread_id, thread_type, ttl=12000
        )

def handle_da_command(message, message_object, thread_id, thread_type, author_id, client):
    if thread_id not in question_cache:
        client.sendMessage(
            Message(text=f"Hiện không có câu hỏi nào. Dùng {PREFIX}dovui để bắt đầu."),
            thread_id, thread_type, ttl=60000
        )
        return
    
    current_time = time.time()
    question_time = question_cache[thread_id]["timestamp"]
    if current_time - question_time > 30:
        client.sendMessage(
            Message(text=f"Câu hỏi đã hết hạn. Dùng {PREFIX}dovui để chơi lại."),
            thread_id, thread_type, ttl=60000
        )
        if question_cache[thread_id]["timer"]:
            question_cache[thread_id]["timer"].cancel()
        del question_cache[thread_id]
        return
    
    text = message.split(maxsplit=1)
    if len(text) < 2 or not text[1].strip():
        client.sendMessage(
            Message(text=f"Vui lòng nhập đáp án. Ví dụ: {PREFIX}da b"),
            thread_id, thread_type, ttl=30000
        )
        return
    
    user_answer = text[1].strip().lower()
    option_labels = question_cache[thread_id]["option_labels"]
    options = question_cache[thread_id]["options"]
    true_answer_text = question_cache[thread_id]["true_answer"]

    if user_answer not in option_labels:
        client.sendMessage(
            Message(text=f"Đáp án không hợp lệ. Vui lòng chọn {', '.join(option_labels)}."),
            thread_id, thread_type, ttl=30000
        )
        return
    
    if question_cache[thread_id]["timer"]:
        question_cache[thread_id]["timer"].cancel()
    
    user_name = get_user_name(client, author_id)
    idx = option_labels.index(user_answer)
    selected_text = options[idx].strip().lower()
    is_correct = selected_text == true_answer_text
    
    if is_correct:
        update_leaderboard(client, author_id, 1)
    
    try:
        if is_correct:
            text_content = f"Chúc mừng em đáp án đúng rồi 🎉"
        else:
            text_content = f"Đáp án sai bớt ngu nha em 😅 Đáp án đúng là: {true_answer_text}"

        mention = Mention(author_id, length=len("@member"), offset=0)
        client.replyMessage(
            Message(text=f"@member {text_content}", mention=mention),
            message_object, thread_id, thread_type, ttl=30000
        )
        
        logger.info(f"Đã gửi tin nhắn trả lời cho người dùng: {author_id}")
    except Exception as e:
        logger.error(f"Lỗi khi gửi tin nhắn với Mention: {str(e)}")
        if is_correct:
            fallback_text = f"{user_name}, chúc mừng em đáp án đúng rồi đó 🎉"
        else:
            fallback_text = f"{user_name}, đáp án sai bớt ngu nha em 😅 Đáp án đúng là: {true_answer_text}"
        
        client.sendMessage(
            Message(text=fallback_text),
            thread_id, thread_type, ttl=20000
        )
    
    question_cache[thread_id]["answered"] = True
    del question_cache[thread_id]

def handle_bxhdv_command(message, message_object, thread_id, thread_type, author_id, client):
    leaderboard = get_leaderboard()
    if not leaderboard:
        client.replyMessage(
            Message(text="Bảng xếp hạng hiện trống!"),
            message_object, thread_id, thread_type, ttl=60000
        )
        return
    
    leaderboard_text = "🏆 Bảng xếp hạng Đố Vui 🏆\n"
    for idx, (user_id, data) in enumerate(leaderboard[:10], 1):
        leaderboard_text += f"{idx}. {data['name']}: {data['points']} điểm\n"
    
    client.replyMessage(
        Message(text=leaderboard_text),
        message_object, thread_id, thread_type, ttl=60000
    )

def handle_rsbxh_command(message, message_object, thread_id, thread_type, author_id, client):
    if reset_leaderboard():
        client.replyMessage(
            Message(text="Bảng xếp hạng và danh sách câu đố đã được reset thành công!"),
            message_object, thread_id, thread_type, ttl=60000
        )
    else:
        client.replyMessage(
            Message(text="Lỗi khi reset bảng xếp hạng và danh sách câu đố! Vui lòng thử lại."),
            message_object, thread_id, thread_type, ttl=60000
        )

def TQD():
    return {
        'dovui': handle_dovui_command,
        'da': handle_da_command,
        'bxhdv': handle_bxhdv_command,
        'rsbxh': handle_rsbxh_command
    }