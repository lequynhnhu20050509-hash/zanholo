from zlapi.models import *
import os
import time
import threading
import logging
from zlapi.models import MultiMsgStyle, MessageStyle, MultiMention, Mention, ThreadType
from config import ADMIN
from config import PREFIX

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

spall_threads = {}

spall_data = {
    "delay": 0.3,
    "content": {}
}

max_messages = 99999
max_duration = 300

MINIMAL_SLEEP_BETWEEN_SENDS = 0
SLEEP_ON_SEND_ERROR = 0

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Spam all.",
    'power': "admin"
}

def check_group_access(thread_id, sender_id):
    return sender_id in ADMIN

def stop_spall(client, message_object, thread_id, thread_type, reply_message=True):
    thread_info = spall_threads.get(thread_id)

    if thread_info:
        logging.info(f"Signaling spall thread for {thread_id} to stop.")
        stop_event, thread = thread_info
        
        stop_event.set()  
        
        logging.info(f"Signaled thread {thread_id}. Waiting for it to join (max 5s)...")
        thread.join(timeout=5) 
        logging.info(f"Spall thread for {thread_id} join attempted.")
        
        if thread_id not in spall_threads: 
             logging.info(f"Spall thread {thread_id} state confirmed cleaned.")
             if reply_message:
                client.replyMessage(Message(text="🚦Đã dừng spam all."), message_object, thread_id, thread_type, ttl=60000)
        else:
             logging.warning(f"Spall thread {thread_id} state still found after join. Might be stuck.")
             if reply_message:
                client.replyMessage(Message(text="🚦Đã gửi tín hiệu dừng spam all. Vui lòng chờ luồng kết thúc."), message_object, thread_id, thread_type, ttl=60000)

    else:
        logging.info(f"No spall thread found for {thread_id} to stop.")
        if thread_id in spall_data["content"]:
             del spall_data["content"][thread_id]
             logging.info(f"Cleaned up orphaned content for {thread_id}.")
             
        if reply_message:
             client.replyMessage(Message(text="❌️ Không có lệnh spall nào đang chạy trong nhóm này."), message_object, thread_id, thread_type, ttl=60000)

def send_spall(client_instance, thread_id, thread_type, stop_event):
    start_time = time.time()
    
    try:
        content = spall_data["content"].get(thread_id) 
        
        if not content:
            logging.warning(f"Spall thread for {thread_id}: No content. Exiting.")
            return 

        members = []
        try:
            logging.info(f"Spall thread for {thread_id}: Fetching members...")
            group_info = client_instance.fetchGroupInfo(thread_id).gridInfoMap.get(thread_id)
            if group_info and 'memVerList' in group_info:
                 members = group_info['memVerList']
            
            if not members:
                logging.warning(f"Spall thread for {thread_id}: No members found. Exiting.")
                client_instance.replyMessage(Message(text="🚦Không tìm thấy thành viên trong nhóm để tag."), None, thread_id, thread_type, ttl=60000)
                return 
            logging.info(f"Spall thread for {thread_id}: Fetched {len(members)} members.")

        except Exception as e:
            logging.error(f"Spall thread for {thread_id}: Error fetching members: {e}", exc_info=True)
            client_instance.replyMessage(Message(text=f"❌️ Lỗi khi lấy danh sách thành viên: {e}"), None, thread_id, thread_type, ttl=60000)
            return 

        count = 0  
        current_delay = spall_data.get("delay", 0) 
        logging.info(f"Spall thread for {thread_id}: Starting send loop with delay {current_delay}s/msg + minimal {MINIMAL_SLEEP_BETWEEN_SENDS}s...")

        while not stop_event.is_set() and (time.time() - start_time) < max_duration and count < max_messages:  
            try:  
                text = f"<b>{content}</b>"  
                mentions = []  
                offset = len(text)
                
                if members: 
                     for member_str in members:  
                        parts = member_str.split('_', 1) 
                        if len(parts) != 2:
                             logging.warning(f"Spall thread for {thread_id}: Invalid member format: {member_str}")
                             continue
                        user_id, user_name = parts  
                        
                        display_text = "@" + user_name + " "
                        
                        mention = Mention(uid=user_id, offset=offset, length=len(display_text), auto_format=False)  
                        mentions.append(mention)  
                        
                        offset += len(display_text)
                     
                multi_mention = MultiMention(mentions) if mentions else None 
                
                client_instance.send(  
                    Message(text=text, mention=multi_mention, parse_mode="HTML"),  
                    thread_id=thread_id,  
                    thread_type=ThreadType.GROUP  
                )  
                count += 1  
                
                if current_delay > 0:
                    time.sleep(current_delay)  
                else:
                    time.sleep(MINIMAL_SLEEP_BETWEEN_SENDS)
                    
            except Exception as e:  
                logging.error(f"Spall thread for {thread_id}: Error sending message (sent {count}): {e}", exc_info=True)
                time.sleep(SLEEP_ON_SEND_ERROR)
                pass 

        logging.info(f"Spall thread for {thread_id} send loop finished. Sent {count} messages.")

    finally:
        logging.info(f"Spall thread for {thread_id} finally block reached. Attempting state cleanup.")
        thread_info = spall_threads.pop(thread_id, None)
        if thread_info:
            logging.info(f"Removed {thread_id} from spall_threads dictionary.")
        else:
            logging.warning(f"{thread_id} not found in spall_threads dictionary during cleanup. State mismatch?")

        content_removed = spall_data["content"].pop(thread_id, None)
        if content_removed is not None:
             logging.info(f"Removed content for {thread_id} from spall_data.")
        else:
             logging.warning(f"Content for {thread_id} not found in spall_data during cleanup. State mismatch?")

        logging.info(f"Spall thread for {thread_id} state cleanup attempt complete.")


