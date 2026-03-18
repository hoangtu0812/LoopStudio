from datetime import datetime, date, time

from ..app import db


class Schedule(db.Model):
    """Thời khóa biểu - môn học, thời gian, khoảng thời gian."""

    __tablename__ = "schedules"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # Môn A
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Mon, 6=Sun
    start_time = db.Column(db.Time, nullable=False)  # 18:00
    end_time = db.Column(db.Time, nullable=False)  # 21:00
    start_date = db.Column(db.Date, nullable=False)  # 17/3/2026
    end_date = db.Column(db.Date, nullable=False)  # 17/5/2026
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sessions = db.relationship("ScheduleSession", backref="schedule", cascade="all, delete-orphan")


class ScheduleSession(db.Model):
    """Một buổi học cụ thể (sinh từ Schedule theo ngày)."""

    __tablename__ = "schedule_sessions"

    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey("schedules.id"), nullable=False)
    session_date = db.Column(db.Date, nullable=False)  # Ngày cụ thể
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    reminder_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    check_ins = db.relationship("CheckIn", backref="session", cascade="all, delete-orphan")
    tasks = db.relationship("Task", backref="session", cascade="all, delete-orphan")


class CheckIn(db.Model):
    """Check-in xác nhận đã tham gia buổi học."""

    __tablename__ = "check_ins"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("schedule_sessions.id"), nullable=False)
    checked_at = db.Column(db.DateTime, default=datetime.utcnow)


class Task(db.Model):
    """Task của buổi học - có deadline."""

    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("schedule_sessions.id"), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    deadline = db.Column(db.DateTime, nullable=True)
    done = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class NotificationConfig(db.Model):
    """Cấu hình thông báo Telegram - channel, thời gian trước buổi/task."""

    __tablename__ = "notification_configs"

    id = db.Column(db.Integer, primary_key=True)
    config_type = db.Column(db.String(50), nullable=False)  # "schedule_reminder" | "task_reminder"
    chat_id = db.Column(db.String(50), nullable=False)  # Channel/chat nhận tin
    chat_target_id = db.Column(db.Integer, nullable=True)  # Tham chiếu danh bạ chat Telegram (tuỳ chọn)
    minutes_before = db.Column(db.Integer, nullable=False)  # 15 = 15 phút trước
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TelegramChatTarget(db.Model):
    """Danh bạ chat Telegram để tái sử dụng trong cấu hình thông báo."""

    __tablename__ = "telegram_chat_targets"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(120), nullable=False, unique=True)  # Ví dụ: "Nhóm A"
    chat_id = db.Column(db.String(50), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
