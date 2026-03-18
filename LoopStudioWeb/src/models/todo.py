from datetime import datetime

from sqlalchemy.orm import backref

from ..app import db


class TodoTask(db.Model):
    """Công việc cá nhân: lặp theo tuần hoặc theo deadline."""

    __tablename__ = "todo_tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    note = db.Column(db.String(1000), nullable=True)
    task_type = db.Column(db.String(20), nullable=False)  # weekly | deadline
    parent_task_id = db.Column(db.Integer, db.ForeignKey("todo_tasks.id"), nullable=True, index=True)

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
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent_task = db.relationship(
        "TodoTask",
        remote_side=[id],
        backref=backref("subtasks", cascade="all, delete-orphan"),
    )
    change_logs = db.relationship(
        "TodoTaskChangeLog",
        backref="task",
        cascade="all, delete-orphan",
        order_by="desc(TodoTaskChangeLog.changed_at)",
    )


class TodoTaskChangeLog(db.Model):
    """Lịch sử thay đổi task/subtask."""

    __tablename__ = "todo_task_change_logs"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("todo_tasks.id"), nullable=False, index=True)
    action = db.Column(db.String(40), nullable=False)  # created | updated | status_changed | ...
    detail = db.Column(db.String(2000), nullable=True)
    changed_by = db.Column(db.String(120), nullable=True)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
