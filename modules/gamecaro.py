# modules/caro_image.py
import os
import json
import random
import tempfile
import threading
import numpy as np
import re
from PIL import Image, ImageDraw, ImageFont
from zlapi.models import Message

des = {
    'version': "7.6.0",
    'credits': "Latte + xAI Bot Engine",
    'description': "Caro 16x16 PvP + Bot AI siêu mạnh: chặn 3-4, fork, open-3, alpha-beta",
    'power': "Thành viên"
}

DATA_FILE = "modules/cache/caro_data.json"
FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
BOARD_SIZE = 16
TIME_LIMIT = 60

# ===== BOT CONSTANTS (từ caro_16x16_bot.py) =====
N = BOARD_SIZE
TOTAL_CELLS = N * N
EMPTY = 0
HUMAN = 1  # X
BOT = 2    # O
BOT_DEPTH = 1
CANDIDATE_RANGE = 30
FORK_BONUS = 25000
CENTER_WEIGHT = 0.2
ADJ_WEIGHT = 5
SCORES = {0: 0, 1: 10, 2: 80, 3: 800, 4: 8000, 5: 100000000}
DIRECTIONS = [(1, 0), (0, 1), (1, 1), (1, -1)]

# ===== FONT =====
def get_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except:
        return ImageFont.load_default()

# ===== AUTOSAVE =====
def autosave(img):
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        img.convert("RGB").save(tf.name, "JPEG", quality=95)
        return tf.name

# ===== DATA =====
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def update_stats(uid, name, win=False):
    data = load_data()
    if uid not in data:
        data[uid] = {"name": name, "win": 0, "lose": 0}
    if win:
        data[uid]["win"] += 1
    else:
        data[uid]["lose"] += 1
    save_data(data)

# ===== BOARD HELPERS =====
def idx_to_rc(idx):
    i = idx - 1
    return i // N, i % N

def rc_to_idx(r, c):
    return r * N + c + 1

def in_bounds(r, c):
    return 0 <= r < N and 0 <= c < N

# ===== WIN CHECK =====
def check_five_in_a_row(board, player):
    for r in range(N):
        for c in range(N):
            if board[r][c] != player:
                continue
            for dx, dy in DIRECTIONS:
                coords = [(r, c)]
                rr, cc = r, c
                for _ in range(4):
                    rr += dy
                    cc += dx
                    if not in_bounds(rr, cc) or board[rr][cc] != player:
                        break
                    coords.append((rr, cc))
                if len(coords) >= 5:
                    return True, [rc_to_idx(rr_, cc_) for rr_, cc_ in coords[:5]]
    return False, None

# ===== PATTERN HELPERS =====
def build_line(board, r, c, dx, dy, span=9):
    half = span // 2
    seq = []
    coords = []
    start_r = r - dy * half
    start_c = c - dx * half
    for i in range(span):
        rr = start_r + dy * i
        cc = start_c + dx * i
        if in_bounds(rr, cc):
            seq.append(int(board[rr][cc]))
            coords.append((rr, cc))
        else:
            seq.append(None)
            coords.append((rr, cc))
    return seq, coords

def seq_to_pattern(seq, player):
    opponent = HUMAN if player == BOT else BOT
    s = []
    for v in seq:
        if v is None: s.append('x')
        elif v == player: s.append('P')
        elif v == opponent: s.append('O')
        else: s.append('.')
    return ''.join(s)

def pattern_score_at(board, r, c, player):
    if board[r][c] != EMPTY: return -1e9, 0, 0
    total = 0
    patterns = 0
    threat_lines = 0
    opponent = HUMAN if player == BOT else BOT

    for dx, dy in DIRECTIONS:
        seq, _ = build_line(board, r, c, dx, dy, span=9)
        center = len(seq) // 2
        seq_sim = seq.copy()
        seq_sim[center] = player
        s = seq_to_pattern(seq_sim, player)

        if 'PPPPP' in s:
            return SCORES[5], 1, 1
        if 'PPPP' in s or '.PPPP' in s or 'PPPP.' in s:
            total += SCORES[4]; patterns += 1; threat_lines += 1
        if re.search(r'P\.?P\.?P', s):
            total += SCORES[3]; patterns += 1; threat_lines += 1
        if 'PP' in s:
            total += int(SCORES[2] * 0.6)

    if threat_lines >= 2: total += FORK_BONUS
    return total, patterns, threat_lines

# ===== IMMEDIATE MOVES =====
def find_immediate_win_moves(board, player):
    wins = []
    for i in range(N):
        for j in range(N):
            if board[i][j] != EMPTY: continue
            board[i][j] = player
            win, _ = check_five_in_a_row(board, player)
            board[i][j] = EMPTY
            if win: wins.append(rc_to_idx(i, j))
    return wins

