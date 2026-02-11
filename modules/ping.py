from zlapi.models import *
import time
from concurrent.futures import ThreadPoolExecutor
import threading
import os
import random

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Xem ping của bot",
    'power': "Thành viên"
}

def ping(message, message_object, thread_id, thread_type, author_id, self):
        start_time = time.time()
        reply_message = Message("Pinging Cutii Check Độ trễ >.<...🐰")
        self.replyMessage(reply_message, message_object, thread_id, thread_type,ttl=30000)

        end_time = time.time()
        ping_time = end_time - start_time

        image_dir = "background"
        image_files = [f for f in os.listdir(image_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
        random_image = random.choice(image_files)
        image_path = os.path.join(image_dir, random_image)

        text = f"🎾 𝘿𝙪̛𝙤̛𝙣𝙜 Ơi ! Delay Của Bot Hiện Tại Là : {ping_time:.2f}ms"
        self.sendLocalImage(imagePath=image_path, thread_id=thread_id, thread_type=thread_type, ttl=60000, message=Message(text))

def TQD():
    return {
    'ping': ping
    }
