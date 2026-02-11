# modules/check.py

from zlapi.models import *
import platform
import psutil
import time
import datetime
import os
import sys

des = {
    'version': "2.4.0",
    'credits': "Latte",
    'description': "xem thông tin ",
    'power': "Thành viên"
}

bot_name = "Latte"
cre = "Dương"
start_time = time.time()


def get_uptime():
    uptime_sec = int(time.time() - start_time)
    hours = uptime_sec // 3600
    minutes = (uptime_sec % 3600) // 60
    seconds = uptime_sec % 60
    return f"{hours}h {minutes}m {seconds}s"


def get_system_info():
    return f"{platform.system()} {platform.release()} ({platform.version()})"


def get_cpu_info():
    # Lấy tên CPU không cần root
    cpu_name = platform.processor() or os.popen("uname -m").read().strip() or "Unknown CPU"
    cpu_cores = psutil.cpu_count(logical=False) or 1
    cpu_threads = psutil.cpu_count(logical=True) or 1
    # CPU usage có thể lỗi trên Termux không root
    try:
        cpu_usage = psutil.cpu_percent(interval=0.1)
        cpu_usage_str = f" | Usage: {cpu_usage}%"
    except PermissionError:
        cpu_usage_str = " | Usage: N/A"
    return f"{cpu_name}\n📊 Cores: {cpu_cores} | Threads: {cpu_threads}{cpu_usage_str}"


def get_ram_info():
    mem = psutil.virtual_memory()
    return {"total": round(mem.total / 1024**3, 2),
            "used": round(mem.used / 1024**3, 2),
            "available": round(mem.available / 1024**3, 2),
            "percent": mem.percent}


def get_swap_info():
    swap = psutil.swap_memory()
    return {"total": round(swap.total / 1024**3, 2),
            "used": round(swap.used / 1024**3, 2),
            "free": round(swap.free / 1024**3, 2)}


def get_disk_info():
    disk_path = '/data' if 'TERMUX_VERSION' in os.environ else '/'
    disk = psutil.disk_usage(disk_path)
    return f"💿 {disk_path}: {round(disk.used / 1024**3, 2)}/{round(disk.total / 1024**3, 2)} GB ({disk.percent}%) - Free: {round(disk.free / 1024**3, 2)} GB"


def get_process_info():
    process = psutil.Process(os.getpid())
    try:
        cpu = process.cpu_percent(interval=0.1)
    except PermissionError:
        cpu = 0.0
    return f"PID: {process.pid} | RAM: {round(process.memory_info().rss / 1024**2, 2)}MB | CPU: {cpu}%"


def get_python_info():
    return f"CPython {platform.python_version()}"


def get_app_info():
    if 'TERMUX_VERSION' in os.environ:
        return "Termux"
    return "Windows Terminal/CMD/PowerShell"


def get_network_speed(interval=1):
    """
    Lấy tốc độ download và upload trong khoảng interval giây.
    Trả về dict: {'download', 'upload', 'status'}
    """
    try:
        net1 = psutil.net_io_counters()
        time.sleep(interval)
        net2 = psutil.net_io_counters()

        download_speed = (net2.bytes_recv - net1.bytes_recv) / interval / 1024 / 1024  # MB/s
        upload_speed = (net2.bytes_sent - net1.bytes_sent) / interval / 1024 / 1024      # MB/s

        total_speed = download_speed + upload_speed
        if total_speed < 1:
            status = "Yếu ⚠️"
        elif total_speed <= 5:
            status = "Trung bình ⚡"
        else:
            status = "Mạnh 🚀"

        return {
            'download': round(download_speed, 2),
            'upload': round(upload_speed, 2),
            'status': status
        }
    except PermissionError:
        return {
            'download': 0.0,
            'upload': 0.0,
            'status': "Không có quyền ❌"
        }


def handle_check_command(message, message_object, thread_id, thread_type, author_id, client):
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %d/%m/%Y")
    time_str = now.strftime("%H:%M:%S")

    ram_info = get_ram_info()
    swap_info = get_swap_info()
    net = get_network_speed(interval=1)

    content = f"""[ THÔNG TIN BOT ]

⏰ Thời gian: {date_str} {time_str}
⏱️ Uptime: {get_uptime()}


🖥️ HỆ THỐNG: {get_system_info()}

💻 CPU: {get_cpu_info()}

💾 STORAGE: {get_disk_info()}

📊 RAM: {ram_info['used']}/{ram_info['total']} GB ({ram_info['percent']}%)

💫 SWAP: {swap_info['used']}/{swap_info['total']} GB

🌐 MẠNG: Download: {net['download']} MB/s | Upload: {net['upload']} MB/s | {net['status']}

🐍 Python: {get_python_info()} | Chạy trên: {get_app_info()}

🚀 Process: {get_process_info()}

👑 Admin: {bot_name}
🎨 Creator: {cre}"""

    client.replyMessage(Message(text=content), message_object, thread_id, thread_type,ttl=60000)


def TQD():
    return {
        'check': handle_check_command
    }
