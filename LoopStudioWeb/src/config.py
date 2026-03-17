"""Cấu hình Web App - đọc từ biến môi trường."""
import os
from pathlib import Path

from dotenv import load_dotenv

_base = Path(__file__).resolve().parent
env_path = _base.parent / ".env"
if not env_path.exists():
    env_path = _base.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def get_env(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)


SECRET_KEY = get_env("SECRET_KEY") or "dev-secret-change-in-production"
SQLALCHEMY_DATABASE_URI = get_env(
    "DATABASE_URL",
    f"sqlite:///{_base.parent.parent / 'app.db'}",
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Telegram (dùng để gửi thông báo từ web)
BOT_TOKEN = get_env("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else None
