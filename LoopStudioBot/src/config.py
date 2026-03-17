"""
Cấu hình ứng dụng - Đọc từ biến môi trường (.env)
Mọi thông tin nhạy cảm (Token, Chat ID) đều lấy từ env vars.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env: ưu tiên thư mục chứa config, sau đó thư mục gốc dự án
_base = Path(__file__).resolve().parent
env_path = _base.parent / ".env"  # LoopStudioBot/.env
if not env_path.exists():
    env_path = _base.parent.parent / ".env"  # project root
load_dotenv(dotenv_path=env_path)


def get_env(key: str, default: str | None = None) -> str | None:
    """Lấy giá trị từ biến môi trường."""
    return os.getenv(key, default)


# Bot credentials
BOT_TOKEN = get_env("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN phải được cấu hình trong file .env")

# Chat ID nhận báo cáo định kỳ (có thể là user hoặc group)
REPORT_CHAT_ID = get_env("REPORT_CHAT_ID")
if not REPORT_CHAT_ID:
    raise ValueError("REPORT_CHAT_ID phải được cấu hình trong file .env")

# Interval chạy netstat tự động (giây) - mặc định 2 giờ = 7200
NETSTAT_INTERVAL_SECONDS = int(get_env("NETSTAT_INTERVAL_SECONDS", "7200"))

# Timezone cho scheduler (mặc định Asia/Ho_Chi_Minh)
TIMEZONE = get_env("TIMEZONE", "Asia/Ho_Chi_Minh")
