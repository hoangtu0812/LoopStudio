"""Gửi tin nhắn Telegram qua HTTP API."""
import requests

from ..config import TELEGRAM_API


def send_telegram_message_verbose(chat_id: str, text: str) -> tuple[bool, str | None]:
    """Gửi tin nhắn và trả về (thành công, mô tả lỗi)."""
    if not TELEGRAM_API:
        return False, "Thiếu BOT_TOKEN."
    try:
        r = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        if r.status_code == 200:
            return True, None
        desc = None
        try:
            payload = r.json()
            desc = payload.get("description")
        except Exception:
            desc = None
        return False, desc or f"HTTP {r.status_code}"
    except Exception as exc:
        return False, str(exc)


def send_telegram_message(chat_id: str, text: str) -> bool:
    """Gửi tin nhắn tới chat_id. Trả về True nếu thành công."""
    ok, _ = send_telegram_message_verbose(chat_id, text)
    return ok
