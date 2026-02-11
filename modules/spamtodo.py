import time
from zlapi.models import Message, ThreadType
from config import ADMIN
from config import PREFIX

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Gửi spam công việc cho người dùng được tag",
    'power': "Quản trị viên Bot"
}

def handle_spamtodo_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        client.replyMessage(
            Message(text="Bạn Không Có Quyền. Chỉ có admin Latte mới được sử dụng lệnh này"),
            message_object, thread_id, thread_type
        )
        return

    if not message_object.mentions:
        response_message = "Vui lòng tag người dùng để giao công việc."
        client.replyMessage(Message(text=response_message), message_object, thread_id, thread_type)
        return

    tagged_user = message_object.mentions[0]['uid']
    parts = message.split(' ', 2)
    
    if len(parts) < 3:
        response_message = f"Vui lòng cung cấp nội dung và số lần spam công việc. Ví dụ: {PREFIX}spamtodo @nguoitag Nội dung công việc 5"
        client.replyMessage(Message(text=response_message), message_object, thread_id, thread_type)
        return

    try:
        content_and_count = message.split(' ', 2)[2]
        content, num_repeats_str = content_and_count.rsplit(' ', 1)
        num_repeats = int(num_repeats_str)
    except ValueError:
        response_message = "Số lần phải là một số nguyên."
        client.replyMessage(Message(text=response_message), message_object, thread_id, thread_type)
        return

    for _ in range(num_repeats):
        client.sendToDo(
            message_object=message_object,
            content=content,
            assignees=[tagged_user],
            thread_id=tagged_user,
            thread_type=ThreadType.USER,
            due_date=-1,
            description="T Q D"
        )
        
        client.sendToDo(
                message_object=message_object,
                content=content,
                assignees=[tagged_user],
                thread_id=thread_id,
                thread_type=thread_type,
                due_date=-1,
                description="T Q D"
        )

        time.sleep(0.0)

def TQD():
    return {
        'spamtodo': handle_spamtodo_command
    }