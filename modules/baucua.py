import json
import secrets
import random
import os
from PIL import Image
from zlapi.models import *
from config import PREFIX

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Chơi game Bầu Cua",
    'power': "Thành viên"
}

game_history = []

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

def merge_images(image_paths, output_path):
    images = [Image.open(img) for img in image_paths]
    total_width = sum(img.width for img in images)
    max_height = max(img.height for img in images)

    new_image = Image.new('RGB', (total_width, max_height))
    x_offset = 0

    for img in images:
        new_image.paste(img, (x_offset, 0))
        x_offset += img.width

    new_image.save(output_path)

def secrets_choice(options, weights):
    total = sum(weights)
    r = secrets.randbelow(total)
    for i, weight in enumerate(weights):
        r -= weight
        if r < 0:
            return options[i]
    return options[-1]

def handle_baucua_command(message, message_object, thread_id, thread_type, author_id, client):
    global game_history
    text = message.split()
    money_data = load_money_data()
    response_message = ""
    data_trave = ""
    dice_results = []
    baucua_options = ["bầu", "cua", "tôm", "cá", "gà", "nai"]
    weights = [15, 15, 20, 20, 15, 15]

    if len(text) < 3 or len(text) % 2 == 0:
        response_message = (
            "🎲 HƯỚNG DẪN CHƠI BẦU CUA CỦA LATTE 🎲\n\n"
            "👉 Cách chơi:\n"
            "➜ Chọn từ 1 đến 3 con: Bầu, Cua, Tôm, Cá, Gà, Nai.\n"
            "➜ Đặt cược số tiền cho mỗi con (hoặc 'all' để cược hết, hoặc % số dư).\n"
            "➜ Kết quả dựa trên 3 xúc xắc, thắng nhận thưởng theo số lần xuất hiện.\n\n"
            "📜 Cú pháp:\n"
            f"{PREFIX}bc <con1> <tiền1> [con2 tiền2] [con3 tiền3]\n\n"
            "🔹 Ví dụ:\n"
            f"➜  {PREFIX}bc cua 100K\n"
            f"➜  {PREFIX}bc bầu 1M cua 200K\n"
            f" {PREFIX}bc tôm 500K cá 50% gà all\n\n"
            "💡 Lưu ý:\n"
            "➜ Số tiền cược phải lớn hơn 0 và không vượt quá số dư.\n"
            "➜ Nhập đúng tên con (không phân biệt hoa/thường).\n\n"
            "📩 Vui lòng thử lại với lệnh hợp lệ!"
        )
    else:
        bets = []
        i = 1
        while i < len(text):
            if i + 1 >= len(text):
                response_message = "➜ Lỗi: Thiếu số tiền cho con cuối cùng."
                break
            choice = text[i].lower()
            bet_amount_text = text[i + 1]
            if choice not in baucua_options:
                response_message = (
                    "➜  LỖI NHẬP LỆNH BẦU CUA TÔM CÁ CỦA LATTE\n\n"
                    f"❌ Con '{choice}' không hợp lệ!\n"
                    "👉 Chỉ được chọn: Bầu, Cua, Tôm, Cá, Gà, Nai.\n\n"
                    "📜 Cú pháp đúng:\n"
                    f"{PREFIX}bc <con1> <tiền1> [con2 tiền2] [con3 tiền3]\n\n"
                    "🔹 Ví dụ:\n"
                    f"➜ {PREFIX}bc cua 100K\n"
                    f"➜  {PREFIX}bc bầu 1M cua 200K\n"
                    f"➜  {PREFIX}bc tôm 500K cá 50% gà all\n\n"
                    "📩 Vui lòng nhập lại lệnh chính xác!"
                )
                break
            current_balance = money_data.get(str(author_id), 0)
            bet_amount, error = parse_bet_amount(bet_amount_text, current_balance)
            if error:
                response_message = error
                break
            if bet_amount > current_balance:
                response_message = f"➜ Số dư của bạn không đủ để đặt cược {format_money(bet_amount)} cho {choice.capitalize()}."
                break
            if bet_amount <= 0:
                response_message = f"➜ Số tiền cược cho {choice.capitalize()} phải lớn hơn 0."
                break
            bets.append((choice, bet_amount))
            i += 2

        if not response_message and len(bets) > 3:
            response_message = "➜ Chỉ được đặt tối đa 3 con."

        if not response_message:
            max_attempts = 5
            for _ in range(max_attempts):
                dice_results = [secrets_choice(baucua_options, weights) for _ in range(3)]
                if len(set(dice_results)) == 1 and secrets.randbelow(100) < 80:
                    continue
                if tuple(dice_results) not in game_history:
                    break
            else:
                dice_results = [secrets_choice(baucua_options, weights) for _ in range(3)]

            game_history.append(tuple(dice_results))
            if len(game_history) > 3:
                game_history.pop(0)

            total_bet = sum(bet[1] for bet in bets)
            total_received = 0
            win_details = []

            for choice, bet_amount in bets:
                win_count = dice_results.count(choice)
                if win_count > 0:
                    reward = bet_amount * (win_count + 1)  # Vốn + thưởng
                    total_received += reward
                    win_details.append(
                        f"➜ {choice.capitalize()}: cược {format_money(bet_amount)}, "
                        f"x{win_count}, nhận {format_money(reward)}"
                    )
                else:
                    win_details.append(
                        f"➜ {choice.capitalize()}: cược {format_money(bet_amount)}, "
                        f"mất {format_money(bet_amount)}"
                    )

            if total_received > total_bet:
                outcome = "thắng"
                
            elif total_received == total_bet:
                outcome = "hòa vốn"
                
            else:
                outcome = "thua"
                

            money_data[str(author_id)] = money_data.get(str(author_id), 0) + total_received - total_bet
            save_money_data(money_data)
            author_name = get_user_name(client, author_id)

            bet_text = ", ".join([f"{bet[0].capitalize()} {format_money(bet[1])}" for bet in bets])
            win_detail_text = "\n".join(win_details) if win_details else "➜ Không trúng con nào."
            data_trave = (
                f"[ Đây là kết quả chơi bẩu cua Latte của : {author_name} ]\n\n"
                f"➜ Bạn đã đặt cược: {bet_text}\n"
                f"➜ Kết quả trả về:\n"
                f"➜ Bầu cua 1: {dice_results[0].capitalize()}\n"
                f"➜ Bầu cua 2: {dice_results[1].capitalize()}\n"
                f"➜ Bầu cua 3: {dice_results[2].capitalize()}\n"
                f"➜ Kết quả cược: {outcome}\n"
                f"{win_detail_text}\n"                
            )
            gui = Message(text=data_trave)

    client.replyMessage(Message(text=response_message), message_object, thread_id, thread_type, ttl=240000)

    if dice_results:
        image_paths = [f'modules/baucua/{result}.jpg' for result in dice_results]
        merged_image_path = "modules/baucua/merged_baucua.jpg"

        if all(os.path.exists(path) for path in image_paths):
            merge_images(image_paths, merged_image_path)

            client.sendLocalImage(
                imagePath=merged_image_path,
                message=gui,
                thread_id=thread_id,
                thread_type=thread_type,
                width=921,
                height=308,
                ttl=240000
            )
            os.remove(merged_image_path)
        else:
            response_message += "\n➜ Không thể hiển thị hình ảnh kết quả do thiếu hình ảnh bầu cua."
            client.replyMessage(Message(text=response_message), message_object, thread_id, thread_type, ttl=60000)

def TQD():
    return {
        'baucua': handle_baucua_command,
        'bc': handle_baucua_command
    }