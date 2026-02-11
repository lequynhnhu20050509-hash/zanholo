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
    'description': "Chơi nối từ với AI.",
    'power': "Thành viên"
}

gemini_api_key = "AIzaSyCdcXwfWBzg492rooDiIC7XJvaBy7S4JUM"
gemini_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
headers = {'content-type': 'application/json'}
game_cache = {}
leaderboard_file = "leaderboard.json"

# ============================
# Helper Functions
# ============================

def get_user_name(client, uid):
    try:
        user_info = client.fetchUserInfo(uid)
        user = user_info.changed_profiles.get(uid)
        return user.displayName if user and user.displayName else "Người dùng không xác định"
    except Exception:
        return "Người dùng không xác định"

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
        return True
    except Exception as e:
        logger.error(f"Lỗi khi reset leaderboard: {str(e)}")
        return False

def reply_with_mention(client, message_text, message_object, thread_id, thread_type, author_id, ttl=60000):
    """Gửi tin nhắn có Mention."""
    try:
        mention = Mention(author_id, length=len("@member"), offset=0)
        client.replyMessage(
            Message(text=f"@member\n{message_text}", mention=mention),
            message_object, thread_id, thread_type, ttl=ttl
        )
    except Exception as e:
        logger.error(f"Lỗi khi gửi tin nhắn với Mention: {str(e)}")
        client.replyMessage(
            Message(text=message_text),
            message_object, thread_id, thread_type, ttl=ttl
        )

# ============================
# Command Handlers
# ============================

def handle_nt_command(message, message_object, thread_id, thread_type, author_id, client):
    text = message.split(maxsplit=1)
    
    if len(text) < 2 or not text[1].strip():
        reply_with_mention(
            client, f"Vui lòng nhập từ để nối! Ví dụ: {PREFIX}nt cá mập",
            message_object, thread_id, thread_type, author_id, ttl=60000
        )
        return
    
    user_word = text[1].strip().lower()
    user_name = get_user_name(client, author_id)

    # Kiểm tra số lượng từ
    if len(user_word.split()) < 2:
        reply_with_mention(
            client, f"Vui lòng nhập ít nhất 2 từ! Ví dụ: {PREFIX}nt cá mập",
            message_object, thread_id, thread_type, author_id, ttl=60000
        )
        return

    # Khởi tạo game nếu chưa có
    if thread_id not in game_cache or not game_cache[thread_id]["active"]:
        game_cache[thread_id] = {
            "used_words": {user_word},
            "last_word": user_word,
            "timestamp": time.time(),
            "active": True,
            "timer": None
        }
        update_leaderboard(client, author_id, 1)
        return ai_respond(thread_id, thread_type, message_object, client, user_name, author_id)
    
    # Hủy timer cũ
    if game_cache[thread_id]["timer"]:
        game_cache[thread_id]["timer"].cancel()
    
    last_word = game_cache[thread_id]["last_word"].split()[-1]
    used_words = game_cache[thread_id]["used_words"]
    
    # Kiểm tra nối từ
    if not user_word.startswith(last_word):
        reply_with_mention(
            client, f"Thua rồi! Từ '{user_word}' không bắt đầu bằng '{last_word}'. Trò chơi kết thúc. Dùng {PREFIX}nt <từ> để chơi lại.",
            message_object, thread_id, thread_type, author_id, ttl=60000
        )
        game_cache[thread_id]["active"] = False
        del game_cache[thread_id]
        return
    
    if user_word in used_words:
        reply_with_mention(
            client, f"Thua rồi! Từ '{user_word}' đã được dùng trước đó. Trò chơi kết thúc. Dùng {PREFIX}nt <từ> để chơi lại.",
            message_object, thread_id, thread_type, author_id, ttl=60000
        )
        game_cache[thread_id]["active"] = False
        del game_cache[thread_id]
        return
    
    user_word_parts = user_word.split()
    if len(user_word_parts) == 2 and user_word_parts[0] == user_word_parts[1]:
        reply_with_mention(
            client, f"Thua rồi! Từ '{user_word}' trùng lặp không hợp lệ. Trò chơi kết thúc. Dùng {PREFIX}nt <từ> để chơi lại.",
            message_object, thread_id, thread_type, author_id, ttl=60000
        )
        game_cache[thread_id]["active"] = False
        del game_cache[thread_id]
        return
    
    game_cache[thread_id]["used_words"].add(user_word)
    game_cache[thread_id]["last_word"] = user_word
    game_cache[thread_id]["timestamp"] = time.time()
    update_leaderboard(client, author_id, 1)
    
    ai_respond(thread_id, thread_type, message_object, client, user_name, author_id)

# ============================
# AI Response
# ============================

