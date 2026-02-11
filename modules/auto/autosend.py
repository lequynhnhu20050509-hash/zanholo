import time
import random
import json
import logging
import threading
from datetime import datetime
import pytz
import ffmpeg
from zlapi.models import Message, ThreadType

# -----------------------------
# Cấu hình Logging
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# -----------------------------
# Tin nhắn theo giờ
# -----------------------------
time_messages = {
    "00:00": "Bot Duong chúc các cậu ngủ ngon nhé 💫",
    "01:00": "Khuya rồi đó, đi ngủ sớm đi kẻo mai dậy không nổi nha 😴",
    "02:00": "Giờ này mà vẫn thức đúng là siêu nhân luôn á 😵‍💫",
    "03:00": "Trời vẫn còn tối lắm, chúc bạn có giấc ngủ thật sâu 💤",
    "04:00": "Sáng sớm yên tĩnh ghê, ai dậy sớm vậy nè 🌄",
    "05:00": "Bình minh sắp lên rồi! Chuẩn bị chào ngày mới thôi ☀️",
    "06:00": "Chào buổi sáng! Hãy bắt đầu một ngày mới tràn đầy năng lượng 🌞",
    "07:00": "Đã đến giờ uống cà phê! Thưởng thức một tách cà phê nhé ☕",
    "08:00": "Đi học hay đi làm thôi nào, chúc một ngày thuận lợi 💪",
    "09:00": "Chúc bạn một buổi sáng vui vẻ và năng suất 🌻",
    "10:00": "Giữa buổi sáng rồi, cố lên nha! 💼",
    "11:00": "Chỉ còn chút nữa là đến giờ nghỉ trưa rồi đó 🍱",
    "12:00": "Giờ nghỉ trưa! Nạp năng lượng và thư giãn chút nào 😋",
    "13:00": "Chúc bạn buổi chiều làm việc hiệu quả 🌤️",
    "14:00": "Giữ tinh thần làm việc cao nhé, chiều nay cố thêm chút nữa 💪",
    "15:00": "Một buổi chiều vui vẻ! Đừng quên đứng dậy vận động một tí 🚶",
    "16:00": "Sắp hết giờ làm rồi, cố nốt chút nữa nhé 🕓",
    "17:00": "Kết thúc một ngày làm việc! Thư giãn thôi 🎶",
    "18:00": "Chào buổi tối! Nghỉ ngơi và ăn tối thật ngon nha 🍲",
    "19:00": "Bữa tối ngon miệng chưa nè? 😋",
    "20:00": "Buổi tối chill thôi nào, xem phim hay nghe nhạc cũng được 🎧",
    "21:00": "Một buổi tối tuyệt vời! Hãy tận hưởng thời gian bên gia đình 💖",
    "22:00": "Sắp đến giờ đi ngủ! Chuẩn bị cho một giấc ngủ ngon 😴",
    "23:00": "Cất điện thoại đi ngủ thôi nào, thức đêm không tốt đâu 📵",
}

# -----------------------------
# Múi giờ
# -----------------------------
vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")

# -----------------------------
# Hàm load JSON từ file
# -----------------------------
def load_json_file(file_path):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except:
        return []

# -----------------------------
# Load danh sách nhóm
# -----------------------------
def load_allowed_groups():
    try:
        with open("modules/cache/sendtask_autosend.json", "r") as f:
            return json.load(f)
    except:
        return {"groups": []}

# -----------------------------
# Lấy thông tin video
# -----------------------------
def get_video_info(video_url):
    try:
        probe = ffmpeg.probe(video_url)
        video_stream = next((s for s in probe["streams"] if s["codec_type"] == "video"), None)
        if not video_stream:
            return 0, 0, 0

        duration = float(video_stream.get("duration") or probe["format"].get("duration", 0)) * 1000
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        return duration, width, height
    except:
        return 0, 0, 0

# -----------------------------
# Load danh sách video
# -----------------------------
def load_video_lists():
    return {
        "gai": load_json_file("modules/cache/vdgai.json"),
        "anime": load_json_file("modules/cache/vdanime.json"),
        "cos": load_json_file("modules/cache/vdcos.json"),
        "chill": load_json_file("modules/cache/vdchill.json"),
        "nhac": load_json_file("modules/cache/nhac.json"),
    }

# -----------------------------
# Chọn video theo giờ
# -----------------------------
def pick_video_by_hour(hour, vids):
    h = int(hour[:2])

    if 0 <= h <= 3:
        pool = vids["chill"] + vids["nhac"]
    elif 4 <= h <= 6:
        pool = vids["cos"]
    elif 7 <= h <= 10:
        pool = vids["gai"] + vids["chill"]
    elif 11 <= h <= 13:
        pool = vids["nhac"]
    elif 14 <= h <= 17:
        pool = vids["anime"] + vids["gai"]
    elif 18 <= h <= 20:
        pool = vids["nhac"] + vids["chill"]
    elif 21 <= h <= 23:
        pool = vids["gai"] + vids["nhac"]
    else:
        pool = []

    return random.choice(pool) if pool else None

# -----------------------------
# Auto SEND TASK – mỗi nhóm random video
# -----------------------------
def start_auto(client):
    allowed_groups_data = load_allowed_groups()
    allowed_thread_ids = allowed_groups_data.get("groups", [])

    if not allowed_thread_ids:
        logger.error("Không có nhóm nào được cấu hình.")
        return

    video_lists = load_video_lists()
    last_sent_key = None

    while True:
        try:
            now = datetime.now(vn_tz)
            time_str = now.strftime("%H:%M")

            if time_str in time_messages and time_str != last_sent_key:

                text = time_messages[time_str]
                gui_msg = Message(text=f"[ SendTask {time_str} ]\n> {text}")

                # Gửi từng nhóm – MỖI NHÓM RANDOM VIDEO
                for thread_id in allowed_thread_ids:
                    try:
                        selected_video = pick_video_by_hour(time_str, video_lists)

                        if selected_video:
                            duration, w, h = get_video_info(selected_video)

                            client.sendRemoteVideo(
                                selected_video,
                                selected_video,
                                duration=duration,
                                message=gui_msg,
                                thread_id=thread_id,
                                thread_type=ThreadType.GROUP,
                                width=w,
                                height=h,
                                ttl=60000 * 60,
                            )

                        logger.info(f"Đã gửi {time_str} đến nhóm {thread_id}")

                    except Exception as e:
                        logger.error(f"Lỗi gửi nhóm {thread_id}: {e}")

                last_sent_key = time_str

            time.sleep(30)

        except Exception as e:
            logger.error(f"Lỗi vòng lặp auto: {e}")
            time.sleep(10)

# -----------------------------
# Thread chạy auto
# -----------------------------
def run_autosend(client):
    th = threading.Thread(target=start_auto, args=(client,))
    th.daemon = True
    th.start()
