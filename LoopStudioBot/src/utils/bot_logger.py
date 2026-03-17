"""Gửi log truy cập bot tới Web App API."""
import requests

from ..config import get_env
from ..utils.logger import get_logger

logger = get_logger(__name__)
WEB_APP_URL = get_env("WEB_APP_URL")  # http://loopstudioweb:5000


def log_bot_access(telegram_user_id: int, username: str, first_name: str, command: str, chat_id: int) -> None:
    """Gửi log tới Web App (không chặn nếu thất bại)."""
    if not WEB_APP_URL:
        return
    try:
        r = requests.post(
            f"{WEB_APP_URL.rstrip('/')}/api/bot/log",
            json={
                "telegram_user_id": telegram_user_id,
                "telegram_username": username,
                "telegram_first_name": first_name,
                "command": command,
                "chat_id": chat_id,
            },
            timeout=3,
        )
        if r.status_code != 204:
            logger.warning("Bot log API returned %s", r.status_code)
    except Exception as e:
        logger.debug("Bot log failed: %s", str(e))
