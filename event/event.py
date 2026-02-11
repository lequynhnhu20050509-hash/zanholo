import time
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageChops
import requests
import base64
import emoji
from datetime import datetime
import concurrent.futures
import json
import random
from zlapi.models import *
from threading import Thread

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "welcome",
    'power': "Thành viên"}

EVENT_SETTINGS_FILE = "data/welcome_setting.json"
DEFAULT_COVER_PATH = "modules/cache/duong.jpg"

EVENT_COLORS = {
    GroupEventType.JOIN: (102, 255, 178),
    GroupEventType.LEAVE: (255, 102, 102),
    GroupEventType.REMOVE_MEMBER: (255, 178, 102),
    GroupEventType.ADD_ADMIN: (102, 178, 255),
    GroupEventType.REMOVE_ADMIN: (204, 102, 255)
}

EVENT_TEXT_COLORS = {
    GroupEventType.JOIN: (153, 255, 204),
    GroupEventType.LEAVE: (255, 153, 153),
    GroupEventType.REMOVE_MEMBER: (255, 204, 153),
    GroupEventType.ADD_ADMIN: (153, 204, 255),
    GroupEventType.REMOVE_ADMIN: (204, 153, 255)
}

EVENT_ICONS = {
    GroupEventType.JOIN: "🎉",
    GroupEventType.LEAVE: "🚪",
    GroupEventType.REMOVE_MEMBER: "🛑",
    GroupEventType.ADD_ADMIN: "👑",
    GroupEventType.REMOVE_ADMIN: "💔"
}

EVENT_NAMES = {
    GroupEventType.JOIN: "JOIN",
    GroupEventType.LEAVE: "LEAVE",
    GroupEventType.REMOVE_MEMBER: "KICK",
    GroupEventType.ADD_ADMIN: "ADMIN ADDED",
    GroupEventType.REMOVE_ADMIN: "ADMIN REMOVED"
}


def load_allowed_groups():
    if os.path.exists(EVENT_SETTINGS_FILE):
        with open(EVENT_SETTINGS_FILE, "r") as f:
            return json.load(f).get("groups", [])
    return []


def draw_gradient(image, size, start_color, end_color, opacity=50):
    gradient = Image.new('RGB', size)
    draw = ImageDraw.Draw(gradient)
    width, height = size
    for y in range(height):
        r = int(start_color[0] + (end_color[0] - start_color[0]) * y / height)
        g = int(start_color[1] + (end_color[1] - start_color[1]) * y / height)
        b = int(start_color[2] + (end_color[2] - start_color[2]) * y / height)
        draw.line((0, y, width, y), fill=(r, g, b))
    return gradient, Image.new('L', size, opacity)


