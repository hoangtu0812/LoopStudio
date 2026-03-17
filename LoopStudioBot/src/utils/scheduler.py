"""
Scheduler - Chạy tác vụ định kỳ (netstat mỗi 2 giờ).
Sử dụng APScheduler với timezone cấu hình.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..config import NETSTAT_INTERVAL_SECONDS, REPORT_CHAT_ID, TIMEZONE
from ..utils.logger import get_logger

logger = get_logger(__name__)


async def _send_scheduled_netstat(application) -> None:
    """
    Job chạy định kỳ: lấy netstat và gửi vào REPORT_CHAT_ID.
    application được inject khi setup.
    """
    from ..services.netstat_service import NetstatService

    try:
        result = NetstatService.get_netstat()
        message = NetstatService.format_netstat_message(result)
        await application.bot.send_message(
            chat_id=REPORT_CHAT_ID,
            text=message,
            parse_mode="Markdown",
        )
        logger.info("Đã gửi báo cáo netstat định kỳ tới %s", REPORT_CHAT_ID)
    except Exception as e:
        logger.exception("Lỗi gửi báo cáo định kỳ: %s", str(e))


def setup_scheduler(application) -> AsyncIOScheduler:
    """
    Cấu hình scheduler chạy netstat mỗi NETSTAT_INTERVAL_SECONDS giây.
    Trả về scheduler đã start.
    """
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    def job_wrapper():
        import asyncio

        asyncio.create_task(_send_scheduled_netstat(application))

    # Inject application vào closure
    async def job():
        await _send_scheduled_netstat(application)

    scheduler.add_job(
        job,
        "interval",
        seconds=NETSTAT_INTERVAL_SECONDS,
        id="netstat_report",
    )
    scheduler.start()
    logger.info(
        "Scheduler started: netstat mỗi %s giây",
        NETSTAT_INTERVAL_SECONDS,
    )
    return scheduler
