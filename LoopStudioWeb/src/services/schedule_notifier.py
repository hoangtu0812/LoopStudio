"""Scheduler gửi thông báo trước buổi học và task."""
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler


def _check_schedule_reminders(app):
    """Kiểm tra các buổi học sắp diễn ra và gửi thông báo."""
    with app.app_context():
        from ..app import db
        from ..models import ScheduleSession, NotificationConfig
        from ..services.telegram_service import send_telegram_message

        cfg = NotificationConfig.query.filter_by(
            config_type="schedule_reminder", enabled=True
        ).first()
        if not cfg or not cfg.chat_id:
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
                msg = f"⏰ Nhắc nhở: {s.schedule.name} - {s.session_date} lúc {s.start_time}"
                if send_telegram_message(cfg.chat_id, msg):
                    s.reminder_sent = True
        db.session.commit()


def _check_task_reminders(app):
    """Kiểm tra task sắp đến deadline."""
    with app.app_context():
        from ..app import db
        from ..models import Task, NotificationConfig
        from ..services.telegram_service import send_telegram_message

        cfg = NotificationConfig.query.filter_by(
            config_type="task_reminder", enabled=True
        ).first()
        if not cfg or not cfg.chat_id:
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
            msg = f"📋 Task: {t.title} - Deadline: {t.deadline}"
            send_telegram_message(cfg.chat_id, msg)
        db.session.commit()


def start_scheduler(app):
    """Khởi động scheduler trong Flask app context."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: _check_schedule_reminders(app), "interval", minutes=1)
    scheduler.add_job(lambda: _check_task_reminders(app), "interval", minutes=1)
    scheduler.start()
