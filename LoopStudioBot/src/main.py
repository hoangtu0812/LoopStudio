"""
LoopStudioBot - Điểm chạy ứng dụng.
Khởi động bot, đăng ký handlers, và scheduler.
"""
from telegram.error import Conflict
from telegram.ext import Application

from .config import BOT_TOKEN
from .handlers import register_handlers
from .utils.logger import get_logger
from .utils.scheduler import setup_scheduler

logger = get_logger(__name__)


def main() -> None:
    """Khởi động bot."""
    # Tạo Application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Đăng ký handlers
    register_handlers(application)

    # Khởi động scheduler (netstat định kỳ)
    setup_scheduler(application)

    # Chạy bot
    logger.info("LoopStudioBot đang khởi động...")
    try:
        application.run_polling(allowed_updates=["message"])
    except Conflict:
        logger.error(
            "Bot conflict: phát hiện instance khác đang polling cùng BOT_TOKEN. "
            "Hãy đảm bảo chỉ có một bot instance đang chạy."
        )


if __name__ == "__main__":
    main()
