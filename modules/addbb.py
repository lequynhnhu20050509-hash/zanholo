import json
import time
import concurrent.futures
from zlapi.models import Message, ZaloAPIException
from config import ADMIN


des = {
    'version': "6.0.0",
    'credits': "Latte",
    'description': "Lấy danh sách bạn bè và thêm vào nhóm",
    'power': "Admin",
}


# ==========================
#  HÀM LẤY DANH SÁCH BẠN BÈ
# ==========================
def fetchAllFriends(client):
    """Lấy toàn bộ bạn bè của bot, bao gồm UID và tên"""
    try:
        print("\n🚀 [fetchAllFriends] Hàm được gọi!\n")

        params = {
            "params": client._encode({
                "incInvalid": 0,
                "page": 1,
                "count": 20000,
                "avatar_size": 120,
                "actiontime": 0
            }),
            "zpw_ver": 641,
            "zpw_type": 30,
            "nretry": 0
        }

        response = client._get(
            "https://profile-wpa.chat.zalo.me/api/social/friend/getfriends",
            params=params
        )
        data = response.json()

        if data.get("error_code") != 0:
            raise ZaloAPIException(f"Lỗi #{data.get('error_code')}: {data.get('error_message')}")

        decoded = client._decode(data.get("data"))
        friends_raw = decoded.get("data", [])

        print(f"📋 Tổng số bạn bè lấy được: {len(friends_raw)}")

        if friends_raw:
            print("📦 Mẫu dữ liệu 1 bạn bè:")
            print(json.dumps(friends_raw[0], indent=2, ensure_ascii=False))

        friends = []
        for f in friends_raw:
            if not isinstance(f, dict):
                continue

            uid = (
                f.get("uid")
                or f.get("id")
                or f.get("oaid")
                or f.get("user_id")
                or f.get("userId")
                or f.get("zaloId")
                or (f.get("user", {}).get("id") if isinstance(f.get("user"), dict) else None)
                or (f.get("profile", {}).get("id") if isinstance(f.get("profile"), dict) else None)
            )

            name = (
                f.get("display_name")
                or f.get("zaloName")
                or f.get("name")
                or f.get("full_name")
                or (f.get("user", {}).get("displayName") if isinstance(f.get("user"), dict) else None)
                or (f.get("profile", {}).get("displayName") if isinstance(f.get("profile"), dict) else None)
                or "Không rõ tên"
            )

            if uid:
                friends.append({"uid": str(uid), "name": name})

        print(f"✅ Đã lọc được {len(friends)} bạn có UID hợp lệ\n")
        return friends

    except Exception as e:
        print("❌ Lỗi khi lấy danh sách bạn bè:", e)
        return []


# ================================
#  HÀM THÊM BẠN BÈ VÀO NHÓM (ĐA LUỒNG)
# ================================
def addUsersToGroup(client, group_id, uids, max_threads=5):
    """Thêm bạn bè vào nhóm bằng đa luồng"""
    results = {"thanh_cong": 0, "that_bai": 0}

    def add_one(uid):
        """Hàm chạy trong từng luồng"""
        try:
            client.addUsersToGroup(uid, group_id)
            print(f"✅ Thêm {uid} thành công.")
            return True
        except Exception as e:
            print(f"❌ Lỗi khi thêm {uid}: {e}")
            return False

    # Giới hạn số luồng (max 10 cho an toàn)
    max_threads = min(max_threads, 10)
    print(f"⚙️ Bắt đầu thêm {len(uids)} bạn bằng {max_threads} luồng...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        future_to_uid = {executor.submit(add_one, uid): uid for uid in uids}

        for future in concurrent.futures.as_completed(future_to_uid):
            success = future.result()
            if success:
                results["thanh_cong"] += 1
            else:
                results["that_bai"] += 1

    print(f"🏁 Hoàn tất: {results['thanh_cong']} thành công, {results['that_bai']} thất bại.")
    return results


# ================================
#  LỆNH CHÍNH: addbb
# ================================
def handle_addbb(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh addbb"""
    if author_id not in ADMIN:
        client.replyMessage(
            Message(text="🚫 Bạn không có quyền sử dụng lệnh này! Chỉ có admin Latte mới được sử dụng"),
            message_object, thread_id, thread_type, ttl=60000
        )
        return

    content = message.text.strip() if hasattr(message, "text") else str(message).strip()
    parts = content.split()

    if len(parts) < 2:
        client.replyMessage(
            Message(text="⚠️ Dùng: addbb all hoặc addbb <uid1> <uid2> ..."),
            message_object, thread_id, thread_type, ttl=60000
        )
        return

    group_id = thread_id
    args = parts[1:]

    # =============== TRƯỜNG HỢP ADD ALL ===============
    if len(args) == 1 and args[0].lower() == "all":
        friends_list = fetchAllFriends(client)
        total = len(friends_list)

        if total == 0:
            client.replyMessage(
                Message(text="⚠️ Không tìm thấy bạn bè để thêm."),
                message_object, thread_id, thread_type, ttl=60000
            )
            return

        uids = [f["uid"] for f in friends_list if f.get("uid")]
        client.replyMessage(
            Message(text=f"🔍 Đang thêm {len(uids)} bạn vào nhóm bằng đa luồng..."),
            message_object, thread_id, thread_type, ttl=10000
        )

        add_results = addUsersToGroup(client, group_id, uids, max_threads=5)

    else:
        # =============== TRƯỜNG HỢP ADD UID TỰ NHẬP ===============
        uids = [str(uid) for uid in args]
        add_results = addUsersToGroup(client, group_id, uids, max_threads=5)

    msg = (
        f"🏁 Hoàn tất thêm vào nhóm:\n"
        f"✅ Thành công: {add_results['thanh_cong']} người\n"
        f"❌ Thất bại: {add_results['that_bai']} người"
    )

    client.replyMessage(
        Message(text=msg),
        message_object, thread_id, thread_type, ttl=86400000
    )


# ================================
#  ĐĂNG KÝ LỆNH
# ================================
def TQD():
    return {
        'addbb': handle_addbb
    }
