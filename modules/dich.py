import logging
import re
import os
import requests
from gtts import gTTS
from openai import OpenAI
from zlapi.models import Message, Mention

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Dịch ngôn ngữ",
    'power': "Thành viên"
}

# 🔑 API key OpenAI
openai_api_key = "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"
client_openai = OpenAI(api_key=openai_api_key)


# ==============================
# 🔹 Làm sạch text GPT trả về
# ==============================
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"(\*\*|\*|__|_|~~|`)+", "", text)
    text = re.sub(r"[^\w\s.,!?;:'\"()\-–—/]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


# ==============================
# 🔹 GPT dịch và tạo phát âm
# ==============================
def translate_with_gpt(text, target_lang):
    try:
        prompt = (
            f"Dịch đoạn văn sau sang ngôn ngữ '{target_lang}'. "
            f"Trả về đúng format:\n"
            f"Dịch: <bản dịch>\nPhát âm: <phiên âm nếu có hoặc bỏ trống nếu không có>.\n\n"
            f"Nội dung:\n{text}"
        )
        response = client_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là chuyên gia dịch thuật, luôn trả kết quả sạch không có markdown hay emoji."},
                {"role": "user", "content": prompt}
            ]
        )
        if response.choices:
            raw = response.choices[0].message.content
            # Tách bản dịch và phát âm
            match = re.search(r"Dịch:\s*(.+?)(?:\nPhát âm:\s*(.+))?$", raw, re.DOTALL)
            if match:
                translated = clean_text(match.group(1))
                pronunciation = clean_text(match.group(2) or "")
                return translated, pronunciation
            return clean_text(raw), ""
        return None, ""
    except Exception as e:
        logging.error(f"Lỗi dịch GPT: {e}")
        return None, ""


# ==============================
# 🔹 Voice (text → mp3 → gửi)
# ==============================
def convert_text_to_mp3(text, lang_code="vi"):
    try:
        tts = gTTS(text=text, lang=lang_code)
        mp3_file = "voice_gpt.mp3"
        tts.save(mp3_file)
        return mp3_file
    except Exception as e:
        logging.error(f"Lỗi TTS: {e}")
        return None


def upload_to_host(file_name):
    try:
        with open(file_name, "rb") as file:
            files = {"files[]": file}
            res = requests.post("https://uguu.se/upload", files=files).json()
            if res.get("success"):
                return res["files"][0]["url"]
            return False
    except Exception as e:
        logging.error(f"Upload lỗi: {e}")
        return False


# ==============================
# 🔹 Xử lý lệnh !dich
# ==============================
def handle_translate_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Lệnh: !dich <ngôn_ngữ_đích> && <văn_bản>
    Ví dụ:
      !dich en && Xin chào
      !dich vi && Hello world
    """
    content = message.strip().split(maxsplit=1)
    if len(content) < 2:
        client.replyMessage(
            Message(
                text="@member Cú pháp sai!\nVí dụ: !dich en && Xin chào",
                mention=Mention(author_id, length=len("@member"), offset=0)
            ),
            message_object, thread_id, thread_type, ttl=8000
        )
        return

    parts = content[1].split("&&", maxsplit=1)
    if len(parts) != 2:
        client.replyMessage(
            Message(
                text="@member Thiếu dấu '&&' giữa ngôn ngữ và nội dung cần dịch!",
                mention=Mention(author_id, length=len("@member"), offset=0)
            ),
            message_object, thread_id, thread_type, ttl=8000
        )
        return

    target_lang = parts[0].strip().lower()
    text_to_translate = parts[1].strip()

    if not target_lang or not text_to_translate:
        client.replyMessage(
            Message(
                text="@member Thiếu ngôn ngữ hoặc nội dung!",
                mention=Mention(author_id, length=len("@member"), offset=0)
            ),
            message_object, thread_id, thread_type, ttl=8000
        )
        return

    # Gọi GPT
    translation, pronunciation = translate_with_gpt(text_to_translate, target_lang)

    if translation:
        msg = f"@member\nDịch \"{text_to_translate}\" sang {target_lang.upper()}:\n\n{translation}"
        if pronunciation:
            msg += f"\n\n🔊 Phát âm: {pronunciation}"

        # Gửi text trước
        client.replyMessage(
            Message(text=msg, mention=Mention(author_id, length=len("@member"), offset=0)),
            message_object, thread_id, thread_type, ttl=300000
        )

        # 🔊 Gửi voice (tùy vào ngôn ngữ đích, fallback là 'en')
        mp3_file = convert_text_to_mp3(pronunciation or translation, lang_code=target_lang if len(target_lang) == 2 else "en")
        if mp3_file:
            url = upload_to_host(mp3_file)
            if url:
                file_size = os.path.getsize(mp3_file)
                client.sendRemoteVoice(url, thread_id, thread_type, fileSize=file_size)
            try:
                if os.path.exists(mp3_file):
                    os.remove(mp3_file)
                    logging.info(f"Đã xoá file voice: {mp3_file}")
            except Exception as e:
                logging.error(f"Lỗi khi xoá file {mp3_file}: {e}")
    else:
        client.replyMessage(Message(text="Không thể dịch văn bản này."), message_object, thread_id, thread_type, ttl=8000)


# ==============================
# 🔹 Đăng ký lệnh
# ==============================
def TQD():
    return {
        "dich": handle_translate_command
    }
