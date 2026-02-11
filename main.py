import json
import os
import time
import sys
import random
import re
import unicodedata
from datetime import datetime, timedelta
import threading
import logging
import urllib.parse
import queue
import math
from PIL import Image
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import ffmpeg
import pyfiglet
from colorama import Fore, Style, init
from zlapi import ZaloAPI
from zlapi.models import *
from config import API_KEY, SECRET_KEY, IMEI, SESSION_COOKIES, ADMIN, ADM, PREFIX
from TQD import CommandHandler
from logging_utils import Logging
from event.event import handleGroupEvent
from threading import Lock
from commands.antispam import AntiSpamHandler
from commands.antilink import AntiLinkHandler
from commands.loctk import LocTKHandler
from commands.antiundo import UndoHandler
from commands.lockbot import LockBotHandler
from commands.whitelist import WhitelistHandler
from commands.cmd import CmdHandler
from commands.bcmd import BcmdHandler
from commands.antiphoto import AntiPhotoHandler
from modules.autojoin import AutoJoinHandler
from commands.antiall import AntiAllHandler
from commands.antivideo import AntiVideoHandler
from commands.antiricon import AntiRiconHandler
from modules.msvc import MSVCHandler
from commands.bot import BotStatusHandler
from commands.antistk import AntiStickerHandler
from commands.antifile import AntiFileHandler
from commands.anticard import AntiCardHandler
from commands.antibot import AntiBotHandler
from concurrent.futures import ThreadPoolExecutor
import collections
from modules import scl
from modules import ytb
from modules.afk import AFKHandler
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor
from modules.chat import handle_chat_command, read_settings
from modules.topchat import update_user_rank
from modules.Atd_mxh import handle_message

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

init(autoreset=True)

colors1 = [
    "FF9900", "FFFF33", "33FFFF", "FF99FF", "FF3366", "FFFF66", "FF00FF", "66FF99",
    "00CCFF", "FF0099", "FF0066", "0033FF", "FF9999", "00FF66", "00FFFF", "CCFFFF",
    "8F00FF", "FF00CC", "FF0000", "FF1100", "FF3300", "FF4400", "FF5500", "FF6600",
    "FF7700", "FF8800", "FF9900", "FFaa00", "FFbb00", "FFcc00", "FFdd00", "FFee00",
    "FFff00", "FFFFFF", "FFEBCD", "F5F5DC", "F0FFF0", "F5FFFA", "F0FFFF", "F0F8FF",
    "FFF5EE", "F5F5F5"
]


def hex_to_ansi(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'\033[38;2;{r};{g};{b}m'


def print_colored_ascii(text):
    colors = [Fore.LIGHTRED_EX, Fore.LIGHTGREEN_EX, Fore.LIGHTYELLOW_EX,
              Fore.LIGHTBLUE_EX, Fore.LIGHTMAGENTA_EX, Fore.LIGHTCYAN_EX]
    ascii_art = pyfiglet.figlet_format(text)
    lines = ascii_art.splitlines()
    for i, line in enumerate(lines):
        print(colors[i % len(colors)] + line + Style.RESET_ALL)


def banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    print_colored_ascii("D - TOOL")


def get_user_name_by_id(bot, user_id):
    try:
        info = bot.fetchUserInfo(user_id)
        if hasattr(info, "changed_profiles") and user_id in info.changed_profiles:
            profile = info.changed_profiles[user_id]
            return getattr(profile, "zaloName", None) or getattr(profile, "displayName", "Unknown User")
        return "Unknown User"
    except Exception:
        return "Unknown User"


COLORS = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA, Fore.WHITE]
main_executor = ThreadPoolExecutor(max_workers=10)

emoji_list = [
    "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🐽",
    "😊", "😇", "🙂", "🙃", "😉", "😌", "😍", "🥰",
    "😘", "😗", "😙", "😚", "😋", "😛", "😜", "🤪",
    "😝", "🤑", "🤗", "🤭", "🤫", "🤔", "🤐", "🤨",
    "😐", "😑", "😶", "😏", "😒", "🙄", "😬", "😮‍💨",
    "🤥", "😌", "😔", "😪", "🤤", "😴", "😷", "🤒",
    "🤕", "🤢", "🤮", "🤧", "🥵", "🥶", "🥴", "😵",
    "😵‍💫", "🤯", "🤠", "🥳", "😎", "🤓", "🧐", "😕",
    "😟", "🙁", "☹️", "😮", "😯", "😲", "😳", "🥺",
    "😦", "😧",  "😖", "😣", "😞","😓", "😩", "😫", 
    "😺", "😸", "😹", "😻", "😼", "😽", "🙀", "😿", 
    "😾"
]

class ResetBot:
    def __init__(self, reset_interval=12500):
        self.reset_event = threading.Event()
        self.reset_interval = reset_interval
        self.load_autorestart_setting()

    def load_autorestart_setting(self):
        try:
            with open("seting.json", "r") as f:
                settings = json.load(f)
                self.autorestart = settings.get("autorestart", "False") == "True"
            if self.autorestart:
                logger.restart("Chế độ auto restart đang được bật")
                threading.Thread(target=self.reset_code_periodically, daemon=True).start()
            else:
                logger.restart("Chế độ auto restart đang được tắt")
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình autorestart: {e}")
            self.autorestart = False

    def reset_code_periodically(self):
        while not self.reset_event.is_set():
            time.sleep(self.reset_interval)
            logger.restart("Đang tiến hành khởi động lại bot...")
            self.restart_bot()

    def restart_bot(self):
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            gui_message = f"Bot đã khởi động lại thành công vào lúc: {current_time}"
            logger.restart(gui_message)
            python = sys.executable
            os.execl(python, python, *sys.argv)
        except Exception as e:
            logger.error(f"Lỗi khi khởi động lại bot: {e}")


logger = Logging()


