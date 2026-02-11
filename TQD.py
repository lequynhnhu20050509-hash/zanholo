import os
import json
import importlib
import sys
import time
import threading
import re
import random
import difflib
from concurrent.futures import ThreadPoolExecutor
from zlapi.models import Message, MultiMsgStyle, MessageStyle
from logging_utils import Logging
from colorama import Fore

sys.path.extend([
    os.path.dirname(os.path.abspath(__file__)),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules/auto'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules/noprefix')
])
logger = Logging()

CACHE_DIR = 'modules/cache'
SETTINGS_FILE = 'seting.json'
DUYETBOX_FILE = os.path.join(CACHE_DIR, 'duyetboxdata.json')
DISABLED_THREADS_FILE = os.path.join(CACHE_DIR, 'disabled_threads.json')
COOLDOWN_FILE = os.path.join(CACHE_DIR, 'cooldown_settings.json')
STW_CMDS_FILE = os.path.join(CACHE_DIR, 'list_cmd_stw.json')
MODULES_DIR = 'modules'
NOPREFIX_MODULES_DIR = 'modules/noprefix'
AUTO_MODULES_DIR = 'modules/auto'


def load_json(file_path, default=None):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {} if file_path.endswith(".json") else []


def save_json(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_duyetbox_data():
    return load_json(DUYETBOX_FILE, [])


def load_disabled_threads():
    return load_json(DISABLED_THREADS_FILE, [])


def save_disabled_threads(disabled_threads):
    save_json(DISABLED_THREADS_FILE, disabled_threads)


def load_stw_commands():
    return load_json(STW_CMDS_FILE, {}).get('commands', [])


def save_stw_commands(commands):
    save_json(STW_CMDS_FILE, {'commands': commands})


def update_any_string(old_string, new_string):
    replaced_count = 0
    files_changed = 0
    pattern = re.compile(re.escape(old_string), re.IGNORECASE)
    for root, dirs, files in os.walk('.'):
        for filename in files:
            if filename.endswith('.py'):
                file_path = os.path.join(root, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    new_code, n = pattern.subn(new_string, code)
                    if n > 0:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_code)
                        replaced_count += n
                        files_changed += 1
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý {file_path}: {e}")
    return replaced_count, files_changed


class ThreadSafeDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = threading.RLock()

    def __getitem__(self, key):
        with self.lock:
            return super().__getitem__(key)

    def __setitem__(self, key, value):
        with self.lock:
            super().__setitem__(key, value)

    def get(self, key, default=None):
        with self.lock:
            return super().get(key, default)

    def update(self, *args, **kwargs):
        with self.lock:
            super().update(*args, **kwargs)

    def pop(self, key, default=None):
        with self.lock:
            return super().pop(key, default)

    def __contains__(self, item):
        with self.lock:
            return super().__contains__(item)

    def keys(self):
        with self.lock:
            return list(super().keys())

    def values(self):
        with self.lock:
            return list(super().values())

    def items(self):
        with self.lock:
            return list(super().items())


executor = ThreadPoolExecutor(max_workers=10)


class CommandHandler:
    def __init__(self, client):
        self.client = client
        self.TQD = ThreadSafeDict(
            self._load_modules(
                MODULES_DIR, 'TQD', [
                    'version', 'credits', 'description', 'power']))
        self.noprefix_tqd = ThreadSafeDict(
            self._load_modules(
                NOPREFIX_MODULES_DIR, 'TQD', [
                    'version', 'credits', 'description']))
        self.auto_tqd = ThreadSafeDict(self._load_auto_modules())
        self.disabled_threads = ThreadSafeDict(
            {t: True for t in load_disabled_threads()})

        self._admin_id = [self.client.ADMIN] + self.client.ADM
        self.current_prefix = self.client.settings.get("prefix") or ""

        self.cooldown_settings = load_json(COOLDOWN_FILE, {})
        self.stw_commands = load_stw_commands()
        self.last_used = ThreadSafeDict()
        self.cooldown_lock = threading.Lock()

        logger.prefixcmd(f"🛡 Prefix hiện tại của bot là '{self.current_prefix}'"
                         if self.current_prefix else "❌️ Prefix hiện tại của bot là 'no prefix'")
        self._log_commands("start with", self.stw_commands)
        self.prefix_handlers = self._create_prefix_handlers()

        # GIỮ NGUYÊN ICON ĐẸP
        self.reaction_icons = {
            'normal': ['/-ok'],
            'admin': ['🔧', '⚙️', '🛠️'],
            'error': ['⚠️', '🚫', '😓'],
            'cooldown': ['⌛', '⏰', '🕒'],
            'stw': ['✨', '💫', '💡']
        }

    def _create_prefix_handlers(self):
        return sorted([(self.current_prefix + command, handler)
                       for command, handler in self.TQD.items() if self.current_prefix],
                      key=lambda item: len(item[0]), reverse=True)

    def _update_prefix(self):
        new_prefix = self.client.settings.get("prefix") or ""
        if new_prefix != self.current_prefix:
            self.current_prefix = new_prefix
            logger.prefixcmd(f"🕹 Prefix đã được cập nhật thành '{self.current_prefix}'"
                             if self.current_prefix else "🎑 Prefix đã được cập nhật thành 'no prefix'")
            self.prefix_handlers = self._create_prefix_handlers()

    def _log_commands(self, command_type, commands):
        if isinstance(commands, dict):
            if commands:
                logger.success(f"Đã load thành công các {command_type}")
            else:
                logger.success(f"Không có {command_type} nào.")
        elif isinstance(commands, list):
            if commands:
                logger.success(f"Đã load thành công các lệnh {command_type}")
            else:
                logger.success(f"Không có lệnh {command_type} nào.")

    def get_username(self, user_id):
        try:
            info = self.client.fetchUserInfo(user_id)
            if info and hasattr(info, "changed_profiles"):
                return info.changed_profiles.get(str(user_id), {}).get('zaloName', 'Không xác định')
            return "Không xác định"
        except Exception:
            return "Không xác định"

    def send_message_async(self, error_message, thread_id, thread_type, author_id):
        executor.submit(self._send_message_blocking, error_message, thread_id, thread_type, author_id)

    def _send_message_blocking(self, error_message, thread_id, thread_type, author_id):
        name = self.get_username(author_id)
        msg = f"{name}\n➜{error_message}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(name), style="bold", auto_format=False)
        ])
        self.client.send(Message(text=msg, style=styles), thread_id, thread_type, ttl=12000)

    def reply_message_async(self, error_message, message_object, thread_id, thread_type, author_id):
        executor.submit(self._reply_message_blocking, error_message, message_object, thread_id, thread_type, author_id)

    def _reply_message_blocking(self, error_message, message_object, thread_id, thread_type, author_id):
        name = self.get_username(author_id)
        msg = f"{name}\n➜{error_message}"
        styles = MultiMsgStyle([
            MessageStyle(offset=0, length=len(name), style="color", color="#db342e", auto_format=False),
            MessageStyle(offset=0, length=len(name), style="bold", auto_format=False)
        ])
        self.client.replyMessage(Message(text=msg, style=styles), message_object, thread_id=thread_id, thread_type=thread_type, ttl=12000)

    def _send_multiple_reactions(self, message_object, command_type, thread_id, thread_type):
        executor.submit(self._send_multiple_reactions_blocking, message_object, command_type, thread_id, thread_type)

    def _send_multiple_reactions_blocking(self, message_object, command_type, thread_id, thread_type):
        icons = random.sample(
            self.reaction_icons.get(command_type, ['✅']),
            min(3, len(self.reaction_icons.get(command_type, ['✅'])))
        )
        for icon in icons:
            try:
                self.client.sendReaction(
                    messageObject=message_object,
                    reactionIcon=icon,
                    thread_id=thread_id,
                    thread_type=thread_type
                )
                time.sleep(0.07)
            except Exception as e:
                logger.error(f"Lỗi khi gửi reaction '{icon}': {e}")

    def _load_modules(self, module_path, attribute_name, required_keys):
        modules, success_modules, failed_modules = {}, [], []
        for filename in os.listdir(module_path):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(f'{module_path.replace("/", ".")}.{module_name}')
                    if (hasattr(module, attribute_name) and hasattr(module, 'des') and
                            all(key in module.des for key in required_keys)):
                        modules.update(getattr(module, attribute_name)())
                        success_modules.append(module_name)
                    else:
                        failed_modules.append(module_name)
                except Exception as e:
                    logger.error(f"Không thể load được lệnh '{module_name}' trong {module_path}: {e}")
                    failed_modules.append(module_name)
        if success_modules:
            logger.success(f"Đã load thành công {len(success_modules)} lệnh trong {module_path}")
        if failed_modules:
            logger.warning(f"Không thể load được {len(failed_modules)} lệnh trong {module_path}: {', '.join(failed_modules)}")
        return modules

    def _load_auto_modules(self):
        auto_modules, success_auto, failed_auto = {}, [], []
        for filename in os.listdir(AUTO_MODULES_DIR):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(f'modules.auto.{module_name}')
                    if hasattr(module, 'start_auto'):
                        auto_modules[module_name] = module
                        success_auto.append(module_name)
                    else:
                        failed_auto.append(module_name)
                except Exception as e:
                    logger.error(f"Không thể load được lệnh auto '{module_name}': {e}")
                    failed_auto.append(module_name)
        if success_auto:
            logger.success(f"Đã load thành công {len(success_auto)} lệnh auto")
            for module in success_auto:
                executor.submit(auto_modules[module].start_auto, self.client)
        if failed_auto:
            logger.warning(f"Không thể load {len(failed_auto)} lệnh auto: {', '.join(failed_auto)}")
        return auto_modules

    def predict_command(self, wrong_command):
        possible_commands = list(self.TQD.keys())
        matches = difflib.get_close_matches(wrong_command, possible_commands, n=1, cutoff=0.6)
        return matches[0] if matches else None

    def _handle_cooldown(self, message, message_object, thread_id, thread_type, author_id):
        if author_id not in self._admin_id:
            self.reply_message_async("Bạn không có quyền quản lý cooldown.", message_object, thread_id, thread_type, author_id)
            return
        parts = message.split(self.current_prefix + 'cooldown', 1)
        if len(parts) < 2:
            self.reply_message_async(f"Vui lòng sử dụng: {self.current_prefix}cooldown [set|remove|list] <command> <time>\nVí dụ: {self.current_prefix}cooldown set menu 3s",
                                     message_object, thread_id, thread_type, author_id)
            return
        command_part = parts[1].strip().lower()
        args = command_part.split()
        if not args:
            self.reply_message_async(f"Vui lòng sử dụng: {self.current_prefix}cooldown [set|remove|list] <command> <time>\nVí dụ: {self.current_prefix}cooldown set menu 3s",
                                     message_object, thread_id, thread_type, author_id)
            return
        action = args[0]
        if action == 'set':
            if len(args) < 3:
                self.reply_message_async(f"Vui lòng sử dụng: {self.current_prefix}cooldown set <command> <time>\nVí dụ: {self.current_prefix}cooldown set menu 3s",
                                         message_object, thread_id, thread_type, author_id)
                return
            command, time_str = args[1], args[2]
            is_valid_command = command in self.TQD or command in self.stw_commands
            if not is_valid_command:
                self.reply_message_async(f"Lệnh {command} không tồn tại.", message_object, thread_id, thread_type, author_id)
                return
            try:
                if time_str.endswith('s'):
                    cooldown_time = float(time_str[:-1])
                elif time_str.endswith('m'):
                    cooldown_time = float(time_str[:-1]) * 60
                else:
                    cooldown_time = float(time_str)
            except ValueError:
                self.reply_message_async("Thời gian không hợp lệ. Vui lòng sử dụng định dạng số giây (3s) hoặc phút (1m).",
                                         message_object, thread_id, thread_type, author_id)
                return
            self.cooldown_settings[command] = cooldown_time
            save_json(COOLDOWN_FILE, self.cooldown_settings)
            self.reply_message_async(f"Đã đặt cooldown {cooldown_time} giây cho lệnh {command}.",
                                     message_object, thread_id, thread_type, author_id)
        elif action == 'remove':
            if len(args) < 2:
                self.reply_message_async(f"Vui lòng sử dụng: {self.current_prefix}cooldown remove <command>",
                                         message_object, thread_id, thread_type, author_id)
                return
            command = args[1]
            if command not in self.cooldown_settings:
                self.reply_message_async(f"Lệnh {command} không có cooldown.", message_object, thread_id, thread_type, author_id)
                return
            del self.cooldown_settings[command]
            save_json(COOLDOWN_FILE, self.cooldown_settings)
            self.reply_message_async(f"Đã xóa cooldown của lệnh {command}.", message_object, thread_id, thread_type, author_id)
        elif action == 'list':
            if self.cooldown_settings:
                response = "Danh sách lệnh có cooldown:\n"
                for command, cooldown_time in self.cooldown_settings.items():
                    response += f"- {command}: {cooldown_time} giây\n"
                self.reply_message_async(response.strip(), message_object, thread_id, thread_type, author_id)
            else:
                self.reply_message_async("Không có lệnh nào được đặt cooldown.", message_object, thread_id, thread_type, author_id)
        else:
            self.reply_message_async(f"Vui lòng sử dụng: {self.current_prefix}cooldown [set|remove|list] <command> <time>",
                                     message_object, thread_id, thread_type, author_id)

    def _handle_credit(self, message, message_object, thread_id, thread_type, author_id):
        if author_id not in self._admin_id:
            self.reply_message_async("Bạn không có quyền sử dụng lệnh credit.", message_object, thread_id, thread_type, author_id)
            return
        parts = message.split(self.current_prefix + 'credit', 1)
        if len(parts) < 2 or not parts[1].strip():
            self.reply_message_async(f"Vui lòng sử dụng: {self.current_prefix}credit <chuỗi cũ> - <chuỗi mới>",
                                     message_object, thread_id, thread_type, author_id)
            return
        args = parts[1].strip().split('-', 1)
        if len(args) < 2:
            self.reply_message_async(f"Vui lòng sử dụng: {self.current_prefix}credit <chuỗi cũ> - <chuỗi mới>",
                                     message_object, thread_id, thread_type, author_id)
            return
        old_string = args[0].strip()
        new_string = args[1].strip()
        if not old_string or not new_string:
            self.reply_message_async(f"Vui lòng sử dụng: {self.current_prefix}credit <chuỗi cũ> - <chuỗi mới>",
                                     message_object, thread_id, thread_type, author_id)
            return
        replaced_count, files_changed = update_any_string(old_string, new_string)
        if files_changed > 0:
            self.reply_message_async(f"Đã thay thế tất cả '{old_string}' thành '{new_string}' trong {files_changed} file, tổng {replaced_count} lần thay thế.",
                                     message_object, thread_id, thread_type, author_id)
        else:
            self.reply_message_async(f"Không tìm thấy chuỗi '{old_string}' trong mã nguồn.",
                                     message_object, thread_id, thread_type, author_id)

    def _handle_stw(self, message, message_object, thread_id, thread_type, author_id):
        if author_id not in self._admin_id:
            self.reply_message_async("Bạn không có quyền quản lý lệnh startwith (stw).", message_object, thread_id, thread_type, author_id)
            return
        parts = message.split(self.current_prefix + 'stw', 1)
        if len(parts) < 2:
            self.reply_message_async(f"Vui lòng sử dụng: {self.current_prefix}stw [add|del|list] [command]",
                                     message_object, thread_id, thread_type, author_id)
            return
        command_part = parts[1].strip().lower()
        action, *target_parts = command_part.split(' ', 1)
        target = target_parts[0].strip() if target_parts else None

        if action == 'add':
            if not target:
                self.reply_message_async("Vui lòng cung cấp tên lệnh để thêm vào danh sách stw.", message_object, thread_id, thread_type, author_id)
                return
            if target not in self.TQD:
                self.reply_message_async(f"Lệnh '{target}' không tồn tại trong danh sách lệnh chính.", message_object, thread_id, thread_type, author_id)
                return
            if target not in self.stw_commands:
                self.stw_commands.append(target)
                save_stw_commands(self.stw_commands)
                self._log_commands("start with", self.stw_commands)
                self.reply_message_async(f"Đã thêm lệnh '{target}' vào danh sách start with.", message_object, thread_id, thread_type, author_id)
            else:
                self.reply_message_async(f"Lệnh '{target}' đã có trong danh sách start with.", message_object, thread_id, thread_type, author_id)
        elif action == 'del':
            if not target:
                self.reply_message_async("Vui lòng cung cấp tên lệnh để xóa khỏi danh sách stw.", message_object, thread_id, thread_type, author_id)
                return
            if target in self.stw_commands:
                self.stw_commands.remove(target)
                save_stw_commands(self.stw_commands)
                self._log_commands("start with", self.stw_commands)
                self.reply_message_async(f"Đã xóa lệnh '{target}' khỏi danh sách start with.", message_object, thread_id, thread_type, author_id)
            else:
                self.reply_message_async(f"Không tìm thấy lệnh '{target}' trong danh sách start with.", message_object, thread_id, thread_type, author_id)
        elif action == 'list':
            if self.stw_commands:
                self.reply_message_async(f"Các lệnh start with: {', '.join(self.stw_commands)}",
                                         message_object, thread_id, thread_type, author_id)
            else:
                self.reply_message_async("Không có lệnh start with nào.", message_object, thread_id, thread_type, author_id)
        else:
            self.reply_message_async(f"Vui lòng sử dụng: {self.current_prefix}stw [add|del|list] [command]",
                                     message_object, thread_id, thread_type, author_id)

    def _check_cooldown(self, command, author_id, thread_id):
        if command not in self.cooldown_settings:
            return True
        cooldown_time = self.cooldown_settings[command]
        key = f"{command}_{author_id}_{thread_id}"
        with self.cooldown_lock:
            current_time = time.time()
            last_used_time = self.last_used.get(key, 0)
            if current_time - last_used_time < cooldown_time:
                remaining = cooldown_time - (current_time - last_used_time)
                return f"Vui lòng chờ {remaining:.1f} giây để sử dụng lại lệnh này."
            self.last_used[key] = current_time
            return True

    def _get_content_message(self, message_object):
        if message_object.msgType == 'chat.sticker':
            return ""
        content = message_object.content
        if isinstance(content, dict) and 'title' in content:
            return content['title']
        elif isinstance(content, str):
            return content
        elif isinstance(content, dict) and 'href' in content:
            return content['href']
        else:
            return ""

    def _execute_command(self, command_handler, message_text, message_object, thread_id, thread_type, author_id, command_name):
        try:
            cooldown_check = self._check_cooldown(command_name, author_id, thread_id)
            if isinstance(cooldown_check, str):
                self._send_multiple_reactions(message_object, 'cooldown', thread_id, thread_type)
                self.reply_message_async(cooldown_check, message_object, thread_id, thread_type, author_id)
                return
            command_handler(message_text, message_object, thread_id, thread_type, author_id, self.client)
        except Exception as e:
            self._send_multiple_reactions(message_object, 'error', thread_id, thread_type)
            self.reply_message_async(f"Lỗi khi thực hiện lệnh: {e}", message_object, thread_id, thread_type, author_id)

    # HANDLE_COMMAND HOÀN CHỈNH – CHỈ DÙNG TTL
    def handle_command(self, message, author_id, message_object, thread_id, thread_type):
        # BỎ QUA TIN NHẮN DO BOT GỬI (CÓ TTL)
        if getattr(message_object, 'ttl', 0) is not 0:
            return

        self._update_prefix()
        message_text = self._get_content_message(message_object)
        if not message_text:
            return

        duyetbox_data = self.client.duyetbox_data
        admins_list = [self.client.ADMIN] + self.client.ADM
        is_admin = (author_id in admins_list)
        is_duyetbox_thread = (thread_id in duyetbox_data)

        # 1. Noprefix
        noprefix_handler = self.noprefix_tqd.get(message_text.lower())
        if noprefix_handler:
            self._send_multiple_reactions(message_object, 'normal', thread_id, thread_type)
            executor.submit(self._execute_command, noprefix_handler, message_text, message_object, thread_id, thread_type, author_id, message_text.lower())
            return

        # 2. Kiểm tra quyền
        if not is_duyetbox_thread and not is_admin:
            if message_text.startswith(self.current_prefix):
                return
            admin_cmd_prefixes = [self.current_prefix + cmd for cmd in ['cooldown', 'credit', 'stw']]
            if any(message_text.startswith(p) for p in admin_cmd_prefixes):
                return
            return

        # 3. Lệnh admin
        special_admin_commands = {
            self.current_prefix + 'cooldown': self._handle_cooldown,
            self.current_prefix + 'credit': self._handle_credit,
            self.current_prefix + 'stw': self._handle_stw
        }
        for cmd_prefix_full, handler_func in special_admin_commands.items():
            if message_text.startswith(cmd_prefix_full) and re.match(rf"^{re.escape(cmd_prefix_full)}(\s|$)", message_text, re.IGNORECASE):
                self._send_multiple_reactions(message_object, 'admin', thread_id, thread_type)
                executor.submit(handler_func, message_text, message_object, thread_id, thread_type, author_id)
                return

        # 4. Lệnh TK: PREFIX Ở BẤT KỲ ĐÂU
        if self.current_prefix and self.TQD:
            message_lower = message_text.lower()
            sorted_tk_cmds = sorted(self.TQD.keys(), key=len, reverse=True)
            for cmd in sorted_tk_cmds:
                cmd_lower = cmd.lower()
                pattern = rf"(?:^|\s){re.escape(self.current_prefix)}\s*{re.escape(cmd_lower)}(?=\s|$|[^\w])"
                match = re.search(pattern, message_lower)
                if match:
                    if self.client.bcmd_handler.is_command_blocked(cmd, author_id, thread_id):
                        self._send_multiple_reactions(message_object, 'error', thread_id, thread_type)
                        self.reply_message_async("Bạn đã bị cấm sử dụng lệnh này.", message_object, thread_id, thread_type, author_id)
                        return
                    handler = self.TQD.get(cmd)
                    if handler:
                        self._send_multiple_reactions(message_object, 'normal', thread_id, thread_type)
                        executor.submit(self._execute_command, handler, message_text, message_object, thread_id, thread_type, author_id, cmd)
                        return

        # 5. Start-with
        if self.stw_commands:
            sorted_stw_cmds = sorted([cmd for cmd in self.stw_commands if cmd in self.TQD], key=len, reverse=True)
            if sorted_stw_cmds:
                stw_pattern = '|'.join(re.escape(cmd.lower()) for cmd in sorted_stw_cmds)
                prefix_escaped = re.escape(self.current_prefix)
                stw_regex = re.compile(rf"{prefix_escaped}\s*({stw_pattern})(?:\s|$)", re.IGNORECASE)
                match = stw_regex.search(message_text)
                if match:
                    cmd = match.group(1).lower()
                    if self.client.bcmd_handler.is_command_blocked(cmd, author_id, thread_id):
                        self._send_multiple_reactions(message_object, 'error', thread_id, thread_type)
                        self.reply_message_async("Bạn đã bị cấm sử dụng lệnh này.", message_object, thread_id, thread_type, author_id)
                        return
                    handler = self.TQD.get(cmd)
                    if handler:
                        self._send_multiple_reactions(message_object, 'stw', thread_id, thread_type)
                        executor.submit(self._execute_command, handler, message_text, message_object, thread_id, thread_type, author_id, cmd)
                        return

        # 6. Lệnh sai
        if message_text.startswith(self.current_prefix):
            command_part = message_text[len(self.current_prefix):].strip()
            wrong_cmd = command_part.split()[0] if command_part else ""
            predicted = self.predict_command(wrong_cmd)
            if predicted:
                help_msg = f"Lệnh `{wrong_cmd}` không tồn tại.\nCó thể bạn muốn dùng `{predicted}`?\nVí dụ: `{self.current_prefix}{predicted}`"
            else:
                help_msg = f"Bạn đã dùng sai lệnh!\nChat ví dụ:\n`{self.current_prefix}menu`\nĐể xem danh sách lệnh."
            self._send_multiple_reactions(message_object, 'error', thread_id, thread_type)
            self.reply_message_async(help_msg, message_object, thread_id, thread_type, author_id)