from zlapi.models import Message, ThreadType
from config import ADMIN, IMEI
import threading
import time
import json
import re

des = {
    'version': "1.5.0",
    'credits': "Latte",
    'description': "spam join",
    'power': "Admin"
}

_spgr_loops = {}  # { group_id: {'thread': Thread, 'stop': Event} }

# --- Helpers ---
def check_admin(author_id):
    return str(author_id) in ADMIN

def _leave_group(client, group_id):
    try:
        if hasattr(client, "leaveGroup"):
            client.leaveGroup(group_id, imei=IMEI)
        elif hasattr(client, "leave_group"):
            client.leave_group(group_id)
    except Exception as e:
        print(f"[DEBUG] Leave lỗi: {e}")

def _join_group_by_link(client, group_link):
    try:
        if hasattr(client, "joinGroup"):
            return client.joinGroup(group_link)
        if hasattr(client, "join_group"):
            return client.join_group(group_link)
        if hasattr(client, "joinGroupByLink"):
            return client.joinGroupByLink(group_link)
    except Exception as e:
        print(f"[DEBUG] Join lỗi: {e}")
    return None

def _get_group_id_from_join_result(join_result):
    if not join_result:
        return None
    if isinstance(join_result, dict):
        for k in ("groupId", "group_id", "gr_id", "id", "gid"):
            if k in join_result and join_result[k]:
                return str(join_result[k])
        data = join_result.get("data") or join_result.get("group") or join_result
        if isinstance(data, dict):
            for k, v in data.items():
                if "id" in k.lower() and v:
                    return str(v)
    if isinstance(join_result, str):
        try:
            j = json.loads(join_result)
            return _get_group_id_from_join_result(j)
        except:
            m = re.search(r"\d{10,}", join_result)
            if m:
                return m.group(0)
    return None

def _get_group_id_by_api(client, group_link):
    for fn in ("getIDsGroup", "getIDsGroupByLink", "getIDs", "getIDs_from_link", "getIDsGroupInfo"):
        if hasattr(client, fn):
            try:
                res = getattr(client, fn)(group_link)
                if isinstance(res, str):
                    try: res = json.loads(res)
                    except: pass
                if isinstance(res, dict):
                    for key in ("groupId", "group_id", "id", "gid", "gr_id"):
                        if res.get(key): return str(res.get(key))
                    data = res.get("data") or res
                    if isinstance(data, dict):
                        for k, v in data.items():
                            if "id" in k.lower() and v: return str(v)
            except: continue
    return None

# --- Core loop: leave → join liên tục ---
def _leave_join_loop(client, group_link, group_id, cycle_delay):
    event = _spgr_loops[group_id]['stop']
    while not event.is_set():
        # Rời nhóm
        _leave_group(client, group_id)
        time.sleep(1)

        # Join lại
        joined_gid = None
        join_res = _join_group_by_link(client, group_link if group_link else f"https://zalo.me/{group_id}")

        if join_res:
            joined_gid = _get_group_id_from_join_result(join_res)

        if not joined_gid and group_link:
            joined_gid = _get_group_id_by_api(client, group_link)

        if joined_gid:
            group_id = joined_gid
            print(f"[LOOP] Join thành công group {group_id}")
        else:
            print(f"[LOOP] ❌ Không join được group {group_link or group_id}, chờ 10s")
            time.sleep(10)
            continue

        time.sleep(max(1, cycle_delay))  # delay giữa các chu kỳ

    print(f"[LOOP] Loop group {group_id} đã dừng.")

# --- Commands ---
def handle_leave_join_start(message, message_object, thread_id, thread_type, author_id, client):
    if not check_admin(author_id):
        client.replyMessage(Message(text="🚫 Chỉ admin mới dùng lệnh này."), message_object, thread_id, thread_type)
        return

    parts = message.split()
    if len(parts) < 3:
        client.replyMessage(Message(text="⚠️ Cú pháp: .leave_join_start <LINK_OR_UID> <DELAY_SEC>"),
                            message_object, thread_id, thread_type)
        return

    group_link_or_uid = parts[1].strip()
    try:
        cycle_delay = float(parts[2].strip())
    except:
        client.replyMessage(Message(text="⚠️ Sai DELAY. Ví dụ: .leave_join_start https://zalo.me/xxxx 5"),
                            message_object, thread_id, thread_type)
        return

    group_link = group_link_or_uid if group_link_or_uid.startswith("http") else None
    group_id = None if group_link else group_link_or_uid

    if group_id in _spgr_loops:
        client.replyMessage(Message(text=f"⚠️ Loop group {group_id} đang chạy"), message_object, thread_id, thread_type)
        return

    stop_event = threading.Event()
    t = threading.Thread(target=_leave_join_loop, args=(client, group_link, group_id, cycle_delay), daemon=True)
    _spgr_loops[group_id] = {'thread': t, 'stop': stop_event}
    t.start()

    client.replyMessage(Message(text=f"✅ Bắt đầu loop leave → join cho group {group_id or group_link}, delay: {cycle_delay}s"),
                        message_object, thread_id, thread_type)

def handle_leave_join_stop(message, message_object, thread_id, thread_type, author_id, client):
    if not check_admin(author_id):
        client.replyMessage(Message(text="🚫 Chỉ admin mới dùng lệnh này."), message_object, thread_id, thread_type)
        return
    parts = message.split()
    if len(parts) < 2:
        client.replyMessage(Message(text="⚠️ Cú pháp: .leave_join_stop <GROUP_ID>"), message_object, thread_id, thread_type)
        return
    group_id = parts[1].strip()
    info = _spgr_loops.get(group_id)
    if not info:
        client.replyMessage(Message(text=f"⚠️ Không tìm thấy loop đang chạy cho {group_id}"), message_object, thread_id, thread_type)
        return
    info['stop'].set()
    time.sleep(0.5)
    _spgr_loops.pop(group_id, None)
    client.replyMessage(Message(text=f"✅ Đã dừng loop leave → join cho {group_id}"), message_object, thread_id, thread_type)

# --- Export commands ---
def TQD():
    return {
        'spjoin': handle_leave_join_start,
        'rsspjoin': handle_leave_join_stop
    }