def find_double_threats(board, player):
    doubles = []
    for i in range(N):
        for j in range(N):
            if board[i][j] != EMPTY: continue
            _, _, threats = pattern_score_at(board, i, j, player)
            if threats >= 2:
                doubles.append(rc_to_idx(i, j))
    return doubles

def find_block_three_moves(board, player):
    opponent = HUMAN if player == BOT else BOT
    blocks = set()
    for i in range(N):
        for j in range(N):
            if board[i][j] != EMPTY: continue
            board[i][j] = opponent
            score, _, _ = pattern_score_at(board, i, j, opponent)
            board[i][j] = EMPTY
            if score >= SCORES[3]:
                blocks.add(rc_to_idx(i, j))
    return list(blocks)

# ===== EVALUATION =====
def evaluate_position(board, r, c, player):
    if board[r][c] != EMPTY: return -1e9
    opponent = HUMAN if player == BOT else BOT
    attack_score, _, attack_threats = pattern_score_at(board, r, c, player)
    defend_score, _, defend_threats = pattern_score_at(board, r, c, opponent)
    score = attack_score + defend_score * 0.9
    adj = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0: continue
            rr, cc = r + dr, c + dc
            if in_bounds(rr, cc) and board[rr][cc] != EMPTY:
                adj += ADJ_WEIGHT
    center_r, center_c = N // 2, N // 2
    center_dist = abs(r - center_r) + abs(c - center_c)
    center_bonus = max(0, (center_r + center_c) - center_dist) * CENTER_WEIGHT
    total = score + adj + center_bonus + attack_threats * 50 - defend_threats * 20
    return total