def ai_respond(thread_id, thread_type, message_object, client, user_name, author_id):
    if thread_id not in game_cache or not game_cache[thread_id]["active"]:
        return
    
    last_word = game_cache[thread_id]["last_word"].split()[-1]
    used_words = game_cache[thread_id]["used_words"]
    
    try:
        prompt = {
            "contents": [{
                "parts": [{
                    "text": (
                        f"Trong trò chơi nối từ bằng tiếng Việt, hãy đưa ra một từ hoặc cụm từ hợp lệ (tối đa 2 từ) "
                        f"bắt đầu bằng từ '{last_word}'. "
                        f"Không được trùng với các từ đã dùng: {', '.join(used_words)}. "
                        f"Từ nối phải là danh từ hoặc cụm danh từ hợp lệ, không được là từ đơn lẻ giống '{last_word}' "
                        f"và không lặp lại từ cuối của từ trước (ví dụ: không trả về '{last_word} {last_word}'). "
                        f"Nếu không tìm được từ hợp lệ, trả về JSON với 'next_word' là chuỗi rỗng. "
                        f"Định dạng JSON:\n"
                        "{\n"
                        "  \"next_word\": \"từ nối\"\n"
                        "}"
                    )
                }]
            }]
        }
        
        response = requests.post(gemini_api_url, headers=headers, json=prompt)
        response.raise_for_status()
        data = response.json()
        
        riddle_text = data["candidates"][0]["content"]["parts"][0]["text"]
        if riddle_text.startswith("```json") or riddle_text.startswith("```"):
            riddle_text = riddle_text.strip("```json").strip("```").strip()
        result = json.loads(riddle_text)
        next_word = result.get("next_word", "").strip().lower()
        
        if not next_word:
            reply_with_mention(
                client, f"Tôi đã thua:((! Không tìm được từ nối. {user_name} thắng! Dùng {PREFIX}nt <từ> để chơi lại.",
                message_object, thread_id, thread_type, author_id, ttl=12000
            )
            game_cache[thread_id]["active"] = False
            del game_cache[thread_id]
            return
        
        if next_word == last_word or next_word in [w.strip() for w in used_words]:
            reply_with_mention(
                client, f"Tôi đã thua:((! Từ '{next_word}' không hợp lệ hoặc đã được dùng. {user_name} thắng! Dùng {PREFIX}nt <từ> để chơi lại.",
                message_object, thread_id, thread_type, author_id, ttl=12000
            )
            game_cache[thread_id]["active"] = False
            del game_cache[thread_id]
            return
        
        next_word_parts = next_word.split()
        if len(next_word_parts) == 2 and next_word_parts[0] == next_word_parts[1]:
            reply_with_mention(
                client, f"Tôi đã thua! Từ trùng lặp không hợp lệ. {user_name} thắng! Dùng {PREFIX}nt <từ> để chơi lại.",
                message_object, thread_id, thread_type, author_id, ttl=12000
            )
            game_cache[thread_id]["active"] = False
            del game_cache[thread_id]
            return
        
        game_cache[thread_id]["used_words"].add(next_word)
        game_cache[thread_id]["last_word"] = next_word
        game_cache[thread_id]["timestamp"] = time.time()
        
        reply_with_mention(
            client, f"Từ nối | {next_word}\nTrả lời bằng {PREFIX}nt <từ> trong 60 giây.",
            message_object, thread_id, thread_type, author_id, ttl=60000
        )
        
        # Timer 60 giây cho lượt người chơi
        def check_timeout():
            if thread_id in game_cache and game_cache[thread_id]["active"]:
                reply_with_mention(
                    client, f"Hết thời gian! {user_name} thua. Trò chơi kết thúc. Dùng {PREFIX}nt <từ> để chơi lại.",
                    message_object, thread_id, thread_type, author_id, ttl=60000
                )
                game_cache[thread_id]["active"] = False
                del game_cache[thread_id]
        
        timer = threading.Timer(60, check_timeout)
        game_cache[thread_id]["timer"] = timer
        timer.start()
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Lỗi kết nối API: {str(e)}")
        reply_with_mention(
            client, f"Lỗi kết nối API AI! {user_name} thắng! Dùng {PREFIX}nt <từ> để chơi lại.",
            message_object, thread_id, thread_type, author_id, ttl=12000
        )
        game_cache[thread_id]["active"] = False
        del game_cache[thread_id]
    except Exception as e:
        logger.error(f"Lỗi không xác định: {str(e)}")
        reply_with_mention(
            client, f"Lỗi không xác định: {str(e)}. {user_name} thắng! Dùng {PREFIX}nt <từ> để chơi lại.",
            message_object, thread_id, thread_type, author_id, ttl=12000
        )
        game_cache[thread_id]["active"] = False
        del game_cache[thread_id]

# ============================
# BXH Commands
# ============================

def handle_bxhnt_command(message, message_object, thread_id, thread_type, author_id, client):
    leaderboard = get_leaderboard()
    if not leaderboard:
        reply_with_mention(
            client, "Bảng xếp hạng hiện trống!",
            message_object, thread_id, thread_type, author_id, ttl=60000
        )
        return
    
    leaderboard_text = "🏆 Bảng xếp hạng Nối Từ 🏆\n"
    for idx, (user_id, data) in enumerate(leaderboard[:10], 1):
        leaderboard_text += f"{idx}. {data['name']}: {data['points']} điểm\n"
    
    reply_with_mention(
        client, leaderboard_text,
        message_object, thread_id, thread_type, author_id, ttl=60000
    )

def handle_resetbxh_command(message, message_object, thread_id, thread_type, author_id, client):
    if reset_leaderboard():
        reply_with_mention(
            client, "Bảng xếp hạng đã được reset thành công!",
            message_object, thread_id, thread_type, author_id, ttl=60000
        )
    else:
        reply_with_mention(
            client, "Lỗi khi reset bảng xếp hạng! Vui lòng thử lại.",
            message_object, thread_id, thread_type, author_id, ttl=60000
        )

# ============================
# TQD Command Mapping
# ============================

def TQD():
    return {
        'nt': handle_nt_command,
        'bxhnt': handle_bxhnt_command,
        'resetbxh': handle_resetbxh_command
    }