def handle_spall_command(message, message_object, thread_id, thread_type, author_id, client):
    if not check_group_access(thread_id, author_id):
        client.replyMessage(
            Message(text="🚦Bạn không có quyền sử dụng lệnh này."),
            message_object, thread_id, thread_type, ttl=60000
        )
        return

    command_parts = message.split(maxsplit=2)  
    action = command_parts[1].lower() if len(command_parts) > 1 else None

    if action == "stop":  
        stop_spall(client, message_object, thread_id, thread_type, reply_message=True)  
        return  

    if action == "delay":  
        try:  
            if len(command_parts) > 2:  
                delay_value_str = command_parts[2].strip()
                delay_value_str = delay_value_str.replace(',', '.')
                delay_value = float(delay_value_str)
                
                if delay_value >= 0:  
                    spall_data["delay"] = delay_value  
                    client.replyMessage(Message(text=f"🚦Đã đặt độ trễ spall: {delay_value} giây."), message_object, thread_id, thread_type, ttl=60000)  
                else:  
                    client.replyMessage(Message(text="❌️ Độ trễ phải là số không âm."), message_object, thread_id, thread_type, ttl=60000)  
            else:  
                current_delay = spall_data.get("delay", 0)
                client.replyMessage(Message(text=f"🚨Độ trễ spall hiện tại: {current_delay} giây. Cú pháp đặt: {PREFIX}spall delay <giây>"), message_object, thread_id, thread_type, ttl=60000)
        except ValueError:
            client.replyMessage(Message(text=f"🚨Sai cú pháp độ trễ. Độ trễ phải là số (vd: {PREFIX}spall delay 0.5 hoặc {PREFIX}spall delay 0)."), message_object, thread_id, thread_type, ttl=60000)  
        return  

    content = message.split(maxsplit=1)[1].strip() if len(message.split(maxsplit=1)) > 1 else ""

    if not content:  
        client.replyMessage(Message(text=f"🚨 Vui lòng cung cấp nội dung để spam. Cú pháp: {PREFIX}spall <nội dung>"), message_object, thread_id, thread_type, ttl=60000)  
        return  

    if thread_id in spall_threads:  
        logging.info(f"Found existing spall thread for {thread_id}. Signaling it to stop before starting new one.")
        stop_spall(client, message_object, thread_id, thread_type, reply_message=False) 

    spall_data["content"][thread_id] = content  

    stop_event = threading.Event()  
    thread = threading.Thread(target=send_spall, args=(client, thread_id, thread_type, stop_event))  
    thread.daemon = True  
    thread.start()  
    
    spall_threads[thread_id] = (stop_event, thread)  
    
    current_delay = spall_data.get("delay", 0.0)
    client.replyMessage(Message(text=f"🚦Bắt đầu spam all: '{content}' với độ trễ {current_delay}s/tin + tối thiểu {MINIMAL_SLEEP_BETWEEN_SENDS}s! (Dừng sau {max_duration}s, {max_messages} tin nhắn, hoặc {PREFIX}spall stop)"), message_object, thread_id, thread_type, ttl=60000)
    logging.info(f"Started new spall thread for {thread_id} with content '{content}'")


def TQD():
    return {
        'spall': handle_spall_command
    }