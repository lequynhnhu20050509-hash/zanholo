import os
import time
import random
from PIL import Image, ImageDraw, ImageFont
from zlapi.models import Message

# ================= CONFIG =================
WIDTH, HEIGHT = 400, 120
FONT_SIZE = 60      # CHỮ TO HƠN
FRAME_DELAY = 55
STEP = 5 
OUTPUT_DIR = "modules/cache/tmp"

TEXT_FONT_PATH = "modules/cache/font/BeVietnamPro-Bold.ttf"
NUM_RAIN = 20
RAIN_MAX_LENGTH = 15
RAIN_ALPHA = 200

LIGHTNING_CHANCE = 0.25
LIGHTNING_COLOR = (255, 255, 200)

des = {
    'version': "2.1.0",
    'credits': "Latte",
    'description': "GIF text",
    'power': "Thành viên"
}

# ================= FUN =================
def get_gradient_color(x, total_width, shift=0):
    rainbow = [
        (255,0,0), (255,127,0), (255,255,0),
        (0,255,0), (0,0,255), (75,0,130), (148,0,211), (255,0,0)
    ]
    pos = ((x + shift) / total_width) * (len(rainbow)-1)
    idx = int(pos) % (len(rainbow)-1)
    frac = pos - idx
    c1, c2 = rainbow[idx], rainbow[idx+1]
    return tuple(int(c1[i] + (c2[i]-c1[i])*frac) for i in range(3))

def draw_lightning(draw):
    x = random.randint(50, WIDTH - 50)
    y = 0
    main_path = []
    for _ in range(random.randint(6, 9)):
        x2 = x + random.randint(-20, 20)
        y2 = y + random.randint(15, 30)
        draw.line((x, y, x2, y2), fill=LIGHTNING_COLOR, width=2)
        main_path.append((x2, y2))
        x, y = x2, y2
    for (bx, by) in random.sample(main_path, k=min(3, len(main_path))):
        nx, ny = bx, by
        for _ in range(random.randint(2, 4)):
            nx2 = nx + random.randint(-15, 15)
            ny2 = ny + random.randint(10, 20)
            draw.line((nx, ny, nx2, ny2), fill=(200, 200, 255), width=1)
            nx, ny = nx2, ny2

def draw_rainbow(draw, shift):
    rainbow_colors = [
        (255,0,0), (255,127,0), (255,255,0),
        (0,255,0), (0,0,255), (75,0,130), (148,0,211)
    ]
    arc_width = 12
    radius = WIDTH
    for i, _ in enumerate(rainbow_colors):
        color = get_gradient_color(i*50, WIDTH, shift/8)
        bbox = [
            -radius//2 + i*arc_width,
            -HEIGHT + i*arc_width,
            WIDTH + radius//2 - i*arc_width,
            HEIGHT + i*arc_width
        ]
        draw.arc(bbox, start=180, end=360, fill=color, width=arc_width)

def create_gif(text):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        text_font = ImageFont.truetype(TEXT_FONT_PATH, FONT_SIZE)
    except:
        text_font = ImageFont.load_default()

    
    dummy = Image.new("RGB", (WIDTH, HEIGHT))
    draw_dummy = ImageDraw.Draw(dummy)
    text_width = 0
    for c in text:
        text_width += draw_dummy.textlength(c, font=text_font) + 5
    text_height = draw_dummy.textbbox((0, 0), text, font=text_font)[3]

    total_frames = (text_width + WIDTH) // STEP
    frames = []

    
    rain_pos = [[random.randint(0, WIDTH), random.randint(-HEIGHT, 0), random.randint(5, RAIN_MAX_LENGTH)] for _ in range(NUM_RAIN)]

    i = 0
    shift = 0
    while i < total_frames:
        img = Image.new("RGB", (WIDTH, HEIGHT), color="black")
        draw = ImageDraw.Draw(img)

        draw_rainbow(draw, shift)

        offset_x = WIDTH - i*STEP

        
        cursor_x = offset_x
        for c in text:
            w = draw.textlength(c, font=text_font)
            char_color = get_gradient_color(cursor_x, text_width, shift/5)
            draw.text(
                (cursor_x, (HEIGHT - text_height)//2), 
                c, 
                font=text_font, 
                fill=char_color
            )
            cursor_x += w + 5  

        
        for j in range(len(rain_pos)):
            x, y, l = rain_pos[j]
            y += 8
            if y > HEIGHT:
                y = random.randint(-20, 0)
                x = random.randint(0, WIDTH)
                l = random.randint(5, RAIN_MAX_LENGTH)
            rain_pos[j] = [x, y, l]
            dx = random.randint(1, 3)
            draw.line([(x, y), (x+dx, y+l)], fill=(RAIN_ALPHA, RAIN_ALPHA, 255))

        
        if random.random() < LIGHTNING_CHANCE:
            lightning_img = img.copy()
            lightning_draw = ImageDraw.Draw(lightning_img)
            draw_lightning(lightning_draw)
            frames.append(lightning_img)

            flash = Image.new("RGB", (WIDTH, HEIGHT), (255,255,255))
            flash_blend = Image.blend(lightning_img, flash, 0.3)
            frames.append(flash_blend)

            i += 2
            shift += 2
            continue

        frames.append(img)
        i += 1
        shift += 1

    gif_path = os.path.join(OUTPUT_DIR, f"giftext_{int(time.time())}.gif")
    frames[0].save(
        gif_path, save_all=True, append_images=frames[1:], optimize=True,
        duration=FRAME_DELAY, loop=0
    )
    return gif_path

def handle_giftext_command(message, message_object, thread_id, thread_type, author_id, client):
    content = getattr(message_object, "content", None) or message
    content = content.strip()
    parts = content.split()
    if len(parts) < 2:
        client.sendMessage(Message(text="❌ Sai định dạng!\nDùng: ,gif <chữ muốn tạo GIF>"), thread_id, thread_type,ttl=60000)
        return

    text = " ".join(parts[1:])
    client.sendMessage(Message(text="⏳ Đợi tớ tí, đang tạo GIF đẹp lung linh ✨"), thread_id, thread_type,ttl=20000)

    try:
        gif_path = create_gif(text)
    except Exception as e:
        client.sendMessage(Message(text=f"❌ Lỗi tạo GIF: {e}"), thread_id, thread_type,ttl=60000)
        return

    try:
        client.sendLocalGif(
            gifPath=gif_path,
            thumbnailUrl=None,
            thread_id=thread_id,
            thread_type=thread_type,
            gifName=os.path.basename(gif_path),
            width=WIDTH,
            height=HEIGHT,
            ttl=0
        )
    except Exception as e:
        client.sendMessage(Message(text=f"❌ Lỗi gửi GIF: {e}"), thread_id, thread_type,ttl=60000)

def TQD():
    return {"giftext": handle_giftext_command}
