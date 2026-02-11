import json
import os


des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Chống thu hồi tin nhắn",
    'power': "Admin"
}
# Đường dẫn file lưu tin nhắn chống thu hồi
path = "database/dataundo.json"

def onBotRestart():
    try:
        # Nếu file chưa tồn tại thì tạo file mới rỗng
        if not os.path.exists(path):
            print("[AntiUndo] File dataundo.json không tồn tại, tạo mới.")
            with open(path, "w") as f:
                json.dump([], f)
            return

        # Đọc dữ liệu undo
        with open(path, "r") as f:
            dataUndo = json.load(f)

        # Kiểm tra có tin nhắn không
        if len(dataUndo) > 0:
            msg = dataUndo[0]
            print(f"[AntiUndo] Gửi lại tin nhắn xác nhận: {msg}")
            # Nếu bot có hàm gửi tin nhắn, có thể gọi tại đây
            # sendMessage(msg)
        else:
            print("[AntiUndo] Không có tin nhắn để gửi sau khi restart.")

    except Exception as e:
        print(f"[AntiUndo] Lỗi khi gửi tin nhắn xác nhận sau khi restart: {e}")
