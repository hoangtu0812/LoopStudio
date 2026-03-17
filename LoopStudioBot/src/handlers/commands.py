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
/otp - Lấy mã xác thực đăng ký tài khoản (VD: /otp admin)

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


async def cmd_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý /otp - Lấy mã xác thực tài khoản."""
    _log_access(update, "/otp")
    if not context.args:
        await update.message.reply_text("❌ Vui lòng nhập username. Ví dụ: `/otp admin`", parse_mode="Markdown")
        return
    
    username = context.args[0]
    user = update.effective_user
    sent = await update.message.reply_text(f"⏳ Đang lấy mã OTP cho tài khoản `{username}`...", parse_mode="Markdown")
    
    from ..utils.bot_logger import WEB_APP_URL
    import requests

    if not WEB_APP_URL:
        await sent.edit_text("❌ Bot chưa cấu hình liên kết Web App.")
        return

    try:
        r = requests.post(f"{WEB_APP_URL.rstrip('/')}/api/bot/otp", json={
            "username": username,
            "telegram_user_id": user.id
        }, timeout=5)
        
        if r.status_code == 200:
            data = r.json()
            otp = data.get("otp")
            await sent.edit_text(
                f"✅ Mã OTP của bạn cho tài khoản **{username}** là: `{otp}`\n\n"
                f"Vui lòng nhập mã này trên web để kích hoạt tài khoản.", 
                parse_mode="Markdown"
            )
        else:
            try:
                err = r.json().get("error", "Lỗi không xác định")
            except Exception:
                err = "Lỗi phản hồi API"
            await sent.edit_text(f"❌ Không thể lấy mã OTP: {err}")
    except Exception as e:
        logger.exception("OTP error: %s", str(e))
        await sent.edit_text(f"❌ Lỗi kết nối đến Web App: {str(e)}")


def register_handlers(application) -> None:
    """Đăng ký tất cả handlers vào application."""
    from telegram.ext import CommandHandler

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("netstat", cmd_netstat))
    application.add_handler(CommandHandler("otp", cmd_otp))
    logger.info("Handlers registered: start, help, netstat, otp")
