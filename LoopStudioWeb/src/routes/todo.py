"""Quản lý công việc cá nhân (weekly/deadline)."""
from datetime import datetime, timedelta

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

        task = TodoTask(
            title=title,
            note=note or None,
            task_type=task_type,
            is_active=True,
        )

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


@todo_bp.route("/board")
@login_required
def board():
    """Kanban board: phân cột theo status."""
    tasks = TodoTask.query.filter_by(is_active=True).all()
    columns: dict[str, list[TodoTask]] = {"backlog": [], "doing": [], "done": []}
    for t in tasks:
        col = t.status or "backlog"
        if col not in columns:
            col = "backlog"
        columns[col].append(t)

    for col_tasks in columns.values():
        col_tasks.sort(key=lambda t: (-(t.priority or 2), t.deadline or t.start_at or t.created_at))

    return render_template("todo/board.html", columns=columns)


@todo_bp.route("/<int:id>/move", methods=["POST"])
@login_required
def move(id: int):
    """Đổi status của task (dùng cho Kanban)."""
    task = TodoTask.query.get_or_404(id)
    new_status = request.form.get("status") or ""
    if new_status not in {"backlog", "doing", "done"}:
        flash("Trạng thái không hợp lệ.", "error")
        return redirect(url_for("todo.board"))
    task.status = new_status
    db.session.commit()
    return redirect(url_for("todo.board"))


@todo_bp.route("/gantt")
@login_required
def gantt():
    tasks = TodoTask.query.filter_by(is_active=True).all()
    prepared_rows: list[dict] = []
    spans: list[tuple[datetime, datetime]] = []

    for t in tasks:
        start = t.start_at or t.created_at
        end = t.deadline or start
        if not start or not end:
            continue
        if end < start:
            end = start
        spans.append((start, end))
        prepared_rows.append(
            {
                "id": t.id,
                "title": t.title,
                "status": t.status or "backlog",
                "start": start,
                "end": end,
                "start_label": start.strftime("%d/%m/%Y"),
                "end_label": end.strftime("%d/%m/%Y"),
            }
        )

    if not spans:
        return render_template(
            "todo/gantt.html",
            gantt_rows=[],
            week_headers=[],
            month_groups=[],
            total_weeks=0,
        )

    min_start = min(s for s, _ in spans)
    max_end = max(e for _, e in spans)

    timeline_start = min_start - timedelta(days=min_start.weekday())  # Monday
    timeline_end = max_end + timedelta(days=(6 - max_end.weekday()))  # Sunday
    total_days = max((timeline_end - timeline_start).days + 1, 1)
    total_weeks = max((total_days + 6) // 7, 1)

    week_starts = [timeline_start + timedelta(days=7 * i) for i in range(total_weeks)]
    week_headers: list[dict] = []
    month_groups: list[dict] = []
    current_month = None
    for ws in week_starts:
        month_label = ws.strftime("%B")
        if current_month != month_label:
            month_groups.append({"label": month_label, "span": 0})
            current_month = month_label
        month_groups[-1]["span"] += 1
        week_index_in_month = ((ws.day - 1) // 7) + 1
        week_headers.append({"label": f"W{week_index_in_month}"})

    gantt_rows: list[dict] = []
    for row in prepared_rows:
        start_offset_days = (row["start"] - timeline_start).total_seconds() / 86400
        duration_days = max((row["end"] - row["start"]).total_seconds() / 86400, 0.75)
        left_pct = (start_offset_days / total_days) * 100
        width_pct = (duration_days / total_days) * 100
        gantt_rows.append(
            {
                **row,
                "left_pct": round(left_pct, 3),
                "width_pct": round(width_pct, 3),
            }
        )

    return render_template(
        "todo/gantt.html",
        gantt_rows=gantt_rows,
        week_headers=week_headers,
        month_groups=month_groups,
        total_weeks=total_weeks,
    )
