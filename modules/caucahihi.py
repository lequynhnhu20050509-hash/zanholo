import os
import json
import time
import random
import logging
from zlapi.models import Message

# ---------------- MÔ TẢ MODULE ----------------
des = {
    "version": "7.3.0",
    "credits": "Latte",
    "description": "Mini game câu cá săn cá - Mua bằng số + số lượng.",
    "power": "Thành viên"
}

# ---------------- CẤU HÌNH ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PREFIX = "ca "
BASE_DIR = os.path.dirname(__file__)
PLAYER_FILE = os.path.join(BASE_DIR, "players.json")

# ---------------- DỮ LIỆU CƠ BẢN ----------------

fish_pool = [
    {"name": "Cá Mập Máu", "strength": 9, "speed": 8, "rarity": "Hiếm", "desc": "Mạnh mẽ và hung dữ, nổi tiếng trên khắp đại dương."},
    {"name": "Cá Rồng Bất Tử", "strength": 10, "speed": 9, "rarity": "Huyền thoại", "desc": "Cá rồng thần thoại, khó ai có thể bắt được."},
    {"name": "Cá Lốc Tử Thần", "strength": 8, "speed": 7, "rarity": "Hiếm", "desc": "Tốc độ phi thường, dễ dàng thoát khỏi lưỡi câu thường."},
    {"name": "Mực Bóng Ma Nguyên Thủy", "strength": 8, "speed": 7, "rarity": "Hiếm", "desc": "Ẩn mình trong bóng tối, tấn công bất ngờ."},
    {"name": "Cá Chép Vàng", "strength": 2, "speed": 2, "rarity": "Bình thường", "desc": "Cá chép vàng phổ biến, dễ câu."},
    {"name": "Cá Hề Biển Sâu", "strength": 3, "speed": 4, "rarity": "Bình thường", "desc": "Nhỏ nhưng nhanh, thích sống giữa san hô."},
    {"name": "Cá Ngựa Tím", "strength": 4, "speed": 3, "rarity": "Xịn", "desc": "Cá nhỏ nhưng đẹp, hiếm gặp ngoài tự nhiên."},
    {"name": "Cá Voi Xanh", "strength": 12, "speed": 5, "rarity": "Huyền thoại", "desc": "Khổng lồ và hiền lành, khó thấy ngoài biển sâu."},
    {"name": "Cá Sấu Nước Ngọt", "strength": 9, "speed": 6, "rarity": "Hiếm", "desc": "Động vật săn mồi mạnh mẽ ở sông hồ."},
    {"name": "Cá Mú Bóng Đêm", "strength": 6, "speed": 5, "rarity": "Xịn", "desc": "Thích sống ở đáy biển tối."},
    {"name": "Cá Tuyết Bắc Cực", "strength": 5, "speed": 4, "rarity": "Hiếm", "desc": "Sống ở vùng lạnh, khó câu."},
    {"name": "Cá Hổ Đại Dương", "strength": 11, "speed": 8, "rarity": "Hiếm", "desc": "Thân to, săn mồi cực nhanh."},
    {"name": "Cá Mèo Điên", "strength": 4, "speed": 3, "rarity": "Bình thường", "desc": "Cá hiền nhưng dễ nổi giận."},
    {"name": "Cá Bơn Rực Rỡ", "strength": 3, "speed": 2, "rarity": "Bình thường", "desc": "Màu sắc sặc sỡ, thường ở gần bờ."},
    {"name": "Cá Thu Bạc", "strength": 6, "speed": 7, "rarity": "Xịn", "desc": "Nhanh và mạnh, thường bị săn."},
    {"name": "Cá Chình Điên", "strength": 5, "speed": 6, "rarity": "Xịn", "desc": "Thích núp dưới bùn, tấn công bất ngờ."},
    {"name": "Cá Hồng Phát Lộc", "strength": 4, "speed": 3, "rarity": "Bình thường", "desc": "Mang lại may mắn, đẹp mắt."},
    {"name": "Cá Bạc Thần", "strength": 8, "speed": 7, "rarity": "Hiếm", "desc": "Cá thần thoại, khó bắt được."},
    {"name": "Cá Heo Vui Vẻ", "strength": 7, "speed": 8, "rarity": "Xịn", "desc": "Thông minh, thích chơi đùa."},
    {"name": "Cá Vàng Bảy Sắc", "strength": 5, "speed": 4, "rarity": "Xịn", "desc": "Sắc màu thay đổi theo ánh sáng."},
    {"name": "Cá Lươn Sấm", "strength": 6, "speed": 9, "rarity": "Hiếm", "desc": "Nhanh như tia sét, khó bắt."},
    {"name": "Cá Bống Nhiệt Đới", "strength": 2, "speed": 3, "rarity": "Bình thường", "desc": "Cá nhỏ, dễ gặp trong rạn san hô."},
    {"name": "Cá Đuối Huyền Bí", "strength": 9, "speed": 6, "rarity": "Hiếm", "desc": "Ẩn mình ở đáy biển, bất ngờ tấn công."},
    {"name": "Cá Phượng Hoàng", "strength": 10, "speed": 9, "rarity": "Huyền thoại", "desc": "Cá thần thoại, rực rỡ, cực hiếm."},
    {"name": "Cá Tầm Cổ Đại", "strength": 7, "speed": 5, "rarity": "Hiếm", "desc": "Cá sống lâu đời, khó bắt."},
    {"name": "Cá Mặt Trời", "strength": 6, "speed": 6, "rarity": "Xịn", "desc": "Thân to, bơi chậm nhưng mạnh."},
    {"name": "Cá Chuồn Bay", "strength": 4, "speed": 8, "rarity": "Xịn", "desc": "Có thể nhảy khỏi mặt nước, rất nhanh."},
    {"name": "Cá Rồng Lửa", "strength": 9, "speed": 8, "rarity": "Hiếm", "desc": "Rực rỡ và hung dữ, khó bắt."},
    {"name": "Cá Tuyết Hoa", "strength": 5, "speed": 4, "rarity": "Bình thường", "desc": "Đẹp mắt nhưng yếu."},
    {"name": "Cá Ngọc Trai", "strength": 3, "speed": 2, "rarity": "Xịn", "desc": "Giá trị cao, hiếm gặp."},
]