# ===== CANDIDATE GENERATION =====
def generate_candidate_moves(board, player, limit=CANDIDATE_RANGE):
    opponent = HUMAN if player == BOT else BOT
    wins = find_immediate_win_moves(board, player)
    if wins: return wins[:limit]
    blocks = find_immediate_win_moves(board, opponent)
    if blocks: return blocks[:limit]
    forks = find_double_threats(board, player)
    if forks: return forks[:limit]
    block3 = find_block_three_moves(board, player)
    if block3: return block3[:limit]

    stones = [(i, j) for i in range(N) for j in range(N) if board[i][j] != EMPTY]
    near = set()
    for r, c in stones:
        for dr in (-2, -1, 0, 1, 2):
            for dc in (-2, -1, 0, 1, 2):
                rr, cc = r + dr, c + dc
                if in_bounds(rr, cc) and board[rr][cc] == EMPTY:
                    near.add(rc_to_idx(rr, cc))
    if not stones:
        return [rc_to_idx(N // 2, N // 2)]

    scored = [(evaluate_position(board, *idx_to_rc(idx), player), idx) for idx in near]
    scored.sort(reverse=True)
    return [idx for _, idx in scored[:limit]]

# ===== ALPHA-BETA =====
def alphabeta(board, depth, alpha, beta, maximizing_player, player):
    win, _ = check_five_in_a_row(board, BOT)
    if win: return 1e12 if player == BOT else -1e12
    win, _ = check_five_in_a_row(board, HUMAN)
    if win: return 1e12 if player == HUMAN else -1e12
    if depth == 0 or all(board[i][j] != EMPTY for i in range(N) for j in range(N)):
        my_scores = sum(s for s, _ in [(evaluate_position(board, i, j, player), 0) for i in range(N) for j in range(N) if board[i][j] == EMPTY][:40])
        opp = HUMAN if player == BOT else BOT
        opp_scores = sum(s for s, _ in [(evaluate_position(board, i, j, opp), 0) for i in range(N) for j in range(N) if board[i][j] == EMPTY][:40])
        return my_scores - opp_scores

    cur = player if maximizing_player else (HUMAN if player == BOT else BOT)
    candidates = generate_candidate_moves(board, cur, limit=20)
    if maximizing_player:
        value = -1e15
        for idx in candidates:
            r, c = idx_to_rc(idx)
            board[r][c] = cur
            val = alphabeta(board, depth - 1, alpha, beta, False, player)
            board[r][c] = EMPTY
            value = max(value, val)
            alpha = max(alpha, value)
            if alpha >= beta: break
        return value
    else:
        value = 1e15
        for idx in candidates:
            r, c = idx_to_rc(idx)
            board[r][c] = cur
            val = alphabeta(board, depth - 1, alpha, beta, True, player)
            board[r][c] = EMPTY
            value = min(value, val)
            beta = min(beta, value)
            if alpha >= beta: break
        return value

# ===== BOT MOVE =====
def bot_move(board_np):
    # 1. Thắng ngay
    wins = find_immediate_win_moves(board_np, BOT)
    if wins: return idx_to_rc(wins[0])

    # 2. Chặn đối thủ thắng
    blocks = find_immediate_win_moves(board_np, HUMAN)
    if blocks:
        best = max(blocks, key=lambda idx: evaluate_position(board_np, *idx_to_rc(idx), BOT))
        return idx_to_rc(best)

    # 3. Chặn 3
    block3 = find_block_three_moves(board_np, BOT)
    if block3:
        best = max(block3, key=lambda idx: evaluate_position(board_np, *idx_to_rc(idx), BOT))
        return idx_to_rc(best)

    # 4. Tạo fork
    forks = find_double_threats(board_np, BOT)
    if forks: return idx_to_rc(forks[0])

    # 5. Chặn fork đối thủ
    opp_forks = find_double_threats(board_np, HUMAN)
    if opp_forks:
        best = max(opp_forks, key=lambda idx: evaluate_position(board_np, *idx_to_rc(idx), BOT))
        return idx_to_rc(best)

    # 6. Alpha-beta
    candidates = generate_candidate_moves(board_np, BOT, limit=CANDIDATE_RANGE)
    best_score = -1e15
    best_move = None
    for idx in candidates:
        r, c = idx_to_rc(idx)
        board_np[r][c] = BOT
        score = alphabeta(board_np, BOT_DEPTH - 1, -1e15, 1e15, False, BOT)
        board_np[r][c] = EMPTY
        center_dist = abs(r - (N // 2)) + abs(c - (N // 2))
        score -= center_dist * 0.01
        if score > best_score:
            best_score = score
            best_move = (r, c)
    return best_move or idx_to_rc(random.choice([rc_to_idx(i, j) for i in range(N) for j in range(N) if board_np[i][j] == EMPTY]))

# ===== DRAW BOARD =====
def draw_board_image(board_np, last_move=None, player_name=None, winner=None, win_coords=None):
    cell_size = 48
    padding = 25
    img_width = N * cell_size + padding * 2
    img_height = N * cell_size + padding * 2 + 70
    font_mark = get_font(28)
    font_info = get_font(22)
    font_num = get_font(11)

    img = Image.new("RGB", (img_width, img_height), (245, 245, 250))
    draw = ImageDraw.Draw(img)

    for i in range(N):
        for j in range(N):
            x0 = padding + j * cell_size
            y0 = padding + i * cell_size
            rect_color = (255, 255, 255)
            if last_move == (i, j):
                rect_color = (255, 230, 200)
            if win_coords and rc_to_idx(i, j) in win_coords:
                rect_color = (180, 255, 180)
            draw.rectangle([x0, y0, x0 + cell_size, y0 + cell_size], fill=rect_color, outline=(180, 180, 220), width=1)

            idx = rc_to_idx(i, j)
            val = board_np[i][j]
            if val == EMPTY:
                try:
                    bbox = font_num.getbbox(str(idx))
                    nx = x0 + (cell_size - (bbox[2] - bbox[0])) / 2
                    ny = y0 + (cell_size - (bbox[3] - bbox[1])) / 2
                    draw.text((nx, ny), str(idx), font=font_num, fill=(130, 130, 130))
                except:
                    draw.text((x0 + 2, y0 + 2), str(idx), font=font_num, fill=(130, 130, 130))
            elif val == HUMAN:
                try:
                    bbox = font_mark.getbbox("X")
                    mx = x0 + (cell_size - (bbox[2] - bbox[0])) / 2
                    my = y0 + (cell_size - (bbox[3] - bbox[1])) / 2
                    draw.text((mx, my), "X", font=font_mark, fill=(255, 60, 60))
                except:
                    draw.text((x0 + 10, y0 + 5), "X", font=font_mark, fill=(255, 60, 60))
            elif val == BOT:
                try:
                    bbox = font_mark.getbbox("O")
                    mx = x0 + (cell_size - (bbox[2] - bbox[0])) / 2
                    my = y0 + (cell_size - (bbox[3] - bbox[1])) / 2
                    draw.text((mx, my), "O", font=font_mark, fill=(60, 100, 255))
                except:
                    draw.text((x0 + 10, y0 + 5), "O", font=font_mark, fill=(60, 100, 255))

    # SỬA LỖI TẠI ĐÂY
    if winner:
        msg = f"Thắng: {winner}"
    elif last_move and player_name:
        r, c = last_move
        msg = f"{player_name} đánh: ô {rc_to_idx(r, c)}"
    else:
        msg = "Lượt tiếp theo"

    try:
        bbox = font_info.getbbox(msg)
        tw = bbox[2] - bbox[0]
    except:
        tw = len(msg) * 12  # fallback
    draw.text(((img_width - tw) / 2, img_height - 55), msg, font=font_info, fill=(40, 40, 60))

    return autosave(img), img_width, img_height
# ===== GAME STATES =====
bot_games = {}  # uid: {"board_np": np.array, "timer": ...}
pvp_games = {}
timers = {}

# ===== TIMER =====
def start_timer(key, callback):
    if key in timers: timers[key].cancel()
    t = threading.Timer(TIME_LIMIT, callback)
    timers[key] = t
    t.start()

def stop_timer(key):
    if key in timers:
        timers[key].cancel()
        del timers[key]

# ===== HANDLE =====
def handle_caro(message, msg_obj, thread_id, thread_type, author_id, client):
    args = message.strip().split()
    if len(args) == 1:
        client.replyMessage(Message(text="Dùng:\n• caro bot → chơi với bot 16x16\n• caro @tag → PvP\n• caro <số_ô> → đánh (1-256)\n• caro bxh → xem BXH\n• caro lose → đầu hàng"), msg_obj, thread_id, thread_type, ttl=60000)
        return

    sub = args[1].lower()

    # BXH
    if sub == "bxh":
        data = load_data()
        if not data:
            client.replyMessage(Message(text="Chưa có ai trong BXH."), msg_obj, thread_id, thread_type, ttl=60000)
            return
        sorted_data = sorted(data.items(), key=lambda x: x[1].get("win", 0), reverse=True)
        msg = "BXH CARO 16x16\n\n"
        for i, (uid, info) in enumerate(sorted_data[:10], 1):
            msg += f"{i}. {info.get('name','Người')} — {info.get('win',0)} thắng\n"
        client.replyMessage(Message(text=msg), msg_obj, thread_id, thread_type, ttl=60000)
        return

    # ĐẦU HÀNG
    if sub == "lose":
        if author_id in bot_games:
            del bot_games[author_id]
            stop_timer(f"bot_{author_id}")
            client.replyMessage(Message(text="Bạn đã đầu hàng — Bot thắng!"), msg_obj, thread_id, thread_type, ttl=60000)
            update_stats(author_id, msg_obj.sender_name, win=False)
            return
        for room_id, game in list(pvp_games.items()):
            if author_id in game["players"]:
                loser = author_id
                winner = game["players"][0] if game["players"][1] == author_id else game["players"][1]
                del pvp_games[room_id]
                stop_timer(room_id)
                client.replyMessage(Message(text=f"{loser} đã đầu hàng!\n{winner} thắng!"), msg_obj, thread_id, thread_type, ttl=60000)
                return
        client.replyMessage(Message(text="Bạn không ở trong ván nào."), msg_obj, thread_id, thread_type, ttl=60000)
        return

    # BOT
    if sub == "bot":
        board_np = np.zeros((N, N), dtype=np.int8)
        bot_games[author_id] = {"board_np": board_np}
        img, w, h = draw_board_image(board_np)
        client.sendLocalImage(img, thread_id=thread_id, thread_type=thread_type, ttl=60000, width=w, height=h, message=Message(text="Caro 16x16 vs Bot AI (60s/lượt)"))
        os.remove(img)
        start_timer(f"bot_{author_id}", lambda: (
            bot_games.pop(author_id, None),
            client.replyMessage(Message(text="Bạn quá 60s — Bot thắng!"), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=60000),
            update_stats(author_id, msg_obj.sender_name, win=False)
        ))
        return

    # PvP
    if msg_obj.mentions:
        target_uid = msg_obj.mentions[0]["uid"]
        if target_uid == author_id:
            client.replyMessage(Message(text="Không thể chơi với chính mình."), msg_obj, thread_id, thread_type, ttl=60000)
            return
        room_id = f"{min(author_id, target_uid)}_{max(author_id, target_uid)}"
        if room_id in pvp_games:
            client.replyMessage(Message(text="Phòng PvP đã tồn tại. Dùng `/caro <số_ô>` để đánh."), msg_obj, thread_id, thread_type, ttl=60000)
            return
        board_np = np.zeros((N, N), dtype=np.int8)
        pvp_games[room_id] = {"players": [author_id, target_uid], "board_np": board_np, "turn": 0}
        img, w, h = draw_board_image(board_np)
        client.sendLocalImage(img, thread_id=thread_id, thread_type=thread_type, ttl=60000, width=w, height=h, message=Message(text=f"PvP 16x16: {author_id} (X) vs {target_uid} (O)\nMỗi lượt 60s"))
        os.remove(img)
        start_timer(room_id, lambda: (
            pvp_games.pop(room_id, None),
            client.replyMessage(Message(text=f"Người đi trước quá 60s — người kia thắng!"), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=60000)
        ))
        return

    # ĐÁNH Ô
    try:
        cell_number = int(sub)
        if not 1 <= cell_number <= TOTAL_CELLS:
            raise ValueError()
        row, col = idx_to_rc(cell_number)
    except:
        client.replyMessage(Message(text="Số ô không hợp lệ. Nhập từ 1–256"), msg_obj, thread_id, thread_type, ttl=60000)
        return

    # PvP
    for room_id, game in pvp_games.items():
        if author_id not in game["players"]: continue
        stop_timer(room_id)
        board_np = game["board_np"]
        if board_np[row][col] != EMPTY:
            client.replyMessage(Message(text="Ô này đã đánh."), msg_obj, thread_id, thread_type, ttl=60000)
            start_timer(room_id, lambda: None)
            return
        mark = HUMAN if game["turn"] == 0 else BOT
        board_np[row][col] = mark
        win, win_coords = check_five_in_a_row(board_np, mark)
        if win:
            winner_name = msg_obj.sender_name
            img, w, h = draw_board_image(board_np, (row, col), msg_obj.sender_name, winner_name, win_coords)
            client.sendLocalImage(img, thread_id=thread_id, thread_type=thread_type, ttl=60000, width=w, height=h, message=Message(text=f"{winner_name} thắng!"))
            os.remove(img)
            del pvp_games[room_id]
            update_stats(author_id, msg_obj.sender_name, win=True)
            return
        game["turn"] = 1 - game["turn"]
        next_player = game["players"][game["turn"]]
        img, w, h = draw_board_image(board_np, (row, col), msg_obj.sender_name)
        client.sendLocalImage(img, thread_id=thread_id, thread_type=thread_type, ttl=60000, width=w, height=h, message=Message(text=f"{msg_obj.sender_name} đánh ô {cell_number}, tới lượt {next_player}"))
        os.remove(img)
        start_timer(room_id, lambda: (
            pvp_games.pop(room_id, None),
            client.replyMessage(Message(text=f"{next_player} quá 60s — người kia thắng!"), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=60000)
        ))
        return

    # BOT
    if author_id in bot_games:
        stop_timer(f"bot_{author_id}")
        board_np = bot_games[author_id]["board_np"]
        if board_np[row][col] != EMPTY:
            client.replyMessage(Message(text="Ô này đã đánh."), msg_obj, thread_id, thread_type, ttl=60000)
            start_timer(f"bot_{author_id}", lambda: None)
            return
        board_np[row][col] = HUMAN
        win, win_coords = check_five_in_a_row(board_np, HUMAN)
        if win:
            img, w, h = draw_board_image(board_np, (row, col), msg_obj.sender_name, "Bạn", win_coords)
            client.sendLocalImage(img, thread_id=thread_id, thread_type=thread_type, ttl=60000, width=w, height=h, message=Message(text="Bạn thắng!"))
            update_stats(author_id, msg_obj.sender_name, win=True)
            os.remove(img)
            del bot_games[author_id]
            return

        # Bot đánh
        br, bc = bot_move(board_np)
        board_np[br][bc] = BOT
        win, win_coords = check_five_in_a_row(board_np, BOT)
        bot_idx = rc_to_idx(br, bc)
        if win:
            img, w, h = draw_board_image(board_np, (br, bc), "Bot", "Bot", win_coords)
            client.sendLocalImage(img, thread_id=thread_id, thread_type=thread_type, ttl=60000, width=w, height=h, message=Message(text="Bot thắng!"))
            update_stats(author_id, msg_obj.sender_name, win=False)
            os.remove(img)
            del bot_games[author_id]
            return

        img, w, h = draw_board_image(board_np, (br, bc), "Bot")
        client.sendLocalImage(img, thread_id=thread_id, thread_type=thread_type, ttl=60000, width=w, height=h, message=Message(text=f"Bot đánh ô {bot_idx}"))
        os.remove(img)
        start_timer(f"bot_{author_id}", lambda: (
            bot_games.pop(author_id, None),
            client.replyMessage(Message(text="Bạn quá 60s — Bot thắng!"), msg_obj, thread_id=thread_id, thread_type=thread_type, ttl=60000),
            update_stats(author_id, msg_obj.sender_name, win=False)
        ))
        return

def TQD():
    return {"caro": handle_caro}