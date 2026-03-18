from datetime import datetime

from ..app import db


class TodoTask(db.Model):
    """Công việc cá nhân: lặp theo tuần hoặc theo deadline."""

    __tablename__ = "todo_tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    note = db.Column(db.String(1000), nullable=True)
    task_type = db.Column(db.String(20), nullable=False)  # weekly | deadline

    # Weekly task: 0=Mon .. 6=Sun
    weekday = db.Column(db.Integer, nullable=True)

    # Deadline task: công việc có khoảng thời gian từ start_at đến deadline
    start_at = db.Column(db.DateTime, nullable=True)
    deadline = db.Column(db.DateTime, nullable=True)
    reminder_minutes_before = db.Column(db.Integer, nullable=False, default=30)
    deadline_reminder_sent = db.Column(db.Boolean, default=False)

    # Kanban / quản lý tiến độ
    status = db.Column(db.String(20), nullable=False, default="backlog")  # backlog | doing | done
    priority = db.Column(db.Integer, nullable=False, default=2)  # 1=thấp, 2=trung bình, 3=cao
    lane = db.Column(db.String(50), nullable=True)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