trash_pool = [
    {"name": "Xô rỉ sét"}, {"name": "Vớ cũ"}, {"name": "Giấy vụn"}, {"name": "Hoa tàn"},
    {"name": "Lốp xe cũ"}, {"name": "Hộp giấy vỡ"}, {"name": "Bát nhựa vỡ"}, {"name": "Đĩa cũ"},
    {"name": "Bao nilon"}, {"name": "Gậy gỗ hỏng"}, {"name": "Quần áo rách"}, {"name": "Bút hỏng"},
    {"name": "Chai nhựa"}, {"name": "Hộp sữa rỗng"}, {"name": "Mảnh thủy tinh"}, {"name": "Đồ chơi vỡ"},
    {"name": "Giày cũ"}, {"name": "Chăn rách"}, {"name": "Túi giấy nhàu nát"}, {"name": "Ống hút nhựa"},
]

shop_items = [
    # --- Cần câu ---
    {"id": "rod_1", "name": "Cần Tre", "type": "cau", "price": 50, "rate": 0.65, "bonus": 0},
    {"id": "rod_2", "name": "Cần Sắt", "type": "cau", "price": 100, "rate": 0.70, "bonus": 1},
    {"id": "rod_3", "name": "Cần Bạch Kim", "type": "cau", "price": 200, "rate": 0.75, "bonus": 1},
    {"id": "rod_4", "name": "Cần Ngọc", "type": "cau", "price": 300, "rate": 0.78, "bonus": 2},
    {"id": "rod_5", "name": "Cần Rồng", "type": "cau", "price": 400, "rate": 0.80, "bonus": 2},
    {"id": "rod_6", "name": "Cần Bão Táp", "type": "cau", "price": 500, "rate": 0.82, "bonus": 2},
    {"id": "rod_7", "name": "Cần Thần Long", "type": "cau", "price": 600, "rate": 0.85, "bonus": 3},
    {"id": "rod_8", "name": "Cần Hắc Ám", "type": "cau", "price": 700, "rate": 0.88, "bonus": 3},
    {"id": "rod_9", "name": "Cần Băng Giá", "type": "cau", "price": 750, "rate": 0.89, "bonus": 3},
    {"id": "rod_10", "name": "Cần Hỏa Phụng", "type": "cau", "price": 800, "rate": 0.90, "bonus": 4},
    {"id": "rod_11", "name": "Cần Thiên Long", "type": "cau", "price": 850, "rate": 0.91, "bonus": 4},
    {"id": "rod_12", "name": "Cần Kim Cương", "type": "cau", "price": 900, "rate": 0.92, "bonus": 4},
    {"id": "rod_13", "name": "Cần Huyền Bí", "type": "cau", "price": 950, "rate": 0.93, "bonus": 5},
    {"id": "rod_14", "name": "Cần Thủy Nguyên", "type": "cau", "price": 1000, "rate": 0.94, "bonus": 5},
    {"id": "rod_15", "name": "Cần Long Vương", "type": "cau", "price": 1050, "rate": 0.95, "bonus": 5},
    {"id": "rod_16", "name": "Cần Ma Thuật", "type": "cau", "price": 1075, "rate": 0.96, "bonus": 5},
    {"id": "rod_17", "name": "Cần Hắc Long", "type": "cau", "price": 1090, "rate": 0.97, "bonus": 6},
    {"id": "rod_18", "name": "Cần Thần Thánh", "type": "cau", "price": 1095, "rate": 0.98, "bonus": 6},
    {"id": "rod_19", "name": "Cần Rồng Hắc Ám", "type": "cau", "price": 1100, "rate": 0.995, "bonus": 6},
    {"id": "rod_20", "name": "Cần Huyền Thoại", "type": "cau", "price": 1200, "rate": 1.0, "bonus": 7},

    # --- Mồi câu ---
    {"id": "bait_1", "name": "Mồi Giun", "type": "mồi", "price": 10, "bonus": 0},
    {"id": "bait_2", "name": "Mồi Cá", "type": "mồi", "price": 50, "bonus": 5},
    {"id": "bait_3", "name": "Mồi Bạch Kim", "type": "mồi", "price": 100, "bonus": 10},
    {"id": "bait_4", "name": "Mồi Rồng", "type": "mồi", "price": 150, "bonus": 15},
    {"id": "bait_5", "name": "Mồi Cá Huyền Thoại", "type": "mồi", "price": 250, "bonus": 20},
]

