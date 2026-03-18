"""Quản lý công việc cá nhân (weekly/deadline)."""
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..app import db
from ..models import TodoTask

todo_bp = Blueprint("todo", __name__)

WEEKDAY_OPTIONS = [
    (0, "Thứ 2"),
    (1, "Thứ 3"),
    (2, "Thứ 4"),
    (3, "Thứ 5"),
    (4, "Thứ 6"),
    (5, "Thứ 7"),
    (6, "Chủ nhật"),
]


@todo_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        note = (request.form.get("note") or "").strip()
        task_type = (request.form.get("task_type") or "weekly").strip()

        if not title:
            flash("Vui lòng nhập tiêu đề công việc.", "error")
            return redirect(url_for("todo.index"))
        if task_type not in {"weekly", "deadline"}:
            flash("Loại công việc không hợp lệ.", "error")
            return redirect(url_for("todo.index"))

        task = TodoTask(title=title, note=note or None, task_type=task_type, is_active=True)

        if task_type == "weekly":
            weekday_raw = request.form.get("weekday")
            try:
                weekday = int(weekday_raw)
            except (TypeError, ValueError):
                flash("Vui lòng chọn thứ trong tuần cho công việc lặp.", "error")
                return redirect(url_for("todo.index"))
            if weekday < 0 or weekday > 6:
                flash("Giá trị thứ trong tuần không hợp lệ.", "error")
                return redirect(url_for("todo.index"))
            task.weekday = weekday
            task.deadline = None
        else:
            start_raw = request.form.get("start_at")
            deadline_raw = request.form.get("deadline")
            if not start_raw or not deadline_raw:
                flash("Vui lòng chọn đầy đủ từ ngày và đến ngày cho công việc theo hạn.", "error")
                return redirect(url_for("todo.index"))
            try:
                task.start_at = datetime.strptime(start_raw, "%Y-%m-%dT%H:%M")
                task.deadline = datetime.strptime(deadline_raw, "%Y-%m-%dT%H:%M")
            except ValueError:
                flash("Khoảng thời gian không đúng định dạng.", "error")
                return redirect(url_for("todo.index"))
            if task.start_at > task.deadline:
                flash("Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc.", "error")
                return redirect(url_for("todo.index"))

            reminder_minutes_raw = request.form.get("reminder_minutes_before", "30")
            try:
                reminder_minutes = int(reminder_minutes_raw)
            except ValueError:
                reminder_minutes = 30
            task.reminder_minutes_before = max(1, reminder_minutes)
            task.weekday = None

        db.session.add(task)
        db.session.commit()
        flash("Đã tạo công việc mới.", "success")
        return redirect(url_for("todo.index"))

    tasks = TodoTask.query.order_by(TodoTask.is_active.desc(), TodoTask.created_at.desc()).all()
    weekday_map = {k: v for k, v in WEEKDAY_OPTIONS}
    return render_template(
        "todo/index.html",
        tasks=tasks,
        weekday_options=WEEKDAY_OPTIONS,
        weekday_map=weekday_map,
    )


@todo_bp.route("/<int:id>/toggle", methods=["POST"])
@login_required
def toggle(id):
    task = TodoTask.query.get_or_404(id)
    task.is_active = not task.is_active
    db.session.commit()
    flash("Đã cập nhật trạng thái công việc.", "success")
    return redirect(url_for("todo.index"))


@todo_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    task = TodoTask.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    flash("Đã xóa công việc.", "success")
    return redirect(url_for("todo.index"))
