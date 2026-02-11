import time
from zlapi.models import Message, Mention, MultiMention
from config import ADMIN

ADMIN_ID = ADMIN

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Tag tên thành viên trong nhóm",
    'power': "Quản trị viên Bot"
}

def handle_checkid_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        if author_id not in ADMIN_ID:
            client.replyMessage(
                Message(text="• Bạn không có quyền sử dụng lệnh này. Chỉ admin được phép thực hiện."),
                message_object, thread_id, thread_type
            )
            return

        group_info = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
        members = group_info.get('memVerList', [])

        if not members:
            client.replyMessage(
                Message(text="Không có thành viên nào trong nhóm để tag."),
                message_object, thread_id, thread_type
            )
            return

        total_members = len(members)
        max_tag_per_message = 250
        current_index = 0

        while current_index < total_members:
            batch_members = members[current_index:current_index + max_tag_per_message]

            text = "T Q D kêu dậy kìa:\n"
            mentions = []
            offset = len(text)

            for member in batch_members:
                user_id = member.split('_')[0]
                user_name = member.split('_')[1]

                text += f"{user_name} "
                mention = Mention(uid=user_id, offset=offset, length=len(user_name), auto_format=False)
                mentions.append(mention)
                offset += len(user_name) + 1

            multi_mention = MultiMention(mentions)

            client.send(
                Message(text=text, mention=multi_mention),
                thread_id=thread_id,
                thread_type=thread_type
            )

            current_index += max_tag_per_message
            time.sleep(1)

    except Exception as e:
        error_message = f"Lỗi khi thực hiện lệnh tag: {str(e)}"
        client.send(Message(text=error_message), thread_id, thread_type)

def TQD():
    return {
        'tagam': handle_checkid_command
    }