rarity_bonus = {
    "Dỏm": 0, "Bình thường": 0, "Xịn": 5, "Hiếm": 10, "Huyền thoại": 20
}

fishing_maps = [
    {"name": "Sông Huyền Bí", "type": "cá thường"},
    {"name": "Hồ Rồng", "type": "cá hiếm"},
    {"name": "Biển Sâu", "type": "cá huyền thoại"},
    {"name": "Suối Ngọc", "type": "cá thường"},
    {"name": "Hồ Băng Giá", "type": "cá hiếm"},
    {"name": "Đầm Lầy Ma Quái", "type": "cá thường"},
    {"name": "Vịnh Thần Long", "type": "cá hiếm"},
    {"name": "Đại Dương Tăm Tối", "type": "cá huyền thoại"},
    {"name": "Hồ Thiên Nga", "type": "cá thường"},
    {"name": "Biển Rồng Thần", "type": "cá huyền thoại"},
]

# ---------------- XỬ LÝ FILE NGƯỜI CHƠI ----------------
def ensure_player_file():
    if not os.path.exists(PLAYER_FILE):
        with open(PLAYER_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

def load_players():
    ensure_player_file()
    try:
        with open(PLAYER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.exception("Lỗi khi đọc players.json: %s", e)
        return {}

def save_players(players):
    try:
        with open(PLAYER_FILE, "w", encoding="utf-8") as f:
            json.dump(players, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception("Lỗi khi lưu players.json: %s", e)

# ---------------- LẤY TÊN NGƯỜI DÙNG ----------------
def get_user_name_by_id(bot, user_id):
    try:
        info = bot.fetchUserInfo(user_id)
        if hasattr(info, "changed_profiles") and user_id in info.changed_profiles:
            profile = info.changed_profiles[user_id]
            return getattr(profile, "zaloName", None) or getattr(profile, "displayName", "Unknown User")
        return "Unknown User"
    except Exception:
        return "Unknown User"

def get_real_name_and_cache(client, players, uid):
    uid_str = str(uid)
    cached = players.get(uid_str, {}).get("name")
    name = get_user_name_by_id(client, uid)
    if name and name != "Unknown User":
        players.setdefault(uid_str, {})["name"] = name
        save_players(players)
        return name
    return cached or f"Người chơi {uid_str}"

# ---------------- KHỞI TẠO NGƯỜI CHƠI ----------------
def ensure_user_keys(players, uid):
    uid_str = str(uid)
    if uid_str not in players:
        players[uid_str] = {}
    p = players[uid_str]
    p.setdefault("name", f"Người chơi {uid_str}")
    p.setdefault("money", 500)
    p.setdefault("kho", [])
    p.setdefault("cau", {"id": "rod_1", "name": "Cần Tre", "rate": 0.65})
    p.setdefault("mồi", [])
    p.setdefault("last_daily", 0)
    return players

# ---------------- TÌM MÓN HÀNG THEO SỐ HOẶC TÊN ----------------
def find_shop_item(query):
    query = query.strip().lower()
    if query.isdigit():
        idx = int(query) - 1
        if 0 <= idx < len(shop_items):
            return shop_items[idx]
    for it in shop_items:
        if query in it["name"].lower() or query == it["id"].lower():
            return it
    return None

# ---------------- LỆNH SHOP ----------------
def handle_ca_shop(client, thread_id, thread_type, players, uid, name):
    player = players[str(uid)]
    lines = ["SHOP — Cần & Mồi (Mini Game)"]
    lines.append("Mua nhanh: ca mua <số> hoặc ca mua <tên> [x<số lượng>]")
    lines.append("")
    for idx, it in enumerate(shop_items, 1):
        bonus = f" (+{it.get('bonus', 0)})" if it.get("bonus", 0) > 0 else ""
        rate = f"{int(it.get('rate', 0) * 100)}%" if 'rate' in it else ""
        lines.append(f"{idx:2}. {it['name']:<20} — {it['price']:>4} xu — {rate:<5} {bonus}")
    lines.append("")
    rod = player.get("cau") or {"name": "Cần Tre", "rate": 0.65}
    lines.append(f"CẦN CỦA BẠN: {rod['name']} (Tỉ lệ: {int(rod['rate'] * 100)}%)")
    if player.get("mồi"):
        lines.append("MỒI CỦA BẠN: " + ", ".join([f"{b['name']} x{b['qty']}" for b in player["mồi"]]))
    else:
        lines.append("MỒI CỦA BẠN: (chưa có)")
    lines.append("")
    lines.append("Câu cá: ca cau")
    lines.append("Bán cá: ca ban <tên cá>")
    lines.append("Xem map: ca map")
    client.sendMessage(Message(text="\n".join(lines)), thread_id, thread_type,ttl=60000)

# ---------------- LỆNH CHÍNH ----------------
def handle_ca(message, message_object, thread_id, thread_type, author_id, client):
    players = ensure_user_keys(load_players(), author_id)
    uid = str(author_id)
    name = get_real_name_and_cache(client, players, author_id)

    args = message.strip().split(maxsplit=1)
    if len(args) < 2:
        client.sendMessage(Message(text=f"{name}, cú pháp: ca <shop|mua|cau|kho|bxh|daily|listlenh|ban|map>"), thread_id, thread_type,ttl=60000)
        return
    cmd = args[1].strip().lower()

    # SHOP
    if cmd == "shop":
        handle_ca_shop(client, thread_id, thread_type, players, uid, name)
        return

    # MUA (HỖ TRỢ SỐ + SỐ LƯỢNG)
    if cmd.startswith("mua"):
        parts = cmd.split(maxsplit=1)
        if len(parts) < 2:
            client.sendMessage(Message(text="Cú pháp: ca mua <số/tên> [x<số lượng>]"), thread_id, thread_type,ttl=60000)
            return

        raw_query = parts[1].strip()
        quantity = 1

        # Tách xN
        if " x" in raw_query.lower():
            query_part, qty_part = raw_query.lower().rsplit(" x", 1)
            if qty_part.isdigit():
                quantity = int(qty_part)
                if quantity <= 0:
                    client.sendMessage(Message(text="Số lượng phải > 0!"), thread_id, thread_type,ttl=60000)
                    return
                if quantity > 10:
                    client.sendMessage(Message(text="Tối đa 10 món/lần!"), thread_id, thread_type,ttl=60000)
                    return
                raw_query = query_part.strip()
            else:
                client.sendMessage(Message(text="Số lượng không hợp lệ! Dùng: x3, x10"), thread_id, thread_type,ttl=60000)
                return
        else:
            raw_query = raw_query.strip()

        item = find_shop_item(raw_query)
        if not item:
            client.sendMessage(Message(text="Không tìm thấy món. Gõ 'ca shop' để xem."), thread_id, thread_type,ttl=60000)
            return

        player = players[uid]
        total_price = item["price"] * quantity

        if player["money"] < total_price:
            client.sendMessage(Message(text=f"Không đủ tiền! Cần {total_price} xu."), thread_id, thread_type,ttl=60000)
            return

        player["money"] -= total_price

        if item["type"] == "cau":
            if quantity > 1:
                client.sendMessage(Message(text="Cần câu chỉ được mua 1 món/lần!"), thread_id, thread_type,ttl=60000)
                player["money"] += total_price
                save_players(players)
                return
            player["cau"] = {"id": item["id"], "name": item["name"], "rate": item["rate"]}
            bonus_msg = f" (+{item.get('bonus', 0)})" if item.get("bonus", 0) > 0 else ""
            client.sendMessage(Message(text=f"{name} mua {item['name']}{bonus_msg} — Còn {player['money']} xu"), thread_id, thread_type,ttl=60000)
        else:
            exist = next((b for b in player["mồi"] if b["id"] == item["id"]), None)
            if exist:
                exist["qty"] += quantity
            else:
                player["mồi"].append({"id": item["id"], "name": item["name"], "bonus": item.get("bonus", 0), "qty": quantity})
            bonus_msg = f" (+{item.get('bonus', 0)})" if item.get("bonus", 0) > 0 else ""
            client.sendMessage(Message(text=f"{name} mua {item['name']} x{quantity}{bonus_msg} — Còn {player['money']} xu"), thread_id, thread_type,ttl=60000)

        save_players(players)
        return

    # CÂU CÁ
    if cmd == "cau":
        player = players[uid]
        rod_rate = player["cau"].get("rate", 0.65)
        total_bait_bonus = sum(b.get("bonus", 0) * b.get("qty", 1) for b in player["mồi"])
        bonus_rate = min(0.15, total_bait_bonus * 0.01)
        eff_rate = min(0.999, rod_rate + bonus_rate)

        chosen_map = random.choice(fishing_maps)

        if random.random() < eff_rate:
            fish = random.choice(fish_pool)
            player["kho"].append(fish)
            reward = random.randint(30, 100)
            player["money"] += reward
            save_players(players)
            msg = (
                f"{name} vừa câu được {fish['name']}\n"
                f"📍Khu vực: {chosen_map['name']} ({chosen_map['type']})\n"
                f"Sức mạnh: {fish['strength']} | Tốc độ: {fish['speed']}\n"
                f"Độ hiếm: {fish['rarity']}\n"
                f"{fish['desc']}\n"
                f"Nhận: +{reward} xu"
            )
        else:
            trash = random.choice(trash_pool)["name"]
            loss = random.randint(5, 20)
            player["money"] = max(0, player["money"] - loss)
            save_players(players)
            msg = (
                f"{name} kéo lên {trash} — mất {loss} xu.\n"
                f"Khu vực: {chosen_map['name']} ({chosen_map['type']})"
            )
        client.sendMessage(Message(text=msg), thread_id, thread_type,ttl=60000)
        return

    # BÁN CÁ
    if cmd.startswith("ban"):
        parts = cmd.split(maxsplit=1)
        if len(parts) < 2:
            client.sendMessage(Message(text="Cú pháp: ca ban <tên cá>"), thread_id, thread_type)
            return

        fish_name = parts[1].strip().lower()
        player = players[uid]

        fish_counts = {}
        for f in player["kho"]:
            fish_counts[f["name"].lower()] = fish_counts.get(f["name"].lower(), 0) + 1

        if fish_name not in fish_counts or fish_counts[fish_name] == 0:
            client.sendMessage(Message(text="Bạn không có cá này."), thread_id, thread_type)
            return

        sold = 0
        total_xu = 0
        new_kho = []
        for f in player["kho"]:
            if f["name"].lower() == fish_name:
                sold += 1
                total_xu += 50 + rarity_bonus.get(f.get("rarity"), 0)
            else:
                new_kho.append(f)

        player["kho"] = new_kho
        player["money"] += total_xu
        save_players(players)

        client.sendMessage(Message(text=f"{name} bán {sold} con {fish_name} → +{total_xu} xu"), thread_id, thread_type,ttl=60000)
        return

    # KHO
    if cmd == "kho":
        p = players[uid]
        lines = [f"KHO CỦA {name}", f"• Xu: {p['money']} xu"]
        lines.append(f"• Cần: {p['cau']['name']} ({int(p['cau']['rate']*100)}%)")
        if p["mồi"]:
            lines.append("• Mồi: " + ", ".join([f"{b['name']} x{b['qty']}" for b in p["mồi"]]))
        else:
            lines.append("• Mồi: (trống)")
        if p["kho"]:
            fish_counts = {}
            for f in p["kho"]:
                fish_counts[f["name"]] = fish_counts.get(f["name"], 0) + 1
            for fname, qty in fish_counts.items():
                lines.append(f"• {fname} x{qty}")
        else:
            lines.append("• Cá: (trống)")
        client.sendMessage(Message(text="\n".join(lines)), thread_id, thread_type,ttl=60000)
        return

    # BXH
    if cmd == "bxh":
        ranking = []
        for uid2, p in players.items():
            total = sum(f["strength"] + f["speed"] + rarity_bonus.get(f["rarity"], 0) for f in p.get("kho", []))
            pname = p.get("name") or get_real_name_and_cache(client, players, uid2)
            ranking.append((pname, total))
        ranking.sort(key=lambda x: x[1], reverse=True)
        lines = ["BẢNG XẾP HẠNG"]
        if not ranking:
            lines.append("Chưa có ai.")
        else:
            for i, (pname, pts) in enumerate(ranking[:10], 1):
                lines.append(f"{i}. {pname} — {pts} điểm")
        client.sendMessage(Message(text="\n".join(lines)), thread_id, thread_type,ttl=60000)
        return

    # DAILY
    if cmd == "daily":
        p = players[uid]
        now = time.time()
        if now - p["last_daily"] < 86400:
            remain = int((86400 - (now - p["last_daily"])) // 3600)
            client.sendMessage(Message(text=f"Quay lại sau {remain}h để nhận daily."), thread_id, thread_type)
            return
        reward = random.randint(80, 200)
        p["money"] += reward
        p["last_daily"] = now
        save_players(players)
        client.sendMessage(Message(text=f"{name} nhận daily: +{reward} xu"), thread_id, thread_type,ttl=60000)
        return

    # MAP
    if cmd == "map":
        lines = ["BẢN ĐỒ CÂU CÁ:"]
        for idx, m in enumerate(fishing_maps, 1):
            lines.append(f"• {idx}. {m['name']} — {m['type']}")
        client.sendMessage(Message(text="\n".join(lines)), thread_id, thread_type,ttl=60000)
        return

    # LIST LỆNH
    if cmd == "listlenh":
        cmds = [
            "ca shop", "ca mua <số/tên> [xN]", "ca cau", "ca kho",
            "ca bxh", "ca daily", "ca ban <tên cá>", "ca map"
        ]
        client.sendMessage(Message(text="DANH SÁCH LỆNH:\n" + "\n".join(cmds)), thread_id, thread_type,ttl=60000)
        return

# ---------------- ĐĂNG KÝ LỆNH ----------------
def TQD():
    return {
        "ca": handle_ca
    }