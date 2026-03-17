"""
Handlers - Xử lý các lệnh Telegram: /start, /help, /netstat
"""
from telegram import Update
from telegram.ext import ContextTypes

from ..services.netstat_service import NetstatService
from ..utils.logger import get_logger
from ..utils.bot_logger import log_bot_access

logger = get_logger(__name__)

# Mô tả các lệnh cho /help
COMMANDS_HELP = """
📋 **Danh sách lệnh:**

/start - Chào mừng và giới thiệu bot
/help - Xem danh sách lệnh và hướng dẫn
/netstat - Báo cáo hệ thống: Speedtest, CPU, RAM, Disk, IP Public

Bot **LoopStudioBot** - Giám sát server tự động.
"""


def _log_access(update: Update, command: str) -> None:
    user = update.effective_user
    log_bot_access(
        telegram_user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "",
        command=command,
        chat_id=update.effective_chat.id,
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý /start - Chào mừng người dùng."""
    _log_access(update, "/start")
    user = update.effective_user
    welcome = (
        f"👋 Xin chào {user.first_name}!\n\n"
        "Đây là **LoopStudioBot** - Bot đa năng giám sát hệ thống.\n"
        "Gõ /help để xem danh sách lệnh."
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")
    logger.info("User %s started bot", user.id)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý /help - Liệt kê tất cả lệnh."""
    _log_access(update, "/help")
    await update.message.reply_text(COMMANDS_HELP, parse_mode="Markdown")
    logger.info("User %s requested help", update.effective_user.id)


async def cmd_netstat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý /netstat - Báo cáo Speedtest + tài nguyên server + IP."""
    _log_access(update, "/netstat")
    sent = await update.message.reply_text("⏳ Đang thu thập dữ liệu...")
    try:
        result = NetstatService.get_netstat()
        message = NetstatService.format_netstat_message(result)
        await sent.edit_text(message, parse_mode="Markdown")
        logger.info("Netstat completed for user %s", update.effective_user.id)
    except Exception as e:
        logger.exception("Lỗi khi chạy netstat: %s", str(e))
        await sent.edit_text(f"❌ Lỗi: {str(e)}")


def register_handlers(application) -> None:
    """Đăng ký tất cả handlers vào application."""
    from telegram.ext import CommandHandler

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("netstat", cmd_netstat))
    logger.info("Handlers registered: start, help, netstat")
