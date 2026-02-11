import os
import time
import threading
import random
import json
import re
from zlapi.models import Message, Mention, MultiMention, ThreadType
from config import ADMIN, PREFIX

# ========= THÔNG TIN MODULE ========= #
des = {
    'version': "5.1.0",
    'credits': "Latte",
    'description': "Nhây tag và nhây all ẩn hỗ trợ màu, text tự nhập",
    'power': "Admin"
}

# ========= BIẾN TOÀN CỤC ========= #
is_nhay_running = False
delay_time = 3
RUNNING_FILE = "running_nhaytag.json"
list_color = ['db342e','f27806','f7b503','15a85f']
emojis = ["😂","🤣","🔥","💀","🤡","😎","🐧","👀"]
words = ["haha","ngu","vl","kaka","bớt ảo tưởng","cười","chọc",
         "thật luôn","đỉnh cao","ảo ma","hết thuốc","bình tĩnh","xong đời"]

# ========= HÀM TIỆN ÍCH ========= #
def load_running_groups():
    if os.path.exists(RUNNING_FILE):
        try:
            with open(RUNNING_FILE,"r",encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_running_groups(data):
    with open(RUNNING_FILE,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

def clear_running_groups():
    if os.path.exists(RUNNING_FILE):
        os.remove(RUNNING_FILE)

def make_sentence():
    n = random.randint(5,7)
    sentence = " ".join(random.sample(words,n))
    emoji = random.choice(emojis)
    return f"{sentence} {emoji}"

def m_tstyles(list_styles):
    return json.dumps({"styles": list_styles,"ver":0})

def tstyles_for_sentence(sentence, skip_offset=0):
    words_list = sentence.split()
    offset = skip_offset
    list_st = []
    for word in words_list:
        if any(char in emojis for char in word):
            offset += len(word) + 1
            continue
        if re.match(r'^[\wÀ-ỹ]+$', word):
            list_st.append({
                "start": offset,
                "len": len(word),
                "st": f"b,i,c_{random.choice(list_color)},f_18"
            })
        offset += len(word) + 1
    return m_tstyles(list_st)

# ========= DỪNG NHÂY ========= #
def stop_nhay(client, message_object, thread_id, thread_type):
    global is_nhay_running
    is_nhay_running = False
    clear_running_groups()
    client.replyMessage(Message(text="🐧 Đã dừng nhây."), message_object, thread_id, thread_type, ttl=6000)

# ========= NHÂY CHÍNH ========= #
def nhay(message, message_object, thread_id, thread_type, author_id, client):
    global is_nhay_running, delay_time

    if author_id not in ADMIN:
        client.replyMessage(Message(text="🚫 Bạn không có quyền dùng lệnh này. Chỉ có admin Latte mới được sử dụng lệnh này"),
                            message_object, thread_id, thread_type, ttl=6000)
        return

    parts = message.strip().split()
    if len(parts) < 2:
        client.replyMessage(Message(text=f"⚙️ Dùng: {PREFIX}nhay on / stop / set / text / info"),
                            message_object, thread_id, thread_type, ttl=6000)
        return

    action = parts[1].lower()
    args = parts[2:]

    # ----- SET DELAY ----- #
    if action == "set":
        if len(args) < 1 or not args[0].isdigit():
            client.replyMessage(Message(text=f"❗ Cú pháp: {PREFIX}nhay set <số giây>"),
                                message_object, thread_id, thread_type, ttl=6000)
            return
        delay_time = int(args[0])
        client.replyMessage(Message(text=f"✅ Đặt delay mỗi lần nhây: {delay_time}s."),
                            message_object, thread_id, thread_type, ttl=6000)
        return

    # ----- TẠO TEXT (AUTO HOẶC TỰ NHẬP) ----- #
    if action == "text":
        if len(args) < 1:
            client.replyMessage(Message(text=f"❗ Cú pháp: {PREFIX}nhay text <số_lượng> hoặc {PREFIX}nhay text <nội_dung>"),
                                message_object, thread_id, thread_type, ttl=6000)
            return

        # Xoá file cũ nếu có
        if os.path.exists("noidung.txt"):
            try:
                os.remove("noidung.txt")
                print("🗑️ Đã xoá file noidung.txt cũ.")
            except Exception as e:
                print(f"[nhay text] Lỗi khi xoá file cũ: {e}")

        # Nếu nhập số → random câu
        if args[0].isdigit():
            num_sentences = int(args[0])
            with open("noidung.txt", "w", encoding="utf-8") as f:
                for _ in range(num_sentences):
                    f.write(make_sentence() + "\n")
            client.replyMessage(Message(text=f"✅ Đã tạo {num_sentences} dòng ngẫu nhiên trong file."),
                                message_object, thread_id, thread_type, ttl=6000)
            return

        # Nếu nhập text → lưu nội dung người dùng
        user_text = " ".join(args)
        with open("noidung.txt", "w", encoding="utf-8") as f:
            f.write(user_text.strip() + "\n")

        client.replyMessage(Message(text=f"✅ Đã lưu nội dung tuỳ chỉnh vào file:\n“{user_text.strip()}”"),
                            message_object, thread_id, thread_type, ttl=6000)
        return

    # ----- INFO ----- #
    if action == "info":
        status = "🟢 Đang chạy" if is_nhay_running else "🔴 Đang tắt"
        num_lines = 0
        if os.path.exists("noidung.txt"):
            with open("noidung.txt", "r", encoding="utf-8") as f:
                num_lines = len([line for line in f if line.strip()])
        info_text = f"📊 Thông tin nhây:\n• Trạng thái: {status}\n• Delay: {delay_time}s\n• Số câu trong file: {num_lines}"
        client.replyMessage(Message(text=info_text),
                            message_object, thread_id, thread_type, ttl=6000)
        return

    # ----- STOP ----- #
    if action == "stop":
        if not is_nhay_running:
            client.replyMessage(Message(text="⚠️ Hiện không có nhây nào đang chạy."),
                                message_object, thread_id, thread_type, ttl=6000)
        else:
            stop_nhay(client, message_object, thread_id, thread_type)
        return

    # ----- ON ----- #
    if action == "on":
        try:
            with open("noidung.txt", "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            client.replyMessage(Message(text="❌ Không tìm thấy file."),
                                message_object, thread_id, thread_type, ttl=6000)
            return

        if not lines:
            client.replyMessage(Message(text="⚠️ File trống."),
                                message_object, thread_id, thread_type, ttl=6000)
            return

        clear_running_groups()
        save_running_groups([{"thread_id": thread_id, "thread_type": str(thread_type)}])
        client.replyMessage(Message(text=f"🔥 Bắt đầu nhây (delay {delay_time}s)..."),
                            message_object, thread_id, thread_type, ttl=6000)
        is_nhay_running = True

        tagged_uid = message_object.mentions[0]['uid'] if message_object.mentions else None
        display_name = message_object.mentions[0].get("name") if message_object.mentions else ""

        def nhay_loop():
            while is_nhay_running:
                for line in lines:
                    if not is_nhay_running:
                        break
                    try:
                        # ========= XỬ LÝ TAG ========= #
                        if tagged_uid:
                            tag_text = f"@{display_name} "
                            text_to_send = tag_text + line
                            mention_obj = Mention(tagged_uid, length=len(tag_text)-1, offset=0)
                            style_offset = len(tag_text)
                            m_st = tstyles_for_sentence(line, skip_offset=style_offset)
                        else:
                            text_to_send = line
                            # Tag all ẩn
                            group_info = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
                            members = group_info.get('memVerList', [])
                            mentions = [Mention(u.split('_')[0], length=3000, offset=0, auto_format=False) for u in members]
                            mention_obj = MultiMention(mentions)
                            m_st = tstyles_for_sentence(line)

                        client.send(Message(text=text_to_send, mention=mention_obj, style=m_st),
                                    thread_id, thread_type, ttl=60000*5)
                        time.sleep(delay_time)
                    except Exception as e:
                        print(f"[NHAY LOOP] Lỗi gửi: {e}")
                        time.sleep(2)

        threading.Thread(target=nhay_loop).start()
        return

    # ----- MẶC ĐỊNH ----- #
    client.replyMessage(Message(text=f"⚙️ Dùng: {PREFIX}nhay on / stop / set / text / info"),
                        message_object, thread_id, thread_type, ttl=6000)

# ========= AUTO RESTART ========= #
def auto_restart_nhaytag(client):
    data = load_running_groups()
    if not data:
        print("[AUTO NHÂY] Không có nhóm nào đang nhây.")
        return
    for g in data:
        try:
            ttype_str = g["thread_type"].split(".")[-1]
            ttype = ThreadType[ttype_str]
            print(f"[AUTO NHÂY] Bật lại nhây cho nhóm {g['thread_id']}")
        except Exception as e:
            print(f"[AUTO NHÂY] Lỗi: {e}")

# ========= REGISTER MODULE ========= #
def TQD():
    return {'nhay': nhay}
