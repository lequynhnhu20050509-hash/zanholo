import json
import random
import os
from PIL import Image
from zlapi.models import Message, Mention
import time
from config import PREFIX

des = {
    'version': '2.0.1',
    'credits': "Latte",
    'description': 'Chơi kéo búa bao!',
    'power': 'Thành viên'
}

def load_money_data():
    try:
        with open('modules/cache/money.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_money_data(data):
    with open('modules/cache/money.json', 'w') as f:
        json.dump(data, f, indent=4)

def format_money(amount):
    abs_amt = abs(amount)
    if abs_amt >= 1_000_000_000_000:
        return f"{int(amount/1_000_000_000_000)}BB"
    elif abs_amt >= 1_000_000_000:
        return f"{int(amount/1_000_000_000)}B"
    elif abs_amt >= 1_000_000:
        return f"{int(amount/1_000_000)}M"
    elif abs_amt >= 1_000:
        return f"{int(amount/1_000)}K"
    else:
        return f"{amount}"

def parse_bet_amount(text, current_balance):
    text = text.lower().strip()
    if text == "all":
        return current_balance, None
    if text.endswith('%'):
        try:
            percent = float(text[:-1])
            if 1 <= percent <= 100:
                return int(current_balance * (percent / 100)), None
            else:
                return 0, "➜ Phần trăm phải từ 1% đến 100%."
        except ValueError:
            return 0, "➜ Phần trăm không hợp lệ."
    
    multiplier = 1
    if text.endswith('k'):
        multiplier = 1_000
        text = text[:-1]
    elif text.endswith('m'):
        multiplier = 1_000_000
        text = text[:-1]
    elif text.endswith('b'):
        multiplier = 1_000_000_000
        text = text[:-1]
    elif text.endswith('bb'):
        multiplier = 1_000_000_000_000
        text = text[:-2]
    
    try:
        amount = int(float(text) * multiplier)
        if amount <= 0:
            return 0, "➜ Số tiền cược phải lớn hơn 0."
        return amount, None
    except (ValueError, TypeError):
        return 0, "➜ Số tiền không hợp lệ. Ví dụ: 100K, 1M, 1B, 1BB"

def get_user_name(client, user_id):
    try:
        user_info = client.fetchUserInfo(user_id)
        profile = user_info.changed_profiles.get(user_id, {})
        user_name = profile.get('zaloName', 'Không xác định')
    except AttributeError:
        user_name = 'Không xác định'
    return user_name

def merge_images(image_paths, output_path, target_height=308):
    images = [Image.open(img) for img in image_paths]
    resized_images = []

    for img in images:
        height_percent = (target_height / float(img.size[1]))
        width_size = int((float(img.size[0]) * float(height_percent)))
        img = img.resize((width_size, target_height), Image.Resampling.LANCZOS)
        resized_images.append(img)

    total_width = sum(img.width for img in resized_images)
    max_height = target_height
    new_image = Image.new('RGB', (total_width, max_height))
    x_offset = 0

    for img in resized_images:
        new_image.paste(img, (x_offset, 0))
        x_offset += img.width

    new_image.save(output_path)

def handle_kbb_command(message, message_object, thread_id, thread_type, author_id, bot):
    text = message.split()
    money_data = load_money_data()
    response_message = ""
    data_trave = ""
    kbb_results = []

    if len(text) != 3 or text[1].lower() not in ["kéo", "búa", "bao"]:
        response_message = (
            "✌️ HƯỚNG DẪN CHƠI KÉO BÚA BAO CỦA LATTE ✌️\n\n"
            "👉 Cách chơi:\n"
            "➜ Chọn một trong ba: Kéo, Búa, Bao.\n"
            "➜ Đặt cược số tiền (hoặc 'all' để cược hết, hoặc % số dư).\n"
            "➜ Thắng nhận gấp đôi tiền cược, hòa không mất tiền, thua mất tiền cược.\n\n"
            "📜 Cú pháp:\n"
            f"{PREFIX}kbb <kéo|búa|bao> <số tiền hoặc all hoặc % số dư>\n\n"
            "🔹 Ví dụ:\n"
            f"➜ {PREFIX}kbb kéo 100K\n"
            f"➜ {PREFIX}kbb búa 1M\n"
            f"➜ {PREFIX}kbb bao 50%\n"
            f"➜ {PREFIX}kbb kéo all\n\n"
            "💡 Lưu ý:\n"
            "➜ Số tiền cược phải lớn hơn 0 và không vượt quá số dư.\n"
            "➜ Nhập đúng lựa chọn (kéo, búa, bao, không phân biệt hoa/thường).\n\n"
            "📩 Vui lòng thử lại với lệnh hợp lệ!"
        )
    else:
        choice = text[1].lower()
        current_balance = money_data.get(str(author_id), 0)
        bet_amount, error = parse_bet_amount(text[2], current_balance)
        if error:
            response_message = error
        else:
            if bet_amount > current_balance:
                response_message = f"➜ Số dư của bạn không đủ để đặt cược {format_money(bet_amount)}."
            elif bet_amount <= 0:
                response_message = f"➜ Số tiền cược phải lớn hơn 0."
            else:
                kbb_options = ["kéo", "búa", "bao"]
                bot_choice = random.choice(kbb_options)
                
                if (choice == "kéo" and bot_choice == "bao") or (choice == "bao" and bot_choice == "búa") or (choice == "búa" and bot_choice == "kéo"):
                    money_data[str(author_id)] = current_balance + bet_amount * 2
                    response = f"Đã cộng {format_money(bet_amount * 2)} vào số dư.\n"
                    outcome = "thắng"
                elif choice == bot_choice:
                    response = f"Hòa, không mất tiền.\n"
                    outcome = "hòa"
                else:
                    money_data[str(author_id)] = current_balance - bet_amount
                    response = f"Đã trừ {format_money(bet_amount)} khỏi số dư.\n"
                    outcome = "thua"
                save_money_data(money_data)
                author_name = get_user_name(bot, author_id)
                data_trave = (
                    f"[ {author_name} ]\n\n"
                    f"   ➜ Bạn đã đặt cược {format_money(bet_amount)} vào {choice.capitalize()}.\n"
                    f"   ➜ Bot đã chọn {bot_choice.capitalize()}.\n"
                    f"   ➜ Bạn đã {outcome}\n"
                    f"   ➜ {response}"
                )
                gui = Message(text=data_trave)

    bot.replyMessage(Message(text=response_message), message_object, thread_id, thread_type, ttl=60000)

    if data_trave:
        image_paths = [f'modules/kbb/{choice}.png', f'modules/kbb/vs.png', f'modules/kbb/{bot_choice}.png']
        merged_image_path = "modules/kbb/merged_kbb.jpg"
        if all(os.path.exists(path) for path in image_paths):
            merge_images(image_paths, merged_image_path)

            bot.sendLocalImage(
                imagePath=merged_image_path,
                message=gui,
                thread_id=thread_id,
                thread_type=thread_type,
                width=921,
                height=308,
                ttl=60000
            )
            os.remove(merged_image_path)
        else:
            response_message += "\n• Không thể hiển thị hình ảnh kết quả do thiếu hình ảnh KBB."
            bot.replyMessage(Message(text=response_message), message_object, thread_id, thread_type, ttl=30000)

def TQD():
    return {
        'kbb': handle_kbb_command
    }