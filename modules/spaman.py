from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import PREFIX, ADMIN
ADMIN_ID = ADMIN

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "spam ẩn",
    'power': "Quản trị viên Bot"
}

import time

spam_active = {}

def handle_span_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        msg = "• Bạn không có quyền sử dụng lệnh này. Chỉ có admin Latte mới được sử dụng lệnh này"
        client.replyMessage(Message(text=msg), message_object, thread_id, thread_type, ttl=12000)
        return

    if not message_object.quote:
        client.replyMessage(Message(text="• Vui lòng quote một tin nhắn để spam."), message_object, thread_id, thread_type, ttl=12000)
        return

    msg2undo = message_object.quote
    msg_id = msg2undo.globalMsgId
    cli_msg_id = msg2undo.cliMsgId
    msg2del = message_object.quote
    action = "/-flag"
    
    spam_active[thread_id] = True
    
    try:
        while spam_active.get(thread_id, False):
            client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
            client.deleteGroupMsg(msg2del.globalMsgId, msg2del.ownerId, msg2del.cliMsgId, thread_id)
            client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)            
            client.deleteGroupMsg(msg2del.globalMsgId, msg2del.ownerId, msg2del.cliMsgId, thread_id)            
            client.undoMessage(msg_id, cli_msg_id, thread_id, thread_type)
            client.deleteGroupMsg(msg2del.globalMsgId, msg2del.ownerId, msg2del.cliMsgId, thread_id)            
            client.undoMessage(msg_id, cli_msg_id, thread_id, thread_type)            
            client.deleteGroupMsg(msg2del.globalMsgId, msg2del.ownerId, msg2del.cliMsgId, thread_id)            
            client.undoMessage(msg_id, cli_msg_id, thread_id, thread_type)            
            client.sendReaction(message_object, action, thread_id, thread_type, reactionType=75)
            client.undoMessage(msg_id, cli_msg_id, thread_id, thread_type)
            
            
    except Exception as e:
        print(f'Error: {e}')
        client.replyMessage(Message(text=f"• Đã xảy ra lỗi: {e}"), message_object, thread_id, thread_type, ttl=12000)
    finally:
        spam_active.pop(thread_id, None)

def handle_stop_command(message, message_object, thread_id, thread_type, author_id, client):
    if author_id not in ADMIN:
        msg = "• Bạn không có quyền sử dụng lệnh này."
        client.replyMessage(Message(text=msg), message_object, thread_id, thread_type, ttl=12000)
        return

    if thread_id in spam_active:
        spam_active[thread_id] = False
        client.replyMessage(Message(text="• Đã dừng spam trong thread này."), message_object, thread_id, thread_type, ttl=12000)
    else:
        client.replyMessage(Message(text="• Không có hoạt động spam nào đang chạy trong thread này."), message_object, thread_id, thread_type, ttl=12000)

def TQD():
    return {
        'wh': handle_span_command,
        'stopwh': handle_stop_command
    }