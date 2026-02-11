from config import PREFIX
from zlapi.models import Message
import json, time

des = {
    'version': "2.0.1",
    'credits': "T Q D",
    'description': "check prefix",
    'power': "Thành viên"
}


user_notified = {}

def prf():
    with open('seting.json', 'r') as f:
        return json.load(f).get('prefix')

def checkprefix(message, message_object, thread_id, thread_type, author_id, client):
           
    
    user_notified[author_id] = False
    
    
    gui = Message(text=f"🚦Prefix hiện tại của bot là: {prf()}")
    client.replyMessage(gui, message_object, thread_id, thread_type, ttl=20000)

def TQD():
    return {
        'prefix': checkprefix
    }