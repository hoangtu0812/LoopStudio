"""Quản lý công việc cá nhân (weekly/deadline + subtask + gantt nâng cao)."""
from datetime import date, datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..app import db
from ..models import TodoTask, TodoTaskChangeLog

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


def _parse_datetime_local(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M")
    except ValueError:
        return None


def _actor_name() -> str:
    return getattr(current_user, "username", None) or "system"


def _log_change(task: TodoTask, action: str, detail: str | None = None) -> None:
    db.session.add(
        TodoTaskChangeLog(
            task_id=task.id,
            action=action,
            detail=detail,
            changed_by=_actor_name(),
        )
    )


def _fmt_dt(dt: datetime | None) -> str:
    return dt.strftime("%H:%M %d/%m/%Y") if dt else "N/A"


def _collect_task_changes(task: TodoTask, form_data: dict) -> list[str]:
    changes: list[str] = []
    old_title = task.title or ""
    new_title = (form_data.get("title") or "").strip()
    if new_title and new_title != old_title:
        changes.append(f"Tiêu đề: '{old_title}' -> '{new_title}'")

    old_note = task.note or ""
    new_note = (form_data.get("note") or "").strip()
    if new_note != old_note:
        changes.append("Đã cập nhật mô tả/ghi chú")

    old_type = task.task_type
    new_type = (form_data.get("task_type") or task.task_type).strip()
    if new_type != old_type:
        changes.append(f"Loại: {old_type} -> {new_type}")

    old_start = _fmt_dt(task.start_at)
    new_start_dt = _parse_datetime_local(form_data.get("start_at"))
    if (new_start_dt or None) != (task.start_at or None):
        changes.append(f"Bắt đầu: {old_start} -> {_fmt_dt(new_start_dt)}")

    old_deadline = _fmt_dt(task.deadline)
    new_deadline_dt = _parse_datetime_local(form_data.get("deadline"))
    if (new_deadline_dt or None) != (task.deadline or None):
        changes.append(f"Deadline: {old_deadline} -> {_fmt_dt(new_deadline_dt)}")

    old_weekday = task.weekday
    new_weekday = form_data.get("weekday")
    if new_weekday is not None and str(old_weekday) != str(new_weekday):
        changes.append(f"Thứ lặp: {old_weekday} -> {new_weekday}")

    return changes


def _timeline_bounds(view_mode: str, anchor_date: date, from_date: date | None, to_date: date | None) -> tuple[datetime, datetime]:
    if view_mode == "week":
        start = anchor_date - timedelta(days=anchor_date.weekday())
        end = start + timedelta(days=6)
    elif view_mode == "year":
        start = date(anchor_date.year, 1, 1)
        end = date(anchor_date.year, 12, 31)
    elif view_mode == "custom" and from_date and to_date:
        start = min(from_date, to_date)
        end = max(from_date, to_date)
    else:  # month
        start = date(anchor_date.year, anchor_date.month, 1)
        if anchor_date.month == 12:
            end = date(anchor_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(anchor_date.year, anchor_date.month + 1, 1) - timedelta(days=1)
    return datetime.combine(start, datetime.min.time()), datetime.combine(end, datetime.max.time())


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
            task.start_at = None
            task.deadline = None
        else:
            start_raw = request.form.get("start_at")
            deadline_raw = request.form.get("deadline")
            if not start_raw or not deadline_raw:
                flash("Vui lòng chọn đầy đủ từ ngày và đến ngày cho công việc theo hạn.", "error")
                return redirect(url_for("todo.index"))
            task.start_at = _parse_datetime_local(start_raw)
            task.deadline = _parse_datetime_local(deadline_raw)
            if not task.start_at or not task.deadline:
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
        db.session.flush()
        _log_change(task, "created", "Tạo task mới.")
        db.session.commit()
        flash("Đã tạo công việc mới.", "success")
        return redirect(url_for("todo.index"))

    root_tasks = (
        TodoTask.query.filter_by(parent_task_id=None)
        .order_by(TodoTask.is_active.desc(), TodoTask.created_at.desc())
        .all()
    )
    for root in root_tasks:
        root.subtasks.sort(key=lambda s: (s.deadline or s.start_at or s.created_at))

    weekday_map = {k: v for k, v in WEEKDAY_OPTIONS}
    return render_template(
        "todo/index.html",
        tasks=root_tasks,
        weekday_options=WEEKDAY_OPTIONS,
        weekday_map=weekday_map,
    )


@todo_bp.route("/<int:id>/toggle", methods=["POST"])
@login_required
def toggle(id):
    task = TodoTask.query.get_or_404(id)
    task.is_active = not task.is_active
    _log_change(task, "toggled_active", "Kích hoạt" if task.is_active else "Tạm dừng")
    db.session.commit()
    flash("Đã cập nhật trạng thái công việc.", "success")
    return redirect(request.referrer or url_for("todo.index"))


@todo_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    task = TodoTask.query.get_or_404(id)
    task_title = task.title
    task_id = task.id
    db.session.delete(task)
    db.session.commit()
    flash(f"Đã xóa công việc '{task_title}' (ID {task_id}).", "success")
    return redirect(request.referrer or url_for("todo.index"))


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
        return redirect(request.referrer or url_for("todo.board"))
    old_status = task.status
    task.status = new_status
    _log_change(task, "status_changed", f"Trạng thái: {old_status} -> {new_status}")
    db.session.commit()
    return redirect(request.referrer or url_for("todo.board"))


@todo_bp.route("/<int:id>/update", methods=["POST"])
@login_required
def update(id: int):
    """Cập nhật task/subtask và lưu lịch sử thay đổi."""
    task = TodoTask.query.get_or_404(id)
    form_data = request.form.to_dict(flat=True)
    title = (request.form.get("title") or "").strip()
    if not title:
        flash("Tiêu đề không được để trống.", "error")
        return redirect(url_for("todo.index"))

    task_type = (request.form.get("task_type") or task.task_type).strip()
    if task_type not in {"weekly", "deadline"}:
        flash("Loại công việc không hợp lệ.", "error")
        return redirect(url_for("todo.index"))

    changes = _collect_task_changes(task, form_data)
    task.title = title
    task.note = (request.form.get("note") or "").strip() or None
    task.task_type = task_type

    if task_type == "weekly":
        weekday_raw = request.form.get("weekday")
        try:
            weekday = int(weekday_raw)
        except (TypeError, ValueError):
            flash("Vui lòng chọn thứ hợp lệ.", "error")
            return redirect(url_for("todo.index"))
        if weekday < 0 or weekday > 6:
            flash("Giá trị thứ trong tuần không hợp lệ.", "error")
            return redirect(url_for("todo.index"))
        task.weekday = weekday
        task.start_at = None
        task.deadline = None
    else:
        start_at = _parse_datetime_local(request.form.get("start_at"))
        deadline = _parse_datetime_local(request.form.get("deadline"))
        if not start_at or not deadline:
            flash("Task deadline phải có đủ ngày bắt đầu và deadline.", "error")
            return redirect(url_for("todo.index"))
        if start_at > deadline:
            flash("Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc.", "error")
            return redirect(url_for("todo.index"))
        task.start_at = start_at
        task.deadline = deadline
        task.weekday = None
        reminder = request.form.get("reminder_minutes_before", type=int) or task.reminder_minutes_before or 30
        task.reminder_minutes_before = max(reminder, 1)

    if changes:
        _log_change(task, "updated", " | ".join(changes))
    db.session.commit()
    flash("Đã cập nhật công việc.", "success")
    return redirect(url_for("todo.index"))


@todo_bp.route("/<int:id>/subtasks", methods=["POST"])
@login_required
def create_subtask(id: int):
    """Tạo subtask cho một task cha."""
    parent = TodoTask.query.get_or_404(id)
    title = (request.form.get("title") or "").strip()
    if not title:
        flash("Tiêu đề subtask không được để trống.", "error")
        return redirect(url_for("todo.index"))

    start_at = _parse_datetime_local(request.form.get("start_at"))
    deadline = _parse_datetime_local(request.form.get("deadline"))
    if not start_at or not deadline:
        flash("Subtask cần có ngày bắt đầu và deadline.", "error")
        return redirect(url_for("todo.index"))
    if start_at > deadline:
        flash("Ngày bắt đầu subtask phải <= deadline.", "error")
        return redirect(url_for("todo.index"))

    reminder = request.form.get("reminder_minutes_before", type=int) or 30
    subtask = TodoTask(
        title=title,
        note=(request.form.get("note") or "").strip() or None,
        task_type="deadline",
        parent_task_id=parent.id,
        start_at=start_at,
        deadline=deadline,
        reminder_minutes_before=max(reminder, 1),
        is_active=True,
    )
    db.session.add(subtask)
    db.session.flush()
    _log_change(subtask, "created_subtask", f"Tạo subtask cho task #{parent.id} - {parent.title}")
    _log_change(parent, "subtask_added", f"Thêm subtask #{subtask.id} - {subtask.title}")
    db.session.commit()
    flash("Đã tạo subtask.", "success")
    return redirect(url_for("todo.index"))


@todo_bp.route("/<int:id>/history")
@login_required
def history(id: int):
    task = TodoTask.query.get_or_404(id)
    logs = TodoTaskChangeLog.query.filter_by(task_id=task.id).order_by(TodoTaskChangeLog.changed_at.desc()).all()
    return render_template("todo/history.html", task=task, logs=logs)


@todo_bp.route("/<int:id>/manage")
@login_required
def manage(id: int):
    """Trang quản lý chi tiết task/subtask để tránh chật ở danh sách."""
    task = TodoTask.query.get_or_404(id)
    root_task = task.parent_task if task.parent_task else task
    subtasks = sorted(root_task.subtasks, key=lambda s: (s.deadline or s.start_at or s.created_at))
    weekday_map = {k: v for k, v in WEEKDAY_OPTIONS}
    return render_template(
        "todo/manage.html",
        task=root_task,
        subtasks=subtasks,
        weekday_options=WEEKDAY_OPTIONS,
        weekday_map=weekday_map,
    )


@todo_bp.route("/gantt")
@login_required
def gantt():
    tasks = TodoTask.query.filter_by(is_active=True).all()
    task_by_id = {t.id: t for t in tasks}
    children_map: dict[int, list[TodoTask]] = {}
    roots: list[TodoTask] = []
    for task in tasks:
        if task.parent_task_id and task.parent_task_id in task_by_id:
            children_map.setdefault(task.parent_task_id, []).append(task)
        else:
            roots.append(task)
    roots.sort(key=lambda t: (t.deadline or t.start_at or t.created_at))
    for pid in children_map:
        children_map[pid].sort(key=lambda t: (t.deadline or t.start_at or t.created_at))

    view_mode = (request.args.get("view") or "month").lower()
    if view_mode not in {"week", "month", "year", "custom"}:
        view_mode = "month"
    anchor_raw = request.args.get("anchor")
    try:
        anchor_date = datetime.strptime(anchor_raw, "%Y-%m-%d").date() if anchor_raw else datetime.now().date()
    except ValueError:
        anchor_date = datetime.now().date()
    from_raw = request.args.get("from_date")
    to_raw = request.args.get("to_date")
    from_date = None
    to_date = None
    try:
        if from_raw:
            from_date = datetime.strptime(from_raw, "%Y-%m-%d").date()
        if to_raw:
            to_date = datetime.strptime(to_raw, "%Y-%m-%d").date()
    except ValueError:
        from_date = None
        to_date = None

    timeline_start, timeline_end = _timeline_bounds(view_mode, anchor_date, from_date, to_date)
    axis_unit = "month" if view_mode == "year" else "day"
    collapsed_raw = (request.args.get("collapsed") or "").strip()
    collapsed_ids = {
        int(x)
        for x in collapsed_raw.split(",")
        if x.strip().isdigit()
    }
    collapsed_query = ",".join(str(x) for x in sorted(collapsed_ids))

    prepared_rows: list[dict] = []
    spans: list[tuple[datetime, datetime]] = []
    rows_ordered: list[tuple[TodoTask, int]] = []
    for root in roots:
        rows_ordered.append((root, 0))
        if root.id not in collapsed_ids:
            for child in children_map.get(root.id, []):
                rows_ordered.append((child, 1))

    for task, depth in rows_ordered:
        start = task.start_at or task.created_at
        end = task.deadline or start
        if not start or not end:
            continue
        if end < start:
            end = start
        if end < timeline_start or start > timeline_end:
            continue
        spans.append((start, end))
        prepared_rows.append(
            {
                "id": task.id,
                "title": task.title,
                "status": task.status or "backlog",
                "start": start,
                "end": end,
                "start_label": start.strftime("%d/%m/%Y"),
                "end_label": end.strftime("%d/%m/%Y"),
                "depth": depth,
                "parent_task_id": task.parent_task_id,
            }
        )

    if not spans:
        return render_template(
            "todo/gantt.html",
            gantt_rows=[],
            day_headers=[],
            month_groups=[],
            total_days=0,
            connectors=[],
            row_height=44,
            view_mode=view_mode,
            anchor_date=anchor_date.strftime("%Y-%m-%d"),
            from_date=(from_date.strftime("%Y-%m-%d") if from_date else ""),
            to_date=(to_date.strftime("%Y-%m-%d") if to_date else ""),
            collapsed_ids=collapsed_ids,
            collapsed_query=collapsed_query,
            toggle_urls={},
        )

    day_headers: list[dict] = []
    month_groups: list[dict] = []
    if axis_unit == "day":
        total_units = max((timeline_end.date() - timeline_start.date()).days + 1, 1)
        current_month_key = None
        weekday_short = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        for i in range(total_units):
            day = (timeline_start + timedelta(days=i)).date()
            day_headers.append(
                {
                    "weekday": weekday_short[day.weekday()],
                    "date": day.strftime("%d/%m"),
                    "is_weekend": day.weekday() >= 5,
                }
            )
            month_key = (day.year, day.month)
            month_label = day.strftime("%B %Y")
            if current_month_key != month_key:
                month_groups.append({"label": month_label, "span": 0})
                current_month_key = month_key
            month_groups[-1]["span"] += 1
    else:
        total_units = 12
        for m in range(1, 13):
            month_date = date(anchor_date.year, m, 1)
            day_headers.append(
                {
                    "weekday": f"Q{((m - 1) // 3) + 1}",
                    "date": month_date.strftime("%b"),
                    "is_weekend": False,
                }
            )
        month_groups = [{"label": str(anchor_date.year), "span": 12}]

    gantt_rows: list[dict] = []
    row_index_by_task: dict[int, int] = {}
    bar_by_task: dict[int, dict] = {}
    for row in prepared_rows:
        start = max(row["start"], timeline_start)
        end = min(row["end"], timeline_end)
        if axis_unit == "day":
            # Căn theo ngày để thanh timeline không bị lệch ngày do timezone/giờ.
            start_offset = (start.date() - timeline_start.date()).days
            duration = max((end.date() - start.date()).days + 1, 1)
        else:
            start_offset = (start.year - anchor_date.year) * 12 + (start.month - 1)
            end_offset = (end.year - anchor_date.year) * 12 + end.month
            duration = max(end_offset - start_offset, 0.35)

        left_pct = (start_offset / total_units) * 100
        width_pct = (duration / total_units) * 100
        row_data = {
            **row,
            "left_pct": round(left_pct, 3),
            "width_pct": round(width_pct, 3),
            "end_pct": round(left_pct + width_pct, 3),
            "is_subtask": row.get("depth", 0) > 0,
            "is_parent": row["id"] in children_map,
        }
        row_index_by_task[row["id"]] = len(gantt_rows)
        bar_by_task[row["id"]] = row_data
        gantt_rows.append(row_data)

    connectors: list[dict] = []
    for row in gantt_rows:
        parent_id = row.get("parent_task_id")
        if not parent_id:
            continue
        parent = bar_by_task.get(parent_id)
        if not parent:
            continue
        p_idx = row_index_by_task.get(parent_id)
        c_idx = row_index_by_task.get(row["id"])
        if p_idx is None or c_idx is None:
            continue
        connectors.append(
            {
                "x1": min(max(parent["end_pct"], 0), 100),
                "x2": min(max(row["left_pct"], 0), 100),
                "from_row": p_idx,
                "to_row": c_idx,
                "from_task_id": parent["id"],
                "to_task_id": row["id"],
            }
        )

    query_base = {
        "view": view_mode,
        "anchor": anchor_date.strftime("%Y-%m-%d"),
        "from_date": from_date.strftime("%Y-%m-%d") if from_date else "",
        "to_date": to_date.strftime("%Y-%m-%d") if to_date else "",
    }
    toggle_urls: dict[int, str] = {}
    parent_ids = [t.id for t in roots if t.id in children_map]
    for pid in parent_ids:
        next_set = set(collapsed_ids)
        if pid in next_set:
            next_set.remove(pid)
        else:
            next_set.add(pid)
        args = dict(query_base)
        args["collapsed"] = ",".join(str(x) for x in sorted(next_set))
        toggle_urls[pid] = url_for("todo.gantt", **args)

    return render_template(
        "todo/gantt.html",
        gantt_rows=gantt_rows,
        day_headers=day_headers,
        month_groups=month_groups,
        total_days=total_units,
        connectors=connectors,
        row_height=44,
        view_mode=view_mode,
        anchor_date=anchor_date.strftime("%Y-%m-%d"),
        from_date=(from_date.strftime("%Y-%m-%d") if from_date else ""),
        to_date=(to_date.strftime("%Y-%m-%d") if to_date else ""),
        collapsed_ids=collapsed_ids,
        collapsed_query=collapsed_query,
        toggle_urls=toggle_urls,
    )
