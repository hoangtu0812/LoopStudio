"""Gửi tin nhắn Telegram qua HTTP API."""
import requests

from ..config import TELEGRAM_API


def send_telegram_message(chat_id: str, text: str) -> bool:
    """Gửi tin nhắn tới chat_id. Trả về True nếu thành công."""
    if not TELEGRAM_API:
        return False
    try:
        r = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False
