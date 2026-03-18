"""Scheduler gửi thông báo trước buổi học và task."""
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from ..config import TIMEZONE


def build_schedule_reminder_message(session) -> str:
    """Sinh nội dung thông báo nhắc buổi học theo định dạng chuẩn."""
    return (
        "━━━━━━━━━━━━━━━━━━\n"
        "📚 NHẮC LỊCH HỌC\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"• Môn học: {session.schedule.name}\n"
        f"• Ngày: {session.session_date.strftime('%d/%m/%Y')}\n"
        f"• Khung giờ: {session.start_time.strftime('%H:%M')} - {session.end_time.strftime('%H:%M')}\n"
        "✅ Chuẩn bị vào học đúng giờ nhé!"
    )


def _check_schedule_reminders(app):
    """Kiểm tra các buổi học sắp diễn ra và gửi thông báo."""
    with app.app_context():
        from ..app import db
        from ..models import ScheduleSession, NotificationConfig, TelegramChatTarget
        from ..services.telegram_service import send_telegram_message

        cfg = NotificationConfig.query.filter_by(
            config_type="schedule_reminder", enabled=True
        ).first()
        if not cfg:
            return
        chat_id = cfg.chat_id
        if cfg.chat_target_id:
            target = TelegramChatTarget.query.get(cfg.chat_target_id)
            chat_id = target.chat_id if target and target.is_active else chat_id
        if not chat_id:
            return
        now = datetime.now()
        lo = now + timedelta(minutes=cfg.minutes_before - 2)
        hi = now + timedelta(minutes=cfg.minutes_before + 2)
        sessions = ScheduleSession.query.filter(
            ScheduleSession.reminder_sent == False,
        ).all()
        for s in sessions:
            session_dt = datetime.combine(s.session_date, s.start_time)
            if lo <= session_dt <= hi:
                msg = build_schedule_reminder_message(s)
                if send_telegram_message(chat_id, msg):
                    s.reminder_sent = True
        db.session.commit()


def _check_task_reminders(app):
    """Kiểm tra task sắp đến deadline."""
    with app.app_context():
        from ..app import db
        from ..models import Task, NotificationConfig, TelegramChatTarget
        from ..services.telegram_service import send_telegram_message

        cfg = NotificationConfig.query.filter_by(
            config_type="task_reminder", enabled=True
        ).first()
        if not cfg:
            return
        chat_id = cfg.chat_id
        if cfg.chat_target_id:
            target = TelegramChatTarget.query.get(cfg.chat_target_id)
            chat_id = target.chat_id if target and target.is_active else chat_id
        if not chat_id:
            return
        now = datetime.now()
        target = now + timedelta(minutes=cfg.minutes_before)
        tasks = Task.query.filter(
            Task.done == False,
            Task.deadline != None,
            Task.deadline >= now,
            Task.deadline <= target,
        ).all()
        for t in tasks:
            deadline_str = t.deadline.strftime("%H:%M %d/%m/%Y")
            msg = (
                "━━━━━━━━━━━━━━━━━━\n"
                "📌 NHẮC TASK BUỔI HỌC\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"• Công việc: {t.title}\n"
                f"• Deadline: {deadline_str}\n"
                "⚠️ Đừng quên hoàn thành trước hạn!"
            )
            send_telegram_message(chat_id, msg)
        db.session.commit()


def _get_todo_chat_ids():
    from ..models import NotificationConfig, TelegramChatTarget

    configs = NotificationConfig.query.filter(
        NotificationConfig.enabled == True,  # noqa: E712
    ).all()
    target_map = {
        t.id: t.chat_id
        for t in TelegramChatTarget.query.filter(
            TelegramChatTarget.is_active == True  # noqa: E712
        ).all()
    }

    def _resolve_chat_id(cfg):
        return (target_map.get(cfg.chat_target_id) or cfg.chat_id or "").strip()

    preferred = {"todo_daily_digest", "todo_deadline_reminder"}
    preferred_chat_ids = {
        _resolve_chat_id(c)
        for c in configs
        if c.config_type in preferred and _resolve_chat_id(c)
    }
    if preferred_chat_ids:
        return sorted(preferred_chat_ids)

    fallback_chat_ids = {
        _resolve_chat_id(c)
        for c in configs
        if c.config_type == "schedule_reminder" and _resolve_chat_id(c)
    }
    return sorted(fallback_chat_ids)


def _send_daily_todo_digest(app):
    """Mỗi sáng gửi danh sách việc cần làm trong ngày."""
    with app.app_context():
        from ..services.telegram_service import send_telegram_message
        from ..services.todo_service import build_today_todo_message

        chat_ids = _get_todo_chat_ids()
        if not chat_ids:
            return

        msg = build_today_todo_message()
        for chat_id in chat_ids:
            send_telegram_message(chat_id, msg)


def _check_todo_deadline_reminders(app):
    """Nhắc trước deadline cho todo loại deadline."""
    with app.app_context():
        from ..app import db
        from ..models import TodoTask
        from ..services.telegram_service import send_telegram_message

        chat_ids = _get_todo_chat_ids()
        if not chat_ids:
            return

        now = datetime.now()
        tasks = TodoTask.query.filter(
            TodoTask.task_type == "deadline",
            TodoTask.is_active == True,  # noqa: E712
            TodoTask.start_at != None,  # noqa: E711
            TodoTask.deadline != None,  # noqa: E711
            TodoTask.deadline_reminder_sent == False,  # noqa: E712
        ).all()

        for task in tasks:
            remind_at = task.deadline - timedelta(minutes=task.reminder_minutes_before or 30)
            active_from = max(remind_at, task.start_at)
            if active_from <= now <= task.deadline:
                msg = (
                    "━━━━━━━━━━━━━━━━━━\n"
                    "🗂️ NHẮC TODO DEADLINE\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    f"• Công việc: {task.title}\n"
                    f"• Bắt đầu: {task.start_at.strftime('%H:%M %d/%m/%Y')}\n"
                    f"• Kết thúc: {task.deadline.strftime('%H:%M %d/%m/%Y')}\n"
                    f"• Nhắc trước: {task.reminder_minutes_before or 30} phút\n"
                    "🚀 Đây là thời điểm tốt để bắt đầu ngay!"
                )
                if task.note:
                    msg += f"\n📝 Ghi chú: {task.note}"

                sent_ok = False
                for chat_id in chat_ids:
                    if send_telegram_message(chat_id, msg):
                        sent_ok = True
                if sent_ok:
                    task.deadline_reminder_sent = True
        db.session.commit()


def _check_uptime_monitors(app):
    """Check uptime các website đến hạn."""
    with app.app_context():
        from ..services.uptime_service import check_due_sites

        check_due_sites()


def _cleanup_uptime_history(app):
    """Dọn lịch sử uptime quá cũ (7 ngày)."""
    with app.app_context():
        from ..services.uptime_service import cleanup_old_checks

        cleanup_old_checks(days=7)


def start_scheduler(app):
    """Khởi động scheduler trong Flask app context."""
    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(lambda: _check_schedule_reminders(app), "interval", minutes=1)
    scheduler.add_job(lambda: _check_task_reminders(app), "interval", minutes=1)
    scheduler.add_job(lambda: _check_todo_deadline_reminders(app), "interval", minutes=1)
    scheduler.add_job(lambda: _send_daily_todo_digest(app), "cron", hour=7, minute=30)
    scheduler.add_job(lambda: _check_uptime_monitors(app), "interval", seconds=30)
    scheduler.add_job(lambda: _cleanup_uptime_history(app), "cron", hour=3, minute=10)
    scheduler.start()
