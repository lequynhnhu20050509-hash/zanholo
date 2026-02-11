import os, tempfile, math, requests, time, threading, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from io import BytesIO
from zlapi.models import Message
from config import PREFIX

# ================== METADATA ==================
des = {
    'version': "2.0.2",
    'credits': "Latte",
    'description': "Kiếm danh sách gif",
    'power': "Thành viên"
}

# ================== CONFIG ==================
FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
EMOJI_FONT_PATH = "modules/cache/font/NotoEmoji-Bold.ttf"
GIPHY_API_KEY = "f6fncDM9pYAU6k0vgVA60eRvnoW0T1SI"
SEARCH_TIMEOUT = 60
user_states = {}
EMOJI_LIST = ["💖"]

# ================== FONTS ==================
def get_font(size):
    try: 
        return ImageFont.truetype(FONT_PATH, size)
    except: 
        return ImageFont.load_default()

def get_emoji_font(size):
    try: 
        return ImageFont.truetype(EMOJI_FONT_PATH, size)
    except: 
        return ImageFont.load_default()

# ================== AUTOSAVE ==================
def autosave(img, quality=92):
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        img.convert("RGB").save(tf, "JPEG", quality=quality)
        return tf.name

# ================== CLEANUP ==================
def cleanup_states():
    while True:
        try:
            now = time.time()
            to_delete = [aid for aid, s in user_states.items() if now - s['time_of_search'] > SEARCH_TIMEOUT]
            for aid in to_delete: del user_states[aid]
        except: 
            pass
        time.sleep(5)

threading.Thread(target=cleanup_states, daemon=True).start()

# ================== GIPHY SEARCH ==================
def search_giphy(query, limit=12):
    url = "https://api.giphy.com/v1/gifs/search"
    params = {"api_key": GIPHY_API_KEY,"q":query,"limit":limit,"offset":0,"rating":"g","lang":"en"}
    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        return [item["images"]["downsized"]["url"] for item in data["data"]]
    except: 
        return []

# ================== FETCH GIF THUMBNAIL + SIZE ==================
def fetch_gif_thumbnail_and_size(url, max_size=(180,180)):
    try:
        resp = requests.get(url, timeout=10)
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(resp.content)
            tmp_path = tmp_file.name
        with Image.open(tmp_path) as img:
            img = img.convert("RGBA")
            width, height = img.size
            img.thumbnail(max_size)
            thumb = img.copy()
        os.remove(tmp_path)
        return thumb, width, height
    except:
        return Image.new("RGBA", max_size, (50,50,70)), max_size[0], max_size[1]

# ================== DRAW GIF LIST ==================
def draw_gif_list_card_simple(gif_urls):
    CARD_W, CARD_H = 180, 180
    PADDING = 20
    COLS = 3
    ROWS = (len(gif_urls)+COLS-1)//COLS
    WIDTH = CARD_W*COLS + PADDING*(COLS+1)
    HEIGHT = CARD_H*ROWS + PADDING*(ROWS+1)

    # Nền trắng
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (255,255,255,255))
    draw = ImageDraw.Draw(overlay)
    small_font = get_font(18)
    used_emojis = set()

    for idx, url in enumerate(gif_urls):
        row = idx//COLS
        col = idx%COLS
        cx = PADDING + col*(CARD_W+PADDING)
        cy = PADDING + row*(CARD_H+PADDING)

        # Lấy thumbnail nhưng không crop tròn
        thumb, _, _ = fetch_gif_thumbnail_and_size(url, max_size=(CARD_W-20, CARD_H-20))

        # Paste thumbnail trực tiếp
        overlay.paste(thumb, (cx + (CARD_W-thumb.width)//2, cy + (CARD_H-thumb.height)//2), mask=thumb if thumb.mode=="RGBA" else None)

        # Emoji + GIF số
        available = [e for e in EMOJI_LIST if e not in used_emojis]
        if not available: available = EMOJI_LIST
        em = random.choice(available)
        used_emojis.add(em)
        text_y = cy + CARD_H - 24
        draw.text((cx+CARD_W//4, text_y), f"{em} GIF {idx+1}", font=small_font, fill=(0,0,0), stroke_width=1, stroke_fill=(255,255,255))

    return autosave(overlay)


# ================== HANDLE COMMAND ==================
def handle_gif_command_pro(message, message_object, thread_id, thread_type, author_id, client):
    if des.get("power") != "Thành viên":
        client.sendMessage(Message(text="❌ Bạn chưa có quyền dùng lệnh này. Chỉ có admin Latte mới được sử dụng lệnh này"), thread_id, thread_type,ttl=30000)
        return

    content = message.strip().split()
    if len(content)<2:
        client.sendMessage(Message(text="Nhập từ khóa tìm GIF. Ví dụ: .gif mèo"), thread_id, thread_type,ttl=30000)
        return
    arg = content[1].strip()

    if arg.isdigit():
        idx = int(arg)-1
        gifs = user_states.get(author_id, {}).get("urls", [])
        if 0 <= idx < len(gifs):
            temp_path = tempfile.NamedTemporaryFile(suffix=".gif", delete=False).name
            resp = requests.get(gifs[idx])
            with open(temp_path,"wb") as f: f.write(resp.content)
            with Image.open(temp_path) as im:
                w, h = im.size
            client.sendLocalGif(temp_path, f"🎉 GIF số {arg}", thread_id, thread_type,ttl=60000*5)
            if os.path.exists(temp_path): os.remove(temp_path)
        else:
            client.sendMessage(Message(text="❌ Số GIF không hợp lệ."), thread_id, thread_type,ttl=30000)
        return

    client.sendMessage(Message(text=f"🔎 Bot đang tìm GIF '{arg}'..."), thread_id, thread_type,ttl=30000)
    urls = search_giphy(arg, limit=12)
    if not urls:
        client.sendMessage(Message(text=f"❌ Không tìm thấy GIF với từ khóa '{arg}'."), thread_id, thread_type,ttl=30000)
        return

    user_states[author_id] = {"urls": urls, "time_of_search": time.time()}

    img_path = draw_gif_list_card_simple(urls)
    try:
        with Image.open(img_path) as im:
            width, height = im.size
        client.sendLocalImage(
            img_path,
            thread_id=thread_id,
            thread_type=thread_type,
            width=width,
            height=height,
            ttl=60000,
            message=Message(text=f"➜ Nhập {PREFIX}gif <số> để xem GIF")
        )
        os.remove(img_path)
    except:
        client.sendMessage(Message(text="❌ Lỗi gửi ảnh GIF list."), thread_id, thread_type,ttl=60000)

# ================== EXPORT ==================
def TQD():
    return {"gif": handle_gif_command_pro}
