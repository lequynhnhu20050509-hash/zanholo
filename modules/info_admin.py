from zlapi.models import *
from config import ADMIN  # DANH SÁCH UID ADMIN
des = {
    'version': "2.1.3",
    'credits': "Latte",
    'description': "Thông tin Admin",
    'power': "Admin"
}

success_styles = MultiMsgStyle([
    MessageStyle(offset=0, length=10000, style="color", color="#15a85f", auto_format=False),
    MessageStyle(offset=0, length=10000, style="font", size="8", auto_format=False),
    MessageStyle(offset=0, length=10000, style="bold", auto_format=False)
])
# ============================================================
# Hàm xử lý lệnh /ttadmin
def handle_ttadmin_command(message, message_object, thread_id, thread_type, author_id, client):
       
    if str(author_id) not in ADMIN:
        client.replyMessage(
            Message(text="🚫 Bạn không có quyền sử dụng lệnh này! Chỉ có admin Latte mới được sử dụng lệnh này"),
            message_object,
            thread_id,
            thread_type,
            ttl=30000
        )
        return

    # Thông tin Creator/Admin cố định
    admin_info = (
        "👑 Creator: Trần Kim Dương\n"
        "🎂 Birthday: 09/05/2009\n"
        "Chiều cao: 1m73\n"
        "Cân nặng: 70kg\n"
        "♋ Cung hoàng đạo: Kim Ngưu\n"
        "💻 Đam mê: Lập trình, Edit Video\n"
        "📱 Contact Zalo: 0522627505\n"
        "🌐 Github: https://www.github.com/DuongConan\n"
        "——————————————\n"
        "Nếu cần hỗ trợ, liên hệ trực tiếp Creator."
    )
    msg_intro = Message(
            text=admin_info,
            mention=Mention(author_id, length=0, offset=0),
            style=success_styles
        )
        
    client.replyMessage(
        msg_intro,
        message_object,
        thread_id,
        thread_type,
        ttl=60000*5
    )

# ============================================================
# Hàm trả về dict lệnh để tích hợp với bot chính
def TQD():
    return {'ttadmin': handle_ttadmin_command}
