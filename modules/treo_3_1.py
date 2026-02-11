import os
import time
import threading
import json
from zlapi.models import Message, MessageStyle, MultiMsgStyle, Mention, MultiMention
from config import PREFIX, ADMIN

des = {
    'version': "1.1.9",
    'credits': "Latte",
    'description': "Treo Ngôn 5 màu",
    'power': "Quản trị viên Bot"
}

COLORS = ['15A85F', 'DB342E', 'F27806', 'F7B503', '0000FF']
is_treo_running = False
treo_threads = {}
treo_color_index = {}
TTL_CMD = 250000  # ttl óc cặc

def handle_treo_command(message, message_object, thread_id, thread_type, author_id, client):
    global is_treo_running, treo_threads, treo_color_index

    # Check quyền ADMIN
    if str(author_id) != str(ADMIN):
        text = "❌ Bạn không có quyền dùng lệnh này!"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(text), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(text), style="bold", auto_format=False),
        ])
        client.replyMessage(Message(text=text, style=styles), message_object, thread_id, thread_type, ttl=TTL_CMD)
        return

    parts = message.split()
    if len(parts) < 2:
        guide = (
            f"Hướng dẫn sử dụng:\n"
            f"• {PREFIX}treo on – Bắt đầu gửi nội dung từ treo.txt\n"
            f"• {PREFIX}treo stop – Dừng gửi nội dung"
        )
        client.replyMessage(Message(text=guide), message_object, thread_id, thread_type, ttl=TTL_CMD)
        return

    action = parts[1].lower()

    if action == "stop":
        is_treo_running = False
        treo_threads.pop(thread_id, None)
        treo_color_index.pop(thread_id, None)
        msg = "🛑 Đã dừng gửi nội dung."
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(msg), style="color", color="#DB342E", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="bold", auto_format=False),
        ])
        client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=TTL_CMD)
        return

    if action == "on":
        try:
            with open("noidung.txt", "r", encoding="utf-8") as f:
                content = f.read().strip()
        except FileNotFoundError:
            msg = "❌ Không tìm thấy file gbaowvminh.txt."
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(msg), style="color", color="#DB342E", auto_format=False),
                MessageStyle(offset=0, length=len(msg), style="bold", auto_format=False),
            ])
            client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=TTL_CMD)
            return

        if not content:
            msg = "⚠️ File gbaowvminh.txt trống."
            styles = MultiMsgStyle([
                MessageStyle(offset=0, length=len(msg), style="color", color="#DB342E", auto_format=False),
                MessageStyle(offset=0, length=len(msg), style="bold", auto_format=False),
            ])
            client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=TTL_CMD)
            return

        is_treo_running = True
        treo_color_index[thread_id] = 0

        def loop_send():
            while is_treo_running:
                idx = treo_color_index.get(thread_id, 0) % len(COLORS)
                color = COLORS[idx]
                admin_name = "ADMIN"
                tag_text = f"@{admin_name}"
                full_text = f"{tag_text}\n{content}"

                mention = Mention(uid=str(ADMIN), length=len(tag_text), offset=0, auto_format=False)
                multi_mention = MultiMention([mention])

                styles = MultiMsgStyle([
                    MessageStyle(offset=0, length=len(tag_text), style="color", color="#DB342E", auto_format=False),
                    MessageStyle(offset=0, length=len(tag_text), style="bold", auto_format=False),
                    MessageStyle(offset=len(tag_text) + 1, length=len(content), style="color", color=f"#{color}", auto_format=False),
                ])

                try:
                    client.send(Message(text=full_text, mention=multi_mention, style=styles), thread_id, thread_type,ttl=60000*5)
                except Exception:
                    pass

                treo_color_index[thread_id] = (idx + 1) % len(COLORS)
                time.sleep(20)

        t = threading.Thread(target=loop_send, daemon=True)
        treo_threads[thread_id] = t
        t.start()

        msg = "🥀 Bot Đã Bắt Đầu Treo!"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(msg), style="color", color="#15A85F", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="bold", auto_format=False),
        ])
        client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=TTL_CMD)
        return

    msg = f"Sai cú pháp! Dùng: {PREFIX}treo on/stop"
    styles = MultiMsgStyle([
        MessageStyle(offset=0, length=len(msg), style="color", color="#DB342E", auto_format=False),
        MessageStyle(offset=0, length=len(msg), style="bold", auto_format=False),
    ])
    client.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type, ttl=TTL_CMD)


def TQD():
    return {
        'treo': handle_treo_command
    }