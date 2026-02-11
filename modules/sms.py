import datetime
import os
import subprocess
import threading
import time
from zlapi.models import MultiMsgStyle, MessageStyle, Message

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Spam SMS",
    'power': "Thành viên"
}

admin_ids = ['2143747344068352058']
last_sms_times = {}
current_processing_number = None


def run_spam_in_thread(client, message_object, thread_id, thread_type, author_id, attack_phone_number, number_of_times, is_admin, msg_style):
    """
    Hàm chạy riêng trong luồng phụ để thực hiện spam
    """
    global current_processing_number

    try:
        masked_number = f"{attack_phone_number[:3]}***{attack_phone_number[-3:]}"
        time_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        process = subprocess.Popen(
            ["python3", os.path.join(os.getcwd(), "smsv2.py"), attack_phone_number, str(number_of_times)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        process.wait()  # chạy độc lập, không chặn bot chính

        msg_end = f"""
✅ Spam SMS & Call hoàn tất  
📱 Số điện thoại:  {masked_number}  
⏰ Thời gian:      {time_str}  
♻️ Số lần gửi:     {number_of_times}  
👱 Quản lý:         {'ADMIN' if is_admin else 'NGUOI DUNG'}
"""
        client.replyMessage(
            Message(text=msg_end.strip(), style=msg_style),
            message_object, thread_id, thread_type, ttl=15000
        )

    except Exception as e:
        client.replyMessage(
            Message(text=f"⚠️ Lỗi trong luồng spam: {str(e)}"),
            message_object, thread_id, thread_type, ttl=10000
        )
    finally:
        current_processing_number = None  # reset sau khi xong


def handle_sms_command(message, message_object, thread_id, thread_type, author_id, client):
    global current_processing_number

    try:
        is_admin = author_id in admin_ids
        parts = message.strip().split()
        if len(parts) < 3:
            client.replyMessage(Message(text='🚫 Vui lòng nhập số điện thoại và số lần spam.'),
                                message_object, thread_id=thread_id, thread_type=thread_type, ttl=8000)
            return

        attack_phone_number = parts[1]

        if attack_phone_number in ['113', '911', '114', '115']:
            client.replyMessage(Message(text="🚫 Số này không thể spam."),
                                message_object, thread_id=thread_id, thread_type=thread_type)
            return

        try:
            number_of_times = int(parts[2])
        except ValueError:
            client.replyMessage(Message(text='❌ Số lần spam phải là số nguyên hợp lệ!'),
                                message_object, thread_id=thread_id, thread_type=thread_type, ttl=8000)
            return

        if not (attack_phone_number.isnumeric() and len(attack_phone_number) == 10):
            client.replyMessage(Message(text='❌ Số điện thoại không hợp lệ! Phải đúng 10 chữ số.'),
                                message_object, thread_id=thread_id, thread_type=thread_type, ttl=8000)
            return

        if current_processing_number:
            client.replyMessage(Message(text=f"⏳ Đang xử lý số {current_processing_number}, vui lòng đợi xong!"),
                                message_object, thread_id=thread_id, thread_type=thread_type, ttl=8000)
            return

        if not is_admin and number_of_times > 10:
            client.replyMessage(Message(text="🚫 Thành viên chỉ được spam tối đa 10 lần!"),
                                message_object, thread_id=thread_id, thread_type=thread_type, ttl=8000)
            return

        current_time = datetime.datetime.now()

        # cooldown 60s
        if not is_admin:
            if author_id in last_sms_times and (current_time - last_sms_times[author_id]).total_seconds() < 60:
                remaining = int(60 - (current_time - last_sms_times[author_id]).total_seconds())
                client.replyMessage(Message(text=f"⏳ Vui lòng đợi {remaining} giây trước khi spam tiếp!"),
                                    message_object, thread_id=thread_id, thread_type=thread_type, ttl=8000)
                return
            last_sms_times[author_id] = current_time

        current_processing_number = attack_phone_number

        masked_number = f"{attack_phone_number[:3]}***{attack_phone_number[-3:]}"
        time_str = current_time.strftime("%d/%m/%Y %H:%M:%S")

        msg_start = f"""
🚀 Bắt đầu spam 
📱 Số điện thoại:  {masked_number}  
⏰ Thời gian:      {time_str}  
♻️ Số lần gửi:     {number_of_times}  
👱 Quản lý:         {'ADMIN' if is_admin else 'NGUOI DUNG'}
"""
        style = MultiMsgStyle([MessageStyle(style="color", color="#4caf50", length=len(msg_start), offset=0)])
        client.replyMessage(
            Message(text=msg_start.strip(), style=style),
            message_object, thread_id, thread_type, ttl=8000
        )

        # ⚡ chạy spam trong luồng riêng
        t = threading.Thread(
            target=run_spam_in_thread,
            args=(client, message_object, thread_id, thread_type, author_id, attack_phone_number, number_of_times, is_admin, style),
            daemon=True
        ) 
        t.start()

    except Exception as e:
        current_processing_number = None
        client.replyMessage(Message(text=f"⚠️ Có lỗi xảy ra: {str(e)}"),
                            message_object, thread_id=thread_id, thread_type=thread_type, ttl=10000)


def TQD():
    return {
        'spsms': handle_sms_command
    }