def draw_badge(draw, text, x, y, font, bg_color, text_color):
    padding = 15
    text_width = sum(font.getlength(c) for c in text) + padding * 2
    text_height = font.getbbox("A")[3] - font.getbbox("A")[1] + padding * 2
    badge_img = Image.new('RGBA', (int(text_width + 20),
                          int(text_height + 20)), (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(badge_img)
    gradient_start = bg_color[:3]
    gradient_end = (
        gradient_start[0] * 2 // 3,
        gradient_start[1] * 2 // 3,
        gradient_start[2] * 2 // 3)
    gradient, gradient_mask = draw_gradient(badge_img, (int(
        text_width + 20), int(text_height + 20)), gradient_start, gradient_end, opacity=200)
    badge_img.paste(gradient, (0, 0), mask=gradient_mask)
    badge_draw.rounded_rectangle(
        (10, 10, text_width + 10, text_height + 10),
        radius=15,
        fill=(0, 0, 0, 100)
    )
    badge_draw.rounded_rectangle(
        (5, 5, text_width + 5, text_height + 5),
        radius=15,
        fill=bg_color
    )
    badge_draw.text((padding, padding), text, fill=text_color, font=font)
    draw._image.paste(badge_img, (int(x - padding),
                      int(y - padding)), mask=badge_img)


def draw_text_line(
    draw,
    text,
    x,
    y,
    font,
    emoji_font,
    text_color,
    shadow_color=(
        100,
        100,
        100)):
    shadow_offset = 2
    for char in text:
        f = emoji_font if emoji.emoji_count(char) else font
        draw.text((x + shadow_offset, y + shadow_offset),
                  char, fill=shadow_color, font=f)
        x += f.getlength(char)
    x = x - sum(f.getlength(char) for char in text)
    for char in text:
        f = emoji_font if emoji.emoji_count(char) else font
        draw.text((x, y), char, fill=text_color, font=f)
        x += f.getlength(char)


def split_text_into_lines(text, font, emoji_font, max_width):
    lines = []
    for paragraph in text.splitlines():
        words = paragraph.split()
        line = ""
        for word in words:
            temp_line = line + word + " "
            width = sum(emoji_font.getlength(c) if emoji.emoji_count(
                c) else font.getlength(c) for c in temp_line)
            if width <= max_width:
                line = temp_line
            else:
                if line:
                    lines.append(line.strip())
                line = word + " "
        if line:
            lines.append(line.strip())
    return lines


def draw_text(
        draw,
        text,
        position,
        font,
        emoji_font,
        image_width,
        separator_x,
        is_long_text,
        event_type):
    x, y = position
    max_width = image_width - separator_x - 120
    lines = split_text_into_lines(text, font, emoji_font, max_width)
    th = font.getbbox("Ay")[3] - font.getbbox("Ay")[1]
    lh = int(th * 1.4)
    yh = len(lines) * lh
    yo = y - yh // 2

    if is_long_text and len(lines) > 5:
        lines = lines[:5]
        lines[-1] = lines[-1][:max(0, len(lines[-1]) - 3)] + "..."
        yh = len(lines) * lh
        yo = y - yh // 2

    yo += lh // 8
    text_color = EVENT_TEXT_COLORS.get(event_type, (255, 255, 255))
    shadow_color = (100, 100, 100)

    separator_x += 70

    badge_font = get_font_size(40)
    badge_text = EVENT_NAMES.get(event_type, "EVENT")
    badge_x = separator_x + 50
    badge_y = yo - 80

    padding = 15
    text_width = sum(badge_font.getlength(c) for c in badge_text) + padding * 2
    text_height = badge_font.getbbox(
        "A")[3] - badge_font.getbbox("A")[1] + padding * 2
    badge_bg = Image.new('RGBA', (int(text_width + 20),
                         int(text_height + 20)), (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(badge_bg)

    gradient_start = EVENT_COLORS.get(event_type, (100, 100, 100))
    gradient_end = (
        gradient_start[0] * 2 // 3,
        gradient_start[1] * 2 // 3,
        gradient_start[2] * 2 // 3)
    gradient, gradient_mask = draw_gradient(badge_bg, (int(
        text_width + 20), int(text_height + 20)), gradient_start, gradient_end, opacity=200)
    badge_bg.paste(gradient, (0, 0), mask=gradient_mask)

    badge_draw.rounded_rectangle(
        (10, 10, text_width + 10, text_height + 10),
        radius=15,
        fill=(0, 0, 0, 100)
    )
    badge_draw.rounded_rectangle(
        (5, 5, text_width + 5, text_height + 5),
        radius=15,
        fill=text_color + (220,)
    )
    badge_draw.text(
        (padding, padding), badge_text, fill=(
            255, 255, 255), font=badge_font)

    draw._image.paste(badge_bg, (int(badge_x - padding),
                      int(badge_y - padding)), mask=badge_bg)

    underline_y = yo + yh + 15
    underline_gradient = Image.new('RGB', (image_width - separator_x - 50, 5))
    underline_draw = ImageDraw.Draw(underline_gradient)
    for x in range(image_width - separator_x - 50):
        r = int(text_color[0] * (1 - x / (image_width - separator_x - 50)))
        g = int(text_color[1] * (1 - x / (image_width - separator_x - 50)))
        b = int(text_color[2] * (1 - x / (image_width - separator_x - 50)))
        underline_draw.line((x, 0, x, 5), fill=(r, g, b))
    draw._image.paste(underline_gradient, (separator_x, underline_y))

    icon = EVENT_ICONS.get(event_type, "")
    if icon:
        icon_font = ImageFont.truetype(
            "modules/cache/font/NotoEmoji-Bold.ttf", 100)
        icon_glow = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
        icon_glow_draw = ImageDraw.Draw(icon_glow)
        icon_glow_draw.text(
            (10, 10), icon, fill=text_color + (100,), font=icon_font)
        icon_glow = icon_glow.filter(ImageFilter.GaussianBlur(5))
        draw._image.paste(
            icon_glow,
            (separator_x - 60,
             yo - 40),
            mask=icon_glow)
        draw.text((separator_x - 50, yo - 30), icon,
                  fill=text_color, font=icon_font)

    corner_size = 40
    for corner in [
        ((0, 0), (corner_size, 0), (0, corner_size)),
        ((image_width, 0), (image_width - corner_size, 0), (image_width, corner_size)),
        ((0, image_width), (corner_size, image_width), (0, image_width - corner_size)),
        ((image_width, image_width), (image_width - corner_size, image_width), (image_width, image_width - corner_size))
    ]:
        corner_img = Image.new('RGB', (corner_size, corner_size))
        corner_draw = ImageDraw.Draw(corner_img)
        gradient, _ = draw_gradient(
            corner_img, (corner_size, corner_size), text_color, gradient_end, opacity=255)
        corner_img.paste(gradient, (0, 0))
        corner_draw.polygon(corner, fill=(0, 0, 0, 0))
        draw._image.paste(corner_img, (int(corner[0][0]), int(corner[0][1])))

    for line in lines:
        line_width = sum(emoji_font.getlength(c) if emoji.emoji_count(
            c) else font.getlength(c) for c in line)
        start_x = separator_x + (max_width - line_width) // 2
        draw_text_line(
            draw,
            line,
            start_x,
            yo,
            font,
            emoji_font,
            text_color,
            shadow_color)
        yo += lh


def get_font_size(size=60):
    return ImageFont.truetype("modules/cache/font/BeVietnamPro-Bold.ttf", size)


def make_circle_mask(size, border_width=0):
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse(
        (border_width,
         border_width,
         size[0] -
         border_width,
         size[1] -
         border_width),
        fill=255)
    return mask


def draw_stylized_avatar(
        image,
        avatar_image,
        position,
        size,
        border_color=(
            220,
            220,
            220),
        border_thickness=15):
    scale = 7
    scaled_size = (size[0] * scale, size[1] * scale)
    scaled_border_thickness = border_thickness * scale
    inner_scaled_size = (
        scaled_size[0] -
        2 *
        scaled_border_thickness,
        scaled_size[1] -
        2 *
        scaled_border_thickness)
    avatar_scaled = avatar_image.resize(
        inner_scaled_size, resample=Image.LANCZOS)
    mask_scaled = make_circle_mask(inner_scaled_size)
    glow_size = (scaled_size[0] + 80, scaled_size[1] + 80)
    glow = Image.new("RGBA", glow_size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    inner_glow_color = (
        min(255, border_color[0] + 40),
        min(255, border_color[1] + 40),
        min(255, border_color[2] + 40),
        100
    )
    outer_glow_color = (border_color[0], border_color[1], border_color[2], 60)
    glow_draw.ellipse(
        (40,
         40,
         glow_size[0] - 40,
         glow_size[1] - 40),
        fill=outer_glow_color)
    glow_draw.ellipse(
        (50,
         50,
         glow_size[0] - 50,
         glow_size[1] - 50),
        fill=inner_glow_color)
    glow = glow.filter(ImageFilter.GaussianBlur(20))
    border_img = Image.new("RGBA", scaled_size, (0, 0, 0, 0))
    draw_obj = ImageDraw.Draw(border_img)
    border_top_color = (
        min(255, border_color[0] + 40),
        min(255, border_color[1] + 40),
        min(255, border_color[2] + 40),
        255
    )
    border_bottom_color = (
        max(0, border_color[0] - 40),
        max(0, border_color[1] - 40),
        max(0, border_color[2] - 40),
        255
    )
    gradient, gradient_mask = draw_gradient(
        border_img,
        scaled_size,
        border_top_color,
        border_bottom_color,
        opacity=255
    )
    border_mask = make_circle_mask(scaled_size)
    border_img.paste(gradient, (0, 0), mask=border_mask)
    inner_mask = make_circle_mask(
        (scaled_size[0] - 2 * scaled_border_thickness,
         scaled_size[1] - 2 * scaled_border_thickness)
    )
    inner_mask_img = Image.new("L", scaled_size, 0)
    inner_mask_img.paste(
        inner_mask,
        (scaled_border_thickness, scaled_border_thickness)
    )
    inner_mask_inv = ImageChops.invert(inner_mask_img)
    border_img.putalpha(ImageChops.multiply(border_mask, inner_mask_inv))
    final_img = Image.new("RGBA", glow_size, (0, 0, 0, 0))
    final_img.paste(glow, (0, 0), mask=glow)
    border_offset = (glow_size[0] - scaled_size[0]) // 2
    final_img.paste(
        border_img,
        (border_offset,
         border_offset),
        mask=border_img)
    avatar_offset_x = border_offset + scaled_border_thickness
    avatar_offset_y = border_offset + scaled_border_thickness
    final_img.paste(
        avatar_scaled,
        (avatar_offset_x, avatar_offset_y),
        mask=mask_scaled
    )
    final_img = final_img.resize(
        (size[0] + 35, size[1] + 35),
        resample=Image.LANCZOS
    )
    image.paste(
        final_img,
        (position[0] - 17, position[1] - 17),
        mask=final_img
    )
    return final_img


def calculate_text_height(content, font, image_width):
    lines = split_text_into_lines(content, font, ImageFont.truetype(
        "modules/cache/font/NotoEmoji-Bold.ttf", font.size), int(image_width * 0.6))
    th = font.getbbox("Ay")[3] - font.getbbox("Ay")[1]
    lh = int(th * 1.2)
    return len(lines) * lh


def fetch_image(url):
    if not url:
        return None
    try:
        if url.startswith('data:image'):
            h, e = url.split(',', 1)
            try:
                i = base64.b64decode(e)
            except BaseException:
                return None
            return Image.open(BytesIO(i)).convert("RGB")
        r = requests.get(url, stream=True, timeout=(5, 20))
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print(f"Error fetching image: {e}")
        return None


def process_image(
        avatar_url,
        cover_url,
        content,
        author_name,
        event_time,
        event_type):
    dw, dh = 2000, 760
    f = get_font_size(70)
    text_height = calculate_text_height(content, f, dw)
    cover_width, cover_height = 2000, 760
    avatar_size = 325
    avatar_x = int(dw * 0.03)
    avatar_y = int(dh * 0.5 - avatar_size * 0.5)
    if cover_url == "https://cover-talk.zadn.vn/default" and os.path.exists(
            DEFAULT_COVER_PATH):
        try:
            ci = Image.open(DEFAULT_COVER_PATH).convert("RGB")
        except Exception as e:
            print(f"Error loading default cover: {e}")
            ci = None
    else:
        ci = fetch_image(cover_url)
    if ci:
        ci = ci.resize((cover_width, cover_height))
    text_region_height = text_height + 20
    min_height = max(avatar_y + avatar_size + 50, 280 + text_region_height)
    iw, ih = dw, max(min_height, dh)
    image = Image.new("RGB", (iw, ih), color=(50, 50, 50))
    if ci:
        mi = ci.copy()
        mi = mi.filter(ImageFilter.GaussianBlur(5))
        mi = ImageEnhance.Brightness(mi).enhance(0.7)
        mi = ImageEnhance.Contrast(mi).enhance(1.1)
        image.paste(mi.resize((iw, ih)), (0, 0))
    gradient_start = EVENT_COLORS.get(event_type, (100, 100, 100))
    gradient_end = (
        max(0, gradient_start[0] - 70),
        max(0, gradient_start[1] - 70),
        max(0, gradient_start[2] - 70)
    )
    gradient, gradient_mask = draw_gradient(
        image, (iw, ih), gradient_start, gradient_end, opacity=40)
    image.paste(gradient, (0, 0), mask=gradient_mask)
    ai = fetch_image(avatar_url)
    if ai:
        border_color = EVENT_COLORS.get(event_type, (220, 220, 220))
        draw_stylized_avatar(image, ai, (avatar_x, avatar_y),
                             (avatar_size, avatar_size), border_color=border_color)
        if event_type in [GroupEventType.LEAVE, GroupEventType.REMOVE_MEMBER]:
            draw = ImageDraw.Draw(image)
            cross_color = (255, 70, 70)
            cross_thickness = 20
            shadow_offset = 5
            shadow_color = (100, 30, 30, 150)
            draw.line(
                (avatar_x +
                 shadow_offset,
                 avatar_y +
                 shadow_offset,
                 avatar_x +
                 avatar_size +
                 shadow_offset,
                 avatar_y +
                 avatar_size +
                 shadow_offset),
                fill=shadow_color,
                width=cross_thickness)
            draw.line(
                (avatar_x +
                 avatar_size +
                 shadow_offset,
                 avatar_y +
                 shadow_offset,
                 avatar_x +
                 shadow_offset,
                 avatar_y +
                 avatar_size +
                 shadow_offset),
                fill=shadow_color,
                width=cross_thickness)
            draw.line(
                (avatar_x,
                 avatar_y,
                 avatar_x +
                 avatar_size,
                 avatar_y +
                 avatar_size),
                fill=cross_color,
                width=cross_thickness)
            draw.line(
                (avatar_x +
                 avatar_size,
                 avatar_y,
                 avatar_x,
                 avatar_y +
                 avatar_size),
                fill=cross_color,
                width=cross_thickness)
        draw = ImageDraw.Draw(image)
        separator_x = avatar_x * 2 + avatar_size
        sep_gradient = Image.new('RGBA', (10, avatar_size + 40), (0, 0, 0, 0))
        sep_draw = ImageDraw.Draw(sep_gradient)
        for y in range(avatar_size + 40):
            opacity = 255 if y > 20 and y < avatar_size + \
                20 else int(255 * (1 - abs((y - (avatar_size + 40) / 2) / ((avatar_size + 40) / 2))))
            sep_color = (180, 180, 180, opacity)
            sep_draw.line((0, y, 10, y), fill=sep_color)
        image.paste(
            sep_gradient,
            (separator_x,
             avatar_y - 20),
            mask=sep_gradient)
    draw = ImageDraw.Draw(image)
    ef = ImageFont.truetype("modules/cache/font/NotoEmoji-Bold.ttf", f.size)
    text_x = separator_x
    text_y = ih // 2
    is_long_text = len(content) > 20
    draw_text(draw, content, (text_x, text_y), f, ef,
              iw, separator_x, is_long_text, event_type)
    watermark_font = get_font_size(40)
    watermark_text = "©Latte"
    watermark_color = (255, 255, 255, 120)
    watermark_width = sum(watermark_font.getlength(c) for c in watermark_text)
    watermark_x = iw - watermark_width - 20
    watermark_y = ih - 80
    draw.text((watermark_x, watermark_y), watermark_text,
              fill=watermark_color, font=watermark_font)
    timestamp = event_time.strftime("%d-%m-%Y %H:%M")
    timestamp_width = sum(watermark_font.getlength(c) for c in timestamp)
    timestamp_x = 20
    timestamp_y = ih - 80
    draw.text((timestamp_x, timestamp_y), timestamp,
              fill=watermark_color, font=watermark_font)
    return image


def buildWelcomeMessage(
        self,
        groupName,
        joinMembers,
        sourceId=None,
        is_join_request=False,
        group_type_name="Cộng Đồng"):
    member_list = ', '.join([member.get('dName') for member in joinMembers])
    if sourceId:
        adder_info = self.fetchUserInfo(sourceId)
        adder_name = (
            adder_info["changed_profiles"][sourceId].get("zaloName")
            or adder_info["changed_profiles"][sourceId].get("displayName")
            or "Không xác định"
            if adder_info
            and "changed_profiles" in adder_info
            and sourceId in adder_info["changed_profiles"]
            else "Không xác định"
        )

        if adder_name != "Không xác định":
            if is_join_request:
                text = f"{groupName}\nChào Mừng {member_list}\nĐã Tham Gia {group_type_name}\nDuyệt Bởi {adder_name}"
            else:
                text = f"{groupName}\nChào Mừng {member_list}\nĐã Tham Gia {group_type_name}\nThêm Bởi {adder_name}"
        else:
            text = f"{groupName}\nChào Mừng {member_list}\nĐã Tham Gia {group_type_name}\nTham Gia Trực Tiếp Từ Link Hoặc Được Mời"
    else:
        text = f"{groupName}\nChào Mừng {member_list}\nĐã Tham Gia {group_type_name}\nTham Gia Trực Tiếp Từ Link Hoặc Được Mời"
    return text


def buildLeaveMessage(
        self,
        groupName,
        updateMembers,
        eventType,
        sourceId=None,
        group_type_name="Cộng Đồng"):
    member_name = updateMembers[0].get('dName')
    if eventType == GroupEventType.LEAVE:
        text = f"Member Left The Group\n{member_name}\nVừa Rời Khỏi {group_type_name}\n{groupName}"
    elif eventType == GroupEventType.REMOVE_MEMBER:
        remover_info = self.fetchUserInfo(sourceId)
        remover_name = (
            remover_info["changed_profiles"][sourceId].get("zaloName")
            or remover_info["changed_profiles"][sourceId].get("displayName")
            or "Không xác định"
            if remover_info
            and "changed_profiles" in remover_info
            and sourceId in remover_info["changed_profiles"]
            else "Không xác định"
        )

        if remover_name != "Không xác định":
            text = f"Kick Out Member\n{member_name}\nĐã Bị {remover_name} Kick Khỏi {group_type_name}\n{groupName}"
        else:
            text = f"Kick Out Member\n{member_name}\nĐã Bị Sút Khỏi {group_type_name} {groupName}."
    else:
        return
    return text


def handleGroupEvent(self, eventData, eventType):
    groupId = eventData.get('groupId')
    if not groupId:
        return

    # Kiểm tra trạng thái welcome từ file welcome_setting.json
    allowed_groups = load_allowed_groups()
    if groupId not in allowed_groups:
        return  # Bỏ qua nếu nhóm chưa bật welcome

    group_type = self.fetchGroupInfo(groupId).gridInfoMap[groupId].type
    group_type_name = "Cộng Đồng" if group_type == 2 else "Nhóm"

    if eventType == GroupEventType.JOIN:
        groupName = eventData.get('groupName', "group")
        joinMembers = eventData.get('updateMembers', [])
        sourceId = eventData.get("sourceId")
        is_join_request = False
        if sourceId and not any(sourceId == member.get("id")
                                for member in joinMembers):
            is_join_request = True
        if not joinMembers:
            return
        text = buildWelcomeMessage(
            self,
            groupName,
            joinMembers,
            sourceId,
            is_join_request,
            group_type_name)
        event_time = datetime.now()
        memberIds = [member.get('id') for member in joinMembers]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for member_id in memberIds:
                executor.submit(
                    process_group_event_image,
                    self,
                    member_id,
                    text,
                    groupId,
                    event_time,
                    "ZALOBOT_welcome.jpg",
                    has_mention=True,
                    event_type=eventType)

    elif eventType in {GroupEventType.LEAVE, GroupEventType.REMOVE_MEMBER}:
        groupName = eventData.get('groupName', "group")
        updateMembers = eventData.get('updateMembers', [])
        sourceId = eventData.get("sourceId")
        if not updateMembers:
            return
        text = buildLeaveMessage(
            self,
            groupName,
            updateMembers,
            eventType,
            sourceId,
            group_type_name)
        event_time = datetime.now()
        memberIds = [member.get('id') for member in updateMembers]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for member_id in memberIds:
                executor.submit(
                    process_group_event_image,
                    self,
                    member_id,
                    text,
                    groupId,
                    event_time,
                    "ZALOBOT_leave.jpg",
                    has_mention=False,
                    event_type=eventType)

    elif eventType == GroupEventType.REMOVE_ADMIN:
        groupName = eventData.get('groupName', "group")
        updateMembers = eventData.get('updateMembers', [])
        ow_id = eventData.get("sourceId")
        if not updateMembers:
            return
        member_name = updateMembers[0].get('dName')
        ow_info = self.fetchUserInfo(ow_id)
        ow_name = (
            ow_info.get('changed_profiles', {}).get(ow_id, {}).get('zaloName')
            or ow_info.get('changed_profiles', {}).get(ow_id, {}).get('displayName')
            or "Không xác định"
            if ow_info
            and 'changed_profiles' in ow_info
            and ow_id in ow_info.get('changed_profiles', {})
            else "Không xác định"
        )

        text = f'{groupName}\n{member_name}\nĐã Được {ow_name} Cho Bay Màu Khỏi Danh Sách Quản Trị Viên {group_type_name}'
        event_time = datetime.now()
        member_id = updateMembers[0].get('id')
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(
                process_group_event_image,
                self,
                member_id,
                text,
                groupId,
                event_time,
                "ZALOBOT_remove_admin.jpg",
                has_mention=True,
                event_type=eventType)

    elif eventType == GroupEventType.ADD_ADMIN:
        groupName = eventData.get('groupName', "group")
        updateMembers = eventData.get('updateMembers', [])
        ow_id = eventData.get("sourceId")
        if not updateMembers:
            return
        member_name = updateMembers[0].get('dName')
        ow_info = self.fetchUserInfo(ow_id)
        ow_name = (
            ow_info.get('changed_profiles', {}).get(ow_id, {}).get('zaloName')
            or ow_info.get('changed_profiles', {}).get(ow_id, {}).get('displayName')
            or "Không xác định"
            if ow_info
            and 'changed_profiles' in ow_info
            and ow_id in ow_info.get('changed_profiles', {})
            else "Không xác định"
        )

        text = f'{groupName}\n{member_name}\nĐã Được {ow_name} Bổ Nhiệm Làm Quản Trị Viên {group_type_name}'
        event_time = datetime.now()
        member_id = updateMembers[0].get('id')
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(
                process_group_event_image,
                self,
                member_id,
                text,
                groupId,
                event_time,
                "ZALOBOT_add_admin.jpg",
                has_mention=True,
                event_type=eventType)


def process_group_event_image(
        self,
        member_id,
        text,
        groupId,
        event_time,
        filename,
        has_mention=False,
        event_type=None):
    op = None
    try:
        u = self.fetchUserInfo(member_id) or {}
        ud = u.get('changed_profiles', {}).get(member_id, {})

        av, cv = ud.get('avatar'), ud.get('cover')
        an = ud.get('zaloName', 'không xác định')

        image = process_image(av, cv, text, an, event_time, event_type)
        op = os.path.join("modules/cache", filename)
        image.save(op, quality=100)

        if has_mention:
            self.sendLocalImage(
                op,
                thread_id=groupId,
                thread_type=ThreadType.GROUP,
                width=image.width,
                height=image.height,
                message=Message(
                    mention=Mention(member_id, offset=0)
                ),
                ttl=60000
            )
        else:
            self.sendLocalImage(
                op,
                thread_id=groupId,
                thread_type=ThreadType.GROUP,
                width=image.width,
                height=image.height,
                ttl=60000
            )
    except Exception as e:
        self.logger.error(f"Error processing group event image: {e}")
    finally:
        if op and os.path.exists(op):
            try:
                time.sleep(0.3)
                os.remove(op)
            except Exception as cleanup_err:
                self.logger.error(
                    f"⚠️ Không thể xóa file tạm {op}: {cleanup_err}")

    threading.Thread(target=handleGroupEvent, daemon=True).start()


def TQD():
    return {}
