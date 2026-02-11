from zlapi.models import Message
from config import ADMIN
ADMIN_ID = ADMIN

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Kick bản thân ra khỏi nhóm",
    'power': "Thành viên"
}

def handle_kickme_command(message, message_object, thread_id, thread_type, author_id, client):
    group_data = client.fetchGroupInfo(thread_id).gridInfoMap[thread_id]
    admins = group_data.adminIds
    owners = group_data.creatorId
    
    if client.uid not in admins and client.uid != owners:
        msg = "Đưa T Key Bạc 🗝️, T Kick Cho Sếp Xem"
        client.replyMessage(Message(text=msg), message_object, thread_id, thread_type, ttl=60000)
        client.sendReaction(message_object, "🚫", thread_id, thread_type, reactionType=75)
        return
    
    if author_id in admins or author_id == owners:
        msg = "cha ơi cha! Không thể kick key bạc 🗝️ hay key vàng ✨ nha!"
        client.replyMessage(Message(text=msg), message_object, thread_id, thread_type, ttl=60000)
        client.sendReaction(message_object, "🚫", thread_id, thread_type, reactionType=75)
        return
    
    user_info = client.fetchUserInfo(author_id)
    user_name = user_info.changed_profiles[author_id].zaloName
    
    client.kickUsersInGroup(author_id, thread_id)
    
    msg = f"Báo đại ca, {user_name} đã bị sút khỏi nhóm. ✅"
    client.send(Message(text=msg), thread_id, thread_type, ttl=60000)
    client.sendReaction(message_object, "✅", thread_id, thread_type, reactionType=75)

def TQD():
    return {
        'kickme': handle_kickme_command
    }