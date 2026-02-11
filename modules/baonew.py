import feedparser
import urllib.parse
import requests
from bs4 import BeautifulSoup
from zlapi.models import Message
from config import ADMIN

des = {
    'version': "2.0.1",
    'credits': "Latte",
    'description': "Tìm kiếm báo Google News",
    'power': "Thành viên"
}

# Lưu tạm kết quả tìm kiếm để lệnh xem dùng
search_cache = {}

def search_google_news(query, max_results=5):
    query_enc = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={query_enc}&hl=vi&gl=VN&ceid=VN:vi"
    feed = feedparser.parse(rss_url)
    results = []
    for entry in feed.entries[:max_results]:
        results.append((entry.title, entry.link))
    return results

def fetch_full_article(link):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(link, headers=headers, timeout=6)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        paragraphs = soup.find_all('p')
        content = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        return content if content else "⚠️ Không lấy được nội dung chi tiết."
    except Exception as e:
        return f"⚠️ Lỗi khi lấy bài báo: {str(e)}"

# Lệnh tìm kiếm báo
def handle_bao_command(message, message_object, thread_id, thread_type, author_id, client):
    parts = message.split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        client.replyMessage(Message(text="⚠️ Vui lòng nhập từ khóa tìm kiếm báo!"), message_object, thread_id, thread_type)
        return
    query = parts[1].strip()
    client.replyMessage(Message(text=f"🔎 Bạn vừa tìm kiếm báo hôm nay: '{query}'"), message_object, thread_id, thread_type)

    articles = search_google_news(query, max_results=5)
    if not articles:
        client.replyMessage(Message(text=f"❌ Không tìm thấy tin tức nào cho '{query}'"), message_object, thread_id, thread_type)
        return

    search_cache[author_id] = articles  # Lưu tạm để lệnh xem dùng

    msg_lines = []
    for i, (title, link) in enumerate(articles):
        msg_lines.append(f"{i+1}. {title}\n🔗 {link}")
    msg_text = "📰 Kết quả tìm kiếm:\n\n" + "\n\n".join(msg_lines)
    client.replyMessage(Message(text=msg_text), message_object, thread_id, thread_type)

# Lệnh xem full báo
def handle_xem_command(message, message_object, thread_id, thread_type, author_id, client):
    parts = message.split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        client.replyMessage(Message(text="⚠️ Vui lòng nhập số bài báo muốn xem!"), message_object, thread_id, thread_type)
        return
    if author_id not in search_cache:
        client.replyMessage(Message(text="⚠️ Chưa có tìm kiếm nào. Hãy dùng lệnh 'bao <từ khóa>' trước."), message_object, thread_id, thread_type)
        return

    try:
        index = int(parts[1].strip()) - 1
    except ValueError:
        client.replyMessage(Message(text="⚠️ Số bài báo không hợp lệ."), message_object, thread_id, thread_type)
        return

    articles = search_cache[author_id]
    if index < 0 or index >= len(articles):
        client.replyMessage(Message(text="⚠️ Số bài báo ngoài phạm vi."), message_object, thread_id, thread_type)
        return

    title, link = articles[index]
    client.replyMessage(Message(text=f"📰 Đang đọc bài báo: {title}"), message_object, thread_id, thread_type)

    full_text = fetch_full_article(link)
    max_len = 3000
    for i in range(0, len(full_text), max_len):
        part = full_text[i:i+max_len]
        client.replyMessage(Message(text=f"{part}\n\n🔗 Link gốc: {link}"), message_object, thread_id, thread_type)

def TQD():
    return {
        'báo': handle_bao_command,
        'xem': handle_xem_command
    }