class Client(ZaloAPI):
    def __init__(self, api_key, secret_key, imei, session_cookies, reset_interval=12500, auto_approve_interval=0):
        self.uid = None
        self._imei = imei
        super().__init__(api_key, secret_key, imei=imei, session_cookies=session_cookies)
        self.scl_user_states = {}
        self.settings = self.load_settings()
        self.ADMIN = str(self.settings.get("admin") or ADMIN)
        self.ADM = [str(uid) for uid in (self.settings.get("adm", []) or ADM)]
        if not self.uid:
            try:
                self.uid = self.fetchAccountInfo().profile.get("userId")
            except Exception as e:
                logger.error(f"Không thể fetch UID của bot sau khi login: {e}")
                sys.exit("Lỗi nghiêm trọng: Không xác định được UID của bot.")
        logger.info(f"Admin ID: {self.ADMIN}")
        logger.info(f"Additional Admins: {self.ADM}")
        logger.info(f"Bot Main đã đăng nhập thành công với UID: {self.uid}")
        self.command_handler = CommandHandler(self)
        self.reset_bot = ResetBot(reset_interval)
        self.session = requests.Session()
        retry_strategy = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.response_time_limit = timedelta(seconds=0)
        self.group_info_cache = {}
        self.last_sms_times = {}
        self.temp_thread_storage = {}
        self.search_results = {}
        self.search_result_messages = {}
        self.search_result_ttl = 24
        self.scl_user_states = {}
        self.ytb_user_states = {}
        self.spam_enabled = self.load_spam_settings()
        self.group_lock_status = {}
        self.bot_status_handler = BotStatusHandler(self)
        self.user_message_times = {}
        self.warned_users = {}
        self.spam_threshold = 5
        self.kick_threshold = 6
        self.spam_window = 7
        self.antiricon_handler = AntiRiconHandler(self)
        self.antifile_handler = AntiFileHandler(self)
        self.antibot_handler = AntiBotHandler(self)
        self.anticard_handler = AntiCardHandler(self)
        self.loctk_enabled = self.load_loctk_settings()
        self.banned_words = self.load_banned_words()
        self.banned_word_violations = {}
        self.FileNM = 'database/dataundo.json'
        self.locked_users_file = 'data/locked_users.json'
        self.locked_users = self.load_locked_users()
        self.afk_handler = AFKHandler(self)
        self.antispam_handler = AntiSpamHandler(self)
        self.antisticker_handler = AntiStickerHandler(self)
        self.loctk_handler = LocTKHandler(self)
        self.undo_handler = UndoHandler(self)
        self.lockbot_handler = LockBotHandler(self)
        self.antilink_handler = AntiLinkHandler(self)
        self.whitelist_handler = WhitelistHandler(self)
        self.bcmd_handler = BcmdHandler(self)
        self.cmd_handler = CmdHandler(self)
        self.autojoin_handler = AutoJoinHandler(self)
        self.msvc_handler = MSVCHandler(self)
        self.antiall_handler = AntiAllHandler(self)
        self.antiphoto_handler = AntiPhotoHandler(self)
        self.antivideo_handler = AntiVideoHandler(self)
        self.auto_approve_enabled = self.load_auto_approve_settings()
        self.auto_approve_interval = auto_approve_interval
        self.last_auto_approve_check = datetime.min
        self.group_message_counts = {}
        self.duyetbox_data = self.load_duyetbox_data()
        self.whitelist = self.load_whitelist()
        self.whitelist_lock = Lock()
        self.sendtask_autosticker_file = "modules/cache/sendtask_autosticker.json"
        self.datasticker_file = "database/datasticker.json"
        threading.Thread(target=self.auto_approve_periodically, daemon=True).start()
        logger.info('EVENT GROUP: Tiến hành nhận sự kiện các nhóm...')
        self.load_sticker_data()
        if not os.path.exists("data/whitelist.json"):
            with open("data/whitelist.json", "w") as f:
                json.dump({}, f)

    def load_whitelist(self):
        try:
            if not os.path.exists("data/whitelist.json"):
                logger.warning("Whitelist file not found, creating empty whitelist")
                with open("data/whitelist.json", "w") as f:
                    json.dump({}, f)
                return {}
            with open("data/whitelist.json", "r", encoding="utf-8") as f:
                whitelist = json.load(f)
                logger.info(f"Loaded whitelist: {whitelist}")
                return whitelist
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding whitelist.json: {e}. Initializing empty whitelist.")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error loading whitelist: {e}. Initializing empty whitelist.")
            return {}

    def save_whitelist(self):
        with self.whitelist_lock:
            try:
                with open("data/whitelist.json", "w", encoding="utf-8") as f:
                    json.dump(self.whitelist, f, indent=4, ensure_ascii=False)
                logger.info("Whitelist saved successfully")
            except Exception as e:
                logger.error(f"Error saving whitelist: {e}")

    def load_sticker_data(self):
        try:
            with open(self.datasticker_file, "r") as f:
                self.sticker_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.sticker_data = []
            self.save_sticker_data()

    def save_sticker_data(self):
        with open(self.datasticker_file, "w") as f:
            json.dump(self.sticker_data, f, indent=4)

    def load_allowed_groups(self):
        try:
            with open(self.sendtask_autosticker_file, "r") as f:
                return json.load(f).get("groups", [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_allowed_groups(self, allowed_groups):
        with open(self.sendtask_autosticker_file, "w") as f:
            json.dump({"groups": allowed_groups}, f, indent=4)

    def auto_approve_periodically(self):
        while True:
            self.check_and_handle_auto_approve()
            time.sleep(self.auto_approve_interval)

    def onEvent(self, event_data, event_type):
        handleGroupEvent(self, event_data, event_type)

    def send_request(self, url):
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi request: {e}")
            return None

    def load_auto_approve_settings(self):
        try:
            with open("data/auto_approve_settings.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            logger.error("Lỗi khi đọc file auto_approve_settings.json. Khởi tạo settings trống.")
            return {}

    def save_auto_approve_settings(self):
        try:
            with open("data/auto_approve_settings.json", "w") as f:
                json.dump(self.auto_approve_enabled, f, indent=4)
        except Exception as e:
            logger.error(f"Lỗi khi lưu cài đặt auto-approve: {e}")

    def reload_duyetbox_data(self):
        self.duyetbox_data = self.load_duyetbox_data()
        logger.info("[Duyệt Box] Đã tải lại dữ liệu duyệt box.")

    def handle_auto_approve_command(self, message_text, message_object, thread_id, thread_type, author_id):
        if str(author_id) != self.ADMIN and str(author_id) not in self.ADM:
            self.replyMessage(Message(text="Bạn không có quyền sử dụng lệnh này. Chỉ quản trị viên mới có thể thực hiện."), message_object, thread_id, thread_type, ttl=60000)
            return
        parts = message_text.split()
        if len(parts) < 2:
            self.replyMessage(Message(text=f"Hướng dẫn sử dụng: {PREFIX}autoapprv <on/off>\nVí dụ: {PREFIX}autoapprv on (Bật tự động duyệt thành viên mới)"), message_object, thread_id, thread_type, ttl=60000)
            return
        action = parts[1].lower()
        if action == "on":
            self.auto_approve_enabled[thread_id] = True
            self.save_auto_approve_settings()
            self.replyMessage(Message(text="Đã bật chế độ tự động duyệt thành viên mới trong nhóm này."), message_object, thread_id, thread_type, ttl=60000)
        elif action == "off":
            self.auto_approve_enabled[thread_id] = False
            self.save_auto_approve_settings()
            self.replyMessage(Message(text="Đã tắt chế độ tự động duyệt thành viên mới trong nhóm này."), message_object, thread_id, thread_type, ttl=60000)
        else:
            self.replyMessage(Message(text=f"Lệnh không hợp lệ. Vui lòng sử dụng '{PREFIX}autoapprv on' hoặc '{PREFIX}autoapprv off'."), message_object, thread_id, thread_type, ttl=60000)

    def load_spam_settings(self):
        try:
            with open("data/spam_settings.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            logger.error("Lỗi khi đọc file spam_settings.json. Khởi tạo settings trống.")
            return {}

    def save_spam_settings(self):
        try:
            with open("data/spam_settings.json", "w") as f:
                json.dump(self.spam_enabled, f, indent=4)
        except Exception as e:
            logger.error(f"Lỗi khi lưu cài đặt anti-spam: {e}")

    def load_loctk_settings(self):
        try:
            with open("data/loctk_settings.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            logger.error("Lỗi khi đọc file loctk_settings.json. Khởi tạo settings trống.")
            return {}

    def save_loctk_settings(self):
        try:
            with open("data/loctk_settings.json", "w") as f:
                json.dump(self.loctk_enabled, f, indent=4)
        except Exception as e:
            logger.error(f"Lỗi khi lưu cài đặt lọc từ: {e}")

    def load_banned_words(self):
        try:
            with open("data/banned_words.json", "r", encoding='utf-8') as f:
                data = json.load(f)
                return data.get("banned_words", {"words": []}).get("words", [])
        except FileNotFoundError:
            logger.error("File banned_words.json không tìm thấy.")
            return []
        except json.JSONDecodeError:
            logger.error("Lỗi khi đọc file banned_words.json.")
            return []

    def save_banned_words(self):
        try:
            with open("data/banned_words.json", "w", encoding='utf-8') as f:
                json.dump({"banned_words": {"words": self.banned_words}}, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Lỗi khi lưu danh sách từ cấm: {e}")

    def send_sticker(self, id, catId, thread_id, thread_type, author_id, message_object):
        try:
            author_info_for_sticker = self.fetchUserInfo(author_id)
            if author_info_for_sticker and getattr(author_info_for_sticker, "changed_profiles", None):
                fetched_name = author_info_for_sticker.changed_profiles.get(author_id, {}).get('zaloName')
                author_display_name_sticker = fetched_name if fetched_name and fetched_name != 'không xác định' else str(author_id)
            else:
                author_display_name_sticker = str(author_id)
            text = f"[UNDO STICKER] {author_display_name_sticker} vừa thu hồi một sticker."
            styles = MultiMsgStyle([
                MessageStyle(offset=len(" "), length=len("[UNDO STICKER]"), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=len(" "), length=len("[UNDO STICKER]"), style="bold", auto_format=False),
            ])
            offset = text.find(f"{author_display_name_sticker}")
            self.replyMessage(Message(text=text, mention=Mention(author_id, len(f"{author_display_name_sticker}"), offset), style=styles), message_object, thread_id, thread_type, ttl=120000)
            self.sendSticker(1, id, catId, thread_id, thread_type)
        except Exception as e:
            logger.error(f"Lỗi khi gửi sticker: {e}")

    def handle_lockbot_command(self, message_text, message_object, thread_id, thread_type, author_id):
        self.lockbot_handler.handle_lockbot_command(message_text, message_object, thread_id, thread_type, author_id)

    def handle_unlockbot_command(self, message_text, message_object, thread_id, thread_type, author_id):
        self.lockbot_handler.handle_unlockbot_command(message_text, message_object, thread_id, thread_type, author_id)

    def load_mute_list(self):
        mute_tmq = "data/khoamom.json"
        if os.path.exists(mute_tmq):
            with open(mute_tmq, 'r') as f:
                return json.load(f)
        return {}

    def is_user_muted(self, thread_id, author_id):
        mute_list = self.load_mute_list()
        if thread_id in mute_list:
            return str(author_id) in mute_list[thread_id]
        return False

    def is_group_admin(self, thread_id, user_id):
        try:
            if thread_id in self.group_info_cache:
                group_data = self.group_info_cache[thread_id]
            else:
                group_info = self.fetchGroupInfo(thread_id)
                if not group_info or not hasattr(group_info, 'gridInfoMap') or thread_id not in group_info.gridInfoMap:
                    logger.warning(f"Không tìm thấy thông tin nhóm hoặc gridInfoMap cho thread_id: {thread_id} để kiểm tra admin.")
                    return False
                group_data = group_info.gridInfoMap[thread_id]
                self.group_info_cache[thread_id] = group_data
            creator_id = group_data.get('creatorId')
            admin_ids = group_data.get('adminIds', [])
            user_id_str = str(user_id)
            if user_id_str == str(creator_id) or user_id_str in [str(admin_id) for admin_id in admin_ids]:
                return True
            return False
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra admin nhóm {thread_id} cho user {user_id}: {e}")
            return False

    def get_content_message(self, message_object):
        if message_object.msgType == 'chat.recommended':            
            return ""
        texts = []
        if hasattr(message_object, 'text') and isinstance(message_object.text, str):
            texts.append(message_object.text)
        elif message_object.get('msg') and isinstance(message_object.get('msg'), str):
            texts.append(message_object.get('msg'))
        content = message_object.get('content')
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, dict):
            if content.get('title') and isinstance(content['title'], str):
                texts.append(content['title'])
            if content.get('href') and isinstance(content['href'], str):
                texts.append(content['href'])
            if content.get('description') and isinstance(content['description'], str):
                texts.append(content['description'])
            if content.get('params') and isinstance(content['params'], str):
                try:
                    params_data = json.loads(content['params'])
                    if params_data.get('mediaTitle') and isinstance(params_data['mediaTitle'], str):
                        texts.append(params_data['mediaTitle'])
                    if params_data.get('href') and isinstance(params_data['href'], str):
                        texts.append(params_data['href'])
                    if params_data.get('url') and isinstance(params_data['url'], str):
                        texts.append(params_data['url'])
                except json.JSONDecodeError:
                    pass
        attach = message_object.get('attach')
        if isinstance(attach, dict):
            if attach.get('title') and isinstance(attach['title'], str):
                texts.append(attach['title'])
            if attach.get('href') and isinstance(attach['href'], str):
                texts.append(attach['href'])
            if attach.get('description') and isinstance(attach['description'], str):
                texts.append(attach['description'])
            if attach.get('params') and isinstance(attach['params'], str):
                try:
                    params_data = json.loads(attach['params'])
                    if params_data.get('mediaTitle') and isinstance(params_data['mediaTitle'], str):
                        texts.append(params_data['mediaTitle'])
                    if params_data.get('href') and isinstance(params_data['href'], str):
                        texts.append(params_data['href'])
                    if params_data.get('url') and isinstance(params_data['url'], str):
                        texts.append(params_data['url'])
                except json.JSONDecodeError:
                    pass
        return " ".join(filter(None, texts))

    def is_url_in_message(self, message_object):
        msg_type = message_object.get('msgType', '')
        absolutely_ignored_msg_types = ['share.file', 'chat.sticker', 'chat.voice', 'chat.gif', 'chat.location.new']
        if msg_type in absolutely_ignored_msg_types:
            return False
        url_regex = re.compile(r'(?:(?:https?://)|(?:www\.))[\w.-]+\.(?:[a-zA-Z]{2,})[\w\/?=&%.-]*|(?<!\w)[\w-]+\.(com|vn|net|org|info|xyz|me|link|top|site|io|tv|cc|biz|us|uk|au|ca)(?:\.[\w-]+)*[\w\/?=&%.-]*(?!\w)', re.IGNORECASE)
        if msg_type.startswith('chat.photo') or msg_type.startswith('chat.video'):
            title_to_check = []
            content = message_object.get('content', {})
            if isinstance(content, dict) and content.get('title'):
                title_to_check.append(content.get('title'))
            attach = message_object.get('attach', {})
            if isinstance(attach, dict) and attach.get('title'):
                title_to_check.append(attach.get('title'))
            if not title_to_check:
                return False
            text_from_title = " ".join(title_to_check)
            if url_regex.search(text_from_title):
                logger.info(f"ANTI-LINK: Phát hiện link trong mô tả của tin nhắn {msg_type}.")
                return True
            return False
        text_to_check = self.get_content_message(message_object)
        if not text_to_check:
            return False
        if url_regex.search(text_to_check):
            logger.info(f"ANTI-LINK: Phát hiện link trong tin nhắn loại '{msg_type}'.")
            return True
        return False

    def check_and_handle_auto_approve(self):
        now = datetime.now()
        if (now - self.last_auto_approve_check).total_seconds() >= self.auto_approve_interval:
            for thread_id, enabled in self.auto_approve_enabled.items():
                if enabled:
                    self.auto_approve_pending_members(thread_id)
            self.last_auto_approve_check = now

    def auto_approve_pending_members(self, thread_id):
        try:
            group_info = self.fetchGroupInfo(thread_id)
            if not group_info or not hasattr(group_info, 'gridInfoMap'):
                return False
            group_data = group_info.get('gridInfoMap', {}).get(thread_id)
            if not isinstance(group_data, dict):
                return False
            pending_members = group_data.get('pendingApprove', {}).get('uids', [])
            for member_id in pending_members:
                if hasattr(self, 'handleGroupPending'):
                    if thread_id in self.auto_approve_enabled:
                        self.handleGroupPending(member_id, thread_id)
            return True
        except Exception as e:
            return False

    def handle_auto_sticker(self, thread_id, thread_type, message_object):
        allowed_groups = self.load_allowed_groups()
        if thread_type == ThreadType.GROUP and thread_id in allowed_groups:
            if message_object.msgType == "webchat":
                self.group_message_counts[thread_id] = self.group_message_counts.get(thread_id, 0) + 1
                if self.group_message_counts[thread_id] >= random.randint(10, 15):
                    if self.sticker_data:
                        sticker = random.choice(self.sticker_data)
                        self.sendSticker(1, sticker["id"], sticker["catId"], thread_id, thread_type)
                        self.group_message_counts[thread_id] = 0

    def load_settings(self):
        try:
            with open("seting.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("Không tìm thấy file seting.json")
            return {}
        except json.JSONDecodeError:
            logger.error("Lỗi giải mã JSON trong file seting.json")
            return {}

    def load_duyetbox_data(self):
        try:
            with open("modules/cache/duyetboxdata.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("Không tìm thấy file duyetboxdata.json")
            return []
        except json.JSONDecodeError:
            logger.error("Lỗi giải mã JSON trong file duyetboxdata.json")
            return []

    def is_allowed_author(self, author_id):
        return str(author_id) == self.ADMIN or str(author_id) in self.ADM

    def is_duyetbox_thread(self, thread_id):
        return str(thread_id) in self.duyetbox_data

    def check_spam(self, author_id, message_object, thread_id, thread_type):
        if message_object.get('msgType') == 'chat.reaction':
            return
        if self.is_allowed_author(author_id) or self.is_group_admin(thread_id, author_id):
            return
        if not self.spam_enabled.get(thread_id, False):
            return
        if thread_id in self.whitelist and str(author_id) in self.whitelist[thread_id]:
            return
        now = time.time()
        if thread_id not in self.user_message_times:
            self.user_message_times[thread_id] = {}
        if author_id not in self.user_message_times[thread_id]:
            self.user_message_times[thread_id][author_id] = []
        user_messages = self.user_message_times[thread_id][author_id]
        user_messages.append(now)
        user_messages = [timestamp for timestamp in user_messages if now - timestamp <= self.spam_window]
        self.user_message_times[thread_id][author_id] = user_messages
        if len(user_messages) == self.spam_threshold:
            self.handle_spam_warn(author_id, message_object, thread_id, thread_type)
        elif len(user_messages) >= self.kick_threshold:
            self.handle_spam_violation(author_id, message_object, thread_id, thread_type)
            del self.user_message_times[thread_id][author_id]

    def check_banned_words(self, message, message_object, thread_id, thread_type, author_id):
        if self.is_allowed_author(author_id) or self.is_group_admin(thread_id, author_id):
            return
        if thread_id in self.whitelist and str(author_id) in self.whitelist[thread_id]:
            return
        if not self.loctk_enabled.get(thread_id, False):
            return
        normalized_message = unicodedata.normalize('NFKC', message).lower()
        found_banned_word = None
        for word in self.banned_words:
            normalized_word = unicodedata.normalize('NFKC', word).lower()
            if re.search(r'\b' + re.escape(normalized_word) + r'\b', normalized_message):
                found_banned_word = word
                break
        if found_banned_word:
            self.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
            self.record_banned_word_violation(author_id, thread_id, message_object, found_banned_word, message)
            return

    def handle_spam_warn(self, user_id, message_object, thread_id, thread_type):
        if message_object.get('msgType') == 'chat.reaction':
            return
        if self.is_allowed_author(user_id) or self.is_group_admin(thread_id, user_id):
            return
        user_info = self.fetchUserInfo(user_id)
        if user_info and getattr(user_info, "changed_profiles", None):
            fetched_name = user_info.changed_profiles.get(user_id, {}).get('zaloName')
            display_name = fetched_name if fetched_name and fetched_name != 'không xác định' else str(user_id)
        else:
            display_name = str(user_id)
        tag = f"{display_name}"
        msg = f"[ANTI-SPAM]\n{tag}\nĐang gửi tin nhắn quá nhanh.\nVui lòng giảm tốc độ để tránh bị hệ thống chặn khỏi nhóm!"
        styles = MultiMsgStyle([
            MessageStyle(offset=len(" "), length=len("[ANTI-SPAM]"), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=len(" "), length=len("[ANTI-SPAM]"), style="bold", auto_format=False),
        ])
        self.replyMessage(Message(text=msg, mention=Mention(user_id, length=len(tag), offset=msg.find(tag)), style=styles), message_object, thread_id, thread_type, ttl=30000)
        if user_id not in self.warned_users:
            self.warned_users[user_id] = {}
        self.warned_users[user_id][thread_id] = True

    def handle_spam_violation(self, user_id, message_object, thread_id, thread_type):
        if self.is_allowed_author(user_id) or self.is_group_admin(thread_id, user_id):
            return
        user_info = self.fetchUserInfo(user_id)
        display_name = str(user_id)
        if user_info and getattr(user_info, "changed_profiles", None):
            fetched_name = user_info.changed_profiles.get(user_id, {}).get('zaloName')
            if fetched_name and fetched_name != 'không xác định':
                display_name = fetched_name
        group_info = self.fetchGroupInfo(thread_id)
        if not group_info or thread_id not in group_info.gridInfoMap:
            return
        group_data = group_info.gridInfoMap[thread_id]
        creator_id = group_data.get('creatorId')
        admin_ids = group_data.get('adminIds', [])
        if str(self.uid) not in [str(admin) for admin in admin_ids] and str(self.uid) != str(creator_id):
            return
        if user_id in self.warned_users and thread_id in self.warned_users[user_id]:
            del self.warned_users[user_id][thread_id]
        if self.group_lock_status.get(thread_id):
            try:
                self.blockUsersInGroup(user_id, thread_id)
                self._send_kick_notification(user_id, thread_id, display_name, message_object, is_secondary_kick=True)
            except BaseException:
                pass
            return
        threading.Thread(target=self._lock_kick_and_unlock, args=(user_id, thread_id, display_name, message_object)).start()

    def _send_kick_notification(self, user_id, thread_id, display_name, message_object, is_secondary_kick=False):
        tag_user = f"{display_name}"
        if is_secondary_kick:
            initial_text = "[ANTI-SPAM]\n"
        else:
            initial_text = "[ANTI-SPAM]\nHệ thống phát hiện vi phạm spam trong nhóm. Tạm khóa chat để xử lý.\n"
        msg_text = f"{initial_text}{tag_user}\nĐã bị chặn khỏi nhóm.\nHệ thống sẽ sớm mở lại chat."
        styles = MultiMsgStyle([
            MessageStyle(offset=msg_text.find("[ANTI-SPAM]"), length=len("[ANTI-SPAM]"), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=msg_text.find("[ANTI-SPAM]"), length=len("[ANTI-SPAM]"), style="bold", auto_format=False),
        ])
        self.replyMessage(Message(text=msg_text, mention=Mention(user_id, len(tag_user), offset=msg_text.find(tag_user)), style=styles), message_object, thread_id, ThreadType.GROUP, ttl=120000)

    def _lock_kick_and_unlock(self, user_id, thread_id, display_name, message_object):
        self.group_lock_status[thread_id] = True
        try:
            self.changeGroupSetting(thread_id, lockSendMsg=1)
            time.sleep(0)
            self.blockUsersInGroup(user_id, thread_id)
            self._send_kick_notification(user_id, thread_id, display_name, message_object)
            time.sleep(5)
        except Exception as e:
            pass
        finally:
            self.changeGroupSetting(thread_id, lockSendMsg=0)
            self.sendMessage(Message(text="Chat đã được mở lại. Mọi người vui lòng tuân phủ quy định nhóm."), thread_id, ThreadType.GROUP, ttl=15000)
            if thread_id in self.group_lock_status:
                del self.group_lock_status[thread_id]

    def record_banned_word_violation(self, user_id, thread_id, message_object, banned_word, original_message_text):
        if self.is_allowed_author(user_id) or self.is_group_admin(thread_id, user_id):
            return
        if thread_id not in self.banned_word_violations:
            self.banned_word_violations[thread_id] = {}
        if user_id not in self.banned_word_violations[thread_id]:
            self.banned_word_violations[thread_id][user_id] = 0
        self.banned_word_violations[thread_id][user_id] += 1
        violations = self.banned_word_violations[thread_id][user_id]
        user_info = self.fetchUserInfo(user_id)
        if user_info and hasattr(user_info, 'changed_profiles'):
            fetched_name = user_info.changed_profiles.get(user_id, {}).get('zaloName')
            display_name = fetched_name if fetched_name and fetched_name != 'không xác định' else str(user_id)
        else:
            display_name = str(user_id)
        tag_user = f"{display_name}"
        if violations == 3:
            msg = f"[LỌC TC]\n{tag_user}\nĐã vi phạm quy định về từ ngữ thô tục ({violations}/5 lần).\nVui lòng chú ý ngôn từ của bạn. Tiếp tục vi phạm sẽ dẫn đến việc bị chặn khỏi nhóm!"
            styles = MultiMsgStyle([
                MessageStyle(offset=len(""), length=len("[LỌC TC]"), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=len(""), length=len("[LỌC TC]"), style="bold", auto_format=False),
            ])
            self.replyMessage(Message(text=msg, mention=Mention(user_id, len(tag_user), offset=msg.find(tag_user)), style=styles), message_object, thread_id, ThreadType.GROUP, ttl=120000)
        elif violations >= 5:
            group_info = self.fetchGroupInfo(thread_id)
            if not group_info or thread_id not in group_info.gridInfoMap:
                return
            group_data = group_info.gridInfoMap[thread_id]
            creator_id = group_data.get('creatorId')
            admin_ids = group_data.get('adminIds', [])
            if self.uid not in admin_ids and self.uid != creator_id:
                return
            self.blockUsersInGroup(user_id, thread_id)
            msg = f"[LỌC TC] {tag_user}\nĐã bị chặn khỏi nhóm do vi phạm quy định về từ ngữ thô tục quá nhiều lần ({violations}/5 lần).\nNội dung vi phạm: '{original_message_text}'"
            styles = MultiMsgStyle([
                MessageStyle(offset=len(""), length=len("[LỌC TC]"), style="color", color="#db342e", auto_format=False),
                MessageStyle(offset=len(""), length=len("[LỌC TC]"), style="bold", auto_format=False),
            ])
            self.replyMessage(Message(text=msg, mention=Mention(user_id, len(tag_user), offset=msg.find(tag_user)), style=styles), message_object, thread_id, ThreadType.GROUP, ttl=120000)

    def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
        main_executor.submit(self._process_message_async, mid, author_id, message, message_object, thread_id, thread_type)
        handle_chat_command(message, message_object, thread_id, thread_type, author_id, self)
        update_user_rank(self, thread_id, author_id)        
        handle_message(message, message_object, thread_id, thread_type, author_id, self)
        try:
           if getattr(message_object, "mentions", None): 
                for mention in message_object.mentions:
                      if str(mention.uid) == ADMIN:
                         now = time.time()                
                         if not hasattr(self, 'mention_data'):
                              self.mention_data = {}  # { user_id: {"time": last_reply, "count": n} }
                         user_data = self.mention_data.get(author_id, {"time": 0, "count": 0})                
                         if now - user_data["time"] >= 900:
                              user_data = {"time": now, "count": 0}               
                         user_data["count"] += 1
                         user_data["time"] = now
                         self.mention_data[author_id] = user_data                                              
                                                      
                         for i in range(20):
                            self.sendReaction(message_object, random.choice(emoji_list), thread_id, thread_type)
                
        except Exception as e:
             print("Error in mention handler:", e)

        
    def _process_message_async(self, mid, author_id, message, message_object, thread_id, thread_type):
        try:
            user_info_for_display = self.fetchUserInfo(author_id)
            if user_info_for_display and getattr(user_info_for_display, "changed_profiles", None):
                fetched_name = user_info_for_display.changed_profiles.get(author_id, {}).get('zaloName')
                author_display_name = fetched_name if fetched_name and fetched_name != 'không xác định' else str(author_id)
            else:
                author_display_name = str(author_id)
        except Exception:
            author_display_name = str(author_id)

        current_time = time.time()
        if not hasattr(self, "log_rate_limit"):
            self.log_rate_limit = defaultdict(lambda: deque(maxlen=7))
        if not hasattr(self, "log_blocked_users"):
            self.log_blocked_users = {}
        self.LOG_LIMIT_COUNT = 5
        self.LOG_LIMIT_SECONDS = 5
        self.LOG_BLOCK_DURATION = 30 * 60

        if str(author_id) == self.ADMIN or str(author_id) in self.ADM:
            pass
        else:
            if author_id in self.log_blocked_users:
                ban_end = self.log_blocked_users[author_id]
                if current_time < ban_end:
                    return
                else:
                    del self.log_blocked_users[author_id]
                    logger.info(f"Đã gỡ chặn log cho {author_display_name} ({author_id}) sau 30 phút.")
            timestamps = self.log_rate_limit[author_id]
            timestamps.append(current_time)
            if len(timestamps) >= self.LOG_LIMIT_COUNT and (current_time - timestamps[0]) <= self.LOG_LIMIT_SECONDS:
                self.log_blocked_users[author_id] = current_time + self.LOG_BLOCK_DURATION
                remaining = int((self.log_blocked_users[author_id] - current_time) / 60)
                logger.warning(f"PHÁT HIỆN SPAM LOG!\n→ Tên: {author_display_name}\n→ ID: {author_id}\n→ Gửi {self.LOG_LIMIT_COUNT} tin trong {self.LOG_LIMIT_SECONDS}s\n→ ĐÃ BỊ CHẶN GHI LOG TRONG {remaining} PHÚT!\n------------------------------")
                return

        log_text = message.text if isinstance(message, Message) else str(message)
        if not log_text.strip():
            log_text = "[Tin nhắn không có nội dung]"

        safe_text = self.get_content_message(message_object)
        if not safe_text.strip():
            safe_text = ""

        try:
            group_name = "N/A"
            if thread_type == ThreadType.GROUP:
                group_info = self.fetchGroupInfo(thread_id)
                if group_info and hasattr(group_info, 'gridInfoMap') and thread_id in group_info.gridInfoMap:
                    group_name = group_info.gridInfoMap[thread_id].get('name', 'N/A')
            colors_selected = random.sample(colors1, 8)
            current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            output = (
                f"{hex_to_ansi(colors_selected[1])}{Style.BRIGHT}• Message: {log_text}{Style.RESET_ALL}\n"
                f"{hex_to_ansi(colors_selected[1])}{Style.BRIGHT}• Message ID: {mid}{Style.RESET_ALL}\n"
                f"{hex_to_ansi(colors_selected[2])}{Style.BRIGHT}• ID NGƯỜI DÙNG: {author_id}{Style.RESET_ALL}\n"
                f"{hex_to_ansi(colors_selected[6])}{Style.BRIGHT}• TÊN NGƯỜI DÙNG: {author_display_name}{Style.RESET_ALL}\n"
                f"{hex_to_ansi(colors_selected[3])}{Style.BRIGHT}• ID NHÓM: {thread_id}{Style.RESET_ALL}\n"
                f"{hex_to_ansi(colors_selected[4])}{Style.BRIGHT}• TÊN NHÓM: {group_name}{Style.RESET_ALL}\n"
                f"{hex_to_ansi(colors_selected[7])}{Style.BRIGHT}• Loại tin nhắn: {message_object.msgType}{Style.RESET_ALL}\n"
                f"{hex_to_ansi(colors_selected[5])}{Style.BRIGHT}• Nhóm or Chat: {thread_type}{Style.RESET_ALL}\n"
                f"{hex_to_ansi(colors_selected[7])}{Style.BRIGHT}• THỜI GIAN NHẬN ĐƯỢC: {current_time_str}{Style.RESET_ALL}\n"
                f"{hex_to_ansi(colors_selected[0])}{Style.BRIGHT}------------------------------{Style.RESET_ALL}"
            )
            print(output)
        except Exception as e:
            logger.error(f"Lỗi khi ghi log tin nhắn: {e}")

        if message_object.get('msgType') == 'chat.undo':
            if thread_type == ThreadType.GROUP:
                if self.undo_handler.is_undo_enabled(thread_id):
                    self.undo_handler.handle_undo_event(message_object, thread_id, thread_type, author_id)
            return

        if message_object.get('msgType') == 'chat.delete':
            return
        if self.is_allowed_author(author_id):
            pass
        elif thread_type == ThreadType.GROUP:
            if not self.bot_status_handler.is_bot_enabled(thread_id):
                return
            is_bot_command = safe_text.lower().strip().startswith(f"{PREFIX}bot")
            if is_bot_command:
                self.bot_status_handler.handle_bot_command(safe_text, message_object, thread_id, thread_type, author_id)
                return

        try:
            if message_object.get("msgType") == "chat.reaction":
                reaction_author_id = str(author_id)
                if thread_type == ThreadType.GROUP:
                    if self.bot_status_handler.is_bot_enabled(thread_id) or self.is_allowed_author(author_id):
                        self.antiricon_handler.check_spam_reaction(reaction_author_id, message_object, thread_id, thread_type)
                return

            if safe_text.strip().isdigit():
                if author_id in self.scl_user_states:
                    scl_state = self.scl_user_states[author_id]
                    if time.time() - scl_state['time_of_search'] <= scl.SEARCH_TIMEOUT:
                        scl.handle_scl_command(f"{PREFIX}scl {safe_text.strip()}", message_object, thread_id, thread_type, author_id, self)
                        return
                    else:
                        del self.scl_user_states[author_id]
                        self.replyMessage(Message(text=f"{author_display_name}, kết quả tìm kiếm SoundCloud đã hết hạn ({scl.SEARCH_TIMEOUT}s), vui lòng tìm lại."), message_object, thread_id, thread_type, ttl=60000)
                        return

            ytb_selection_pattern = re.compile(r'^\d+(\s+(audio|mp3|low|360|360p|high|1080|1080p|max))?$', re.IGNORECASE)
            if ytb_selection_pattern.match(safe_text.strip()):
                if author_id in self.ytb_user_states:
                    ytb_state = self.ytb_user_states[author_id]
                    if time.time() - ytb_state['time_of_search'] <= ytb.SEARCH_TIMEOUT:
                        fake_command = f"{PREFIX}ytb {safe_text.strip()}"
                        ytb.handle_ytb_command(fake_command, message_object, thread_id, thread_type, author_id, self)
                        return
                    else:
                        del self.ytb_user_states[author_id]
                        self.replyMessage(Message(text=f"{author_display_name}, kết quả tìm kiếm YouTube đã hết hạn ({ytb.SEARCH_TIMEOUT}s), vui lòng tìm lại."), message_object, thread_id, thread_type, ttl=60000)
                        return

            if self.undo_handler.is_undo_enabled(thread_id):
                if message_object.msgType != 'chat.undo':
                    self.undo_handler.LuuNoiDungThuHoi(message_object, safe_text)

            if self.antilink_handler.check_and_handle_link(message_object, thread_id, thread_type, author_id):
                return

            if self.antifile_handler.check_and_delete_file(message_object, thread_id, thread_type, author_id):
                return

            if self.antiphoto_handler.check_antiphoto(message_object, thread_id, thread_type, author_id):
                return

            if self.antivideo_handler.check_antivideo(message_object, thread_id, thread_type, author_id):
                return

            if self.antisticker_handler.check_and_delete_sticker(message_object, thread_id, thread_type, author_id):
                return

            if self.anticard_handler.check_and_delete_card(message_object, thread_id, thread_type, author_id):
                return
            
            if self.antibot_handler.check_and_handle_message(message_object, thread_id, thread_type, author_id):
                return

            if self.is_user_muted(thread_id, author_id):
                if not self.is_allowed_author(author_id):
                    self.check_spam(author_id, message_object, thread_id, thread_type)
                self.deleteGroupMsg(message_object.msgId, author_id, message_object.cliMsgId, thread_id)
                return

            self.afk_handler.check_afk_return(author_id, thread_id, thread_type, message_object)

            self.afk_handler.check_afk_mention(message_object, thread_id, thread_type)

            self.antiall_handler.check_and_ban_if_all_hidden(message_object, thread_id, author_id)

            if author_id in self.locked_users:
                return

            if message_object.msgType == 'chat.sticker':
                allowed_groups = self.load_allowed_groups()
                if thread_type == ThreadType.GROUP and thread_id in allowed_groups:
                    sticker_id = message_object.content.id
                    sticker_catId = message_object.content.catId
                    logger.info(f"Sticker ID: {sticker_id}, Sticker CatId: {sticker_catId}")
                    sticker_info = {"id": sticker_id, "catId": sticker_catId}
                    if sticker_info not in self.sticker_data:
                        self.sticker_data.append(sticker_info)
                        self.save_sticker_data()

            command_handlers = {
                f"{PREFIX}antisp": self.antispam_handler.handle_antispam_command,
                f"{PREFIX}cam": self.loctk_handler.handle_loctk_command,
                f"{PREFIX}bot": self.bot_status_handler.handle_bot_command,
                f"{PREFIX}antiundo": self.undo_handler.handle_undo_command,
                f"{PREFIX}lbot": self.lockbot_handler.handle_lockbot_command,
                f"{PREFIX}unlbot": self.lockbot_handler.handle_unlockbot_command,
                f"{PREFIX}listlb": self.lockbot_handler.handle_listlockbot_command,
                f"{PREFIX}antifile": self.antifile_handler.handle_antifile_command,
                f"{PREFIX}antivideo": self.antivideo_handler.handle_antivideo_command,
                f"{PREFIX}antilink": self.antilink_handler.handle_antilink_command,
                f"{PREFIX}autotv": self.handle_auto_approve_command,
                f"{PREFIX}whitelist": self.whitelist_handler.handle_whitelist_command,
                f"{PREFIX}bcmd": self.bcmd_handler.handle_bcmd_command,
                f"{PREFIX}unbcmd": self.bcmd_handler.handle_unbcmd_command,
                f"{PREFIX}listbcmd": self.bcmd_handler.handle_listbcmd_command,
                f"{PREFIX}cmd": self.cmd_handler.handle_menu_command,
                f"{PREFIX}afk": self.afk_handler.handle_afk_command,
                f"{PREFIX}autojoin": self.autojoin_handler.handle_autojoin_command,
                f"{PREFIX}antiall": self.antiall_handler.handle_antiall_command,
                f"{PREFIX}antistk": self.antisticker_handler.handle_antistk_command,
                f"{PREFIX}antiphoto": self.antiphoto_handler.handle_antiphoto_command,
                f"{PREFIX}antiricon": self.antiricon_handler.handle_antiricon_command,
                f"{PREFIX}luuvc": self.msvc_handler.handle_luuvc_command,
                f"{PREFIX}svc": self.msvc_handler.handle_svc_command,
                f"{PREFIX}listvoice": self.msvc_handler.handle_listvoice_command,
                f"{PREFIX}delvc": self.msvc_handler.handle_delvc_command,
                f"{PREFIX}anticard": self.anticard_handler.handle_anticard_command,                
                f"{PREFIX}antibot": self.antibot_handler.handle_antibot_command,                
            } 

            for prefix_cmd, handler in command_handlers.items():
                if safe_text.lower().startswith(prefix_cmd):
                    handler(safe_text, message_object, thread_id, thread_type, author_id)
                    return

            if safe_text.isdigit() and thread_id in self.search_results and author_id in self.search_results[thread_id]:
                self.handle_download_command(safe_text, message_object, thread_id, thread_type, author_id)
                return

            self.command_handler.handle_command(safe_text, author_id, message_object, thread_id, thread_type)
            self.handle_auto_sticker(thread_id, thread_type, message_object)
            self.autojoin_handler.check_and_join_group(safe_text, message_object, thread_id, thread_type, author_id)
            if message and thread_type == ThreadType.USER:
                if author_id == self.uid:
                    return
                now = time.time()
                if author_id in self.temp_thread_storage:
                    last_message_time = self.temp_thread_storage[author_id]
                    if now - last_message_time < 3600000:
                        return
                self.temp_thread_storage[author_id] = now
                admin_name = get_user_name_by_id(client, ADMIN)
                msg = f"Chào {author_display_name}, {admin_name} đang bận chút nên mình là Trợ lý ảo của {admin_name} trả lời thay đó. {admin_name} sẽ nhắn lại sớm nhất có thể nha! 😀\n\n"
                self.replyMessage(Message(text=msg), message_object, thread_id, thread_type)

        except Exception as e:
            logger.error(f"Lỗi trong onMessage: {e}")

        if thread_type == ThreadType.GROUP:
            self.check_banned_words(safe_text, message_object, thread_id, thread_type, author_id)
            self.check_spam(author_id, message_object, thread_id, thread_type)

    def load_locked_users(self):
        try:
            with open(self.locked_users_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_locked_users(self):
        with open(self.locked_users_file, 'w') as f:
            json.dump(self.locked_users, f, indent=4)

    def handle_undo_command(self, message, message_object, thread_id, thread_type, author_id):
        self.undo_handler.handle_undo_command(message, message_object, thread_id, thread_type, author_id)

    def should_kick_user(self, user_id, thread_id):
        if thread_id in self.banned_word_violations and user_id in self.banned_word_violations[thread_id]:
            return self.banned_word_violations[thread_id][user_id] >= 5
        return False

    def handle_loctk_command(self, message, message_object, thread_id, thread_type, author_id):
        if self.loctk_handler:
            self.loctk_handler.handle_loctk_command(message, message_object, thread_id, thread_type, author_id)

    def handle_antispam_command(self, message, message_object, thread_id, thread_type, author_id):
        if self.antispam_handler:
            self.antispam_handler.handle_antispam_command(message, message_object, thread_id, thread_type, author_id)

    def is_admin(self, user_id, thread_id):
        return self.is_allowed_author(user_id) or self.is_group_admin(thread_id, user_id)

    def get_current_time(self):
        return time.time()

    def handle_new_message(self, mid, author_id, message, message_object, thread_id, thread_type):
        main_executor.submit(self._process_message_async, mid, author_id, message, message_object, thread_id, thread_type)

    def cleanup_expired_search_results(self):
        while True:
            time.sleep(60)
            now = self.get_current_time()
            for thread_id in list(self.search_result_messages):
                for author_id in list(self.search_result_messages[thread_id]):
                    search_result_info = self.search_result_messages[thread_id][author_id]
                    elapsed_time = now - search_result_info['time']
                    if elapsed_time > self.search_result_ttl:
                        self.cleanup_search_result(thread_id, author_id)


if __name__ == "__main__":
    banner()
    try:
        if os.path.exists("session.json"):
            os.remove("session.json")
            logger.warning("Đã xóa file session.json cũ để bắt đầu phiên mới.")
        client = Client(API_KEY, SECRET_KEY, IMEI, SESSION_COOKIES)
        from modules.adv import start_adv_scheduler
        start_adv_scheduler(client)
        from modules.rs import send_reset_success_message
        send_reset_success_message(client)
        from modules.treoanh import auto_restart_war
        auto_restart_war(client)
        from modules.nhaytag import auto_restart_nhaytag
        auto_restart_nhaytag(client)
        from modules.sticker_lag import auto_restart_stklag
        auto_restart_stklag(client)
        from modules.mute import start_expiry_checker
        start_expiry_checker(client)
        client.listen(run_forever=True, delay=0, thread=True)
    except Exception as e:
        logger.error(f"Lỗi rồi, Không thể login...: {e}")
        python = sys.executable
        os.execl(python, python, *sys.argv)
        time.sleep(10)