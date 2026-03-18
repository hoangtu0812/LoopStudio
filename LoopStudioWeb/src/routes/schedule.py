"""Quản lý thời khóa biểu - tạo, sửa, check-in, task."""
from datetime import datetime, date, time, timedelta

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy import func

from ..app import db
from ..models import Schedule, ScheduleSession, CheckIn, Task, NotificationConfig, TelegramChatTarget

schedule_bp = Blueprint("schedule", __name__)

DAY_NAMES = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]


def _generate_sessions(schedule: Schedule) -> list[ScheduleSession]:
    """Sinh các buổi học từ schedule."""
    sessions = []
    current = schedule.start_date
    while current <= schedule.end_date:
        if current.weekday() == schedule.day_of_week:
            sessions.append(
                ScheduleSession(
                    schedule_id=schedule.id,
                    session_date=current,
                    start_time=schedule.start_time,
                    end_time=schedule.end_time,
                )
            )
        current += timedelta(days=1)
    return sessions


@schedule_bp.route("/")
@login_required
def index():
    schedules = Schedule.query.order_by(Schedule.start_date).all()
    return render_template("schedule/index.html", schedules=schedules, day_names=DAY_NAMES)


@schedule_bp.route("/dashboard")
@login_required
def dashboard():
    sessions = ScheduleSession.query.order_by(ScheduleSession.session_date.asc()).all()
    week_stats: dict[str, dict[str, int]] = {}
    subject_stats: dict[str, dict[str, int]] = {}
    for session in sessions:
        year, week, _ = session.session_date.isocalendar()
        week_key = f"{year}-W{week:02d}"
        if week_key not in week_stats:
            week_stats[week_key] = {"total": 0, "checked": 0}
        week_stats[week_key]["total"] += 1
        week_stats[week_key]["checked"] += 1 if session.check_ins else 0

        subject_name = session.schedule.name
        if subject_name not in subject_stats:
            subject_stats[subject_name] = {"total": 0, "checked": 0}
        subject_stats[subject_name]["total"] += 1
        subject_stats[subject_name]["checked"] += 1 if session.check_ins else 0

    week_labels = sorted(week_stats.keys())[-12:]
    week_rates = []
    for wk in week_labels:
        total = week_stats[wk]["total"]
        checked = week_stats[wk]["checked"]
        week_rates.append(round((checked / total) * 100, 1) if total else 0)

    subject_items = []
    for subject, values in subject_stats.items():
        total = values["total"]
        checked = values["checked"]
        subject_items.append((subject, round((checked / total) * 100, 1) if total else 0))
    subject_items.sort(key=lambda x: x[1], reverse=True)
    subject_labels = [x[0] for x in subject_items[:10]]
    subject_rates = [x[1] for x in subject_items[:10]]

    total_all = sum(v["total"] for v in week_stats.values())
    checked_all = sum(v["checked"] for v in week_stats.values())
    overall_rate = round((checked_all / total_all) * 100, 1) if total_all else 0
    upcoming_sessions = ScheduleSession.query.filter(
        ScheduleSession.session_date >= date.today()
    ).count()
    checked_today = (
        db.session.query(func.count(CheckIn.id))
        .join(ScheduleSession, CheckIn.session_id == ScheduleSession.id)
        .filter(ScheduleSession.session_date == date.today())
        .scalar()
        or 0
    )

    return render_template(
        "schedule/dashboard.html",
        week_labels=week_labels,
        week_rates=week_rates,
        subject_labels=subject_labels,
        subject_rates=subject_rates,
        overall_rate=overall_rate,
        total_sessions=total_all,
        checked_sessions=checked_all,
        upcoming_sessions=upcoming_sessions,
        checked_today=checked_today,
    )


@schedule_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        name = request.form.get("name")
        day_of_week = int(request.form.get("day_of_week", 0))
        start_time = datetime.strptime(request.form.get("start_time", "18:00"), "%H:%M").time()
        end_time = datetime.strptime(request.form.get("end_time", "21:00"), "%H:%M").time()
        start_date = datetime.strptime(request.form.get("start_date"), "%Y-%m-%d").date()
        end_date = datetime.strptime(request.form.get("end_date"), "%Y-%m-%d").date()
        schedule = Schedule(
            name=name,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            start_date=start_date,
            end_date=end_date,
        )
        db.session.add(schedule)
        db.session.commit()
        for s in _generate_sessions(schedule):
            db.session.add(s)
        db.session.commit()
        flash("Đã tạo thời khóa biểu.", "success")
        return redirect(url_for("schedule.index"))
    return render_template("schedule/form.html", schedule=None, day_names=DAY_NAMES)


@schedule_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    schedule = Schedule.query.get_or_404(id)
    if request.method == "POST":
        schedule.name = request.form.get("name")
        schedule.day_of_week = int(request.form.get("day_of_week", 0))
        schedule.start_time = datetime.strptime(request.form.get("start_time", "18:00"), "%H:%M").time()
        schedule.end_time = datetime.strptime(request.form.get("end_time", "21:00"), "%H:%M").time()
        schedule.start_date = datetime.strptime(request.form.get("start_date"), "%Y-%m-%d").date()
        schedule.end_date = datetime.strptime(request.form.get("end_date"), "%Y-%m-%d").date()
        for s in schedule.sessions:
            db.session.delete(s)
        for s in _generate_sessions(schedule):
            db.session.add(s)
        db.session.commit()
        flash("Đã cập nhật. Lưu ý: các buổi cũ đã bị xóa và tạo lại.", "success")
        return redirect(url_for("schedule.index"))
    return render_template("schedule/form.html", schedule=schedule, day_names=DAY_NAMES)


@schedule_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    schedule = Schedule.query.get_or_404(id)
    db.session.delete(schedule)
    db.session.commit()
    flash("Đã xóa.", "success")
    return redirect(url_for("schedule.index"))


@schedule_bp.route("/<int:id>/sessions")
@login_required
def schedule_sessions(id):
    schedule = Schedule.query.get_or_404(id)
    sessions = ScheduleSession.query.filter_by(schedule_id=id).order_by(
        ScheduleSession.session_date, ScheduleSession.start_time
    ).all()
    return render_template("schedule/sessions.html", schedule=schedule, sessions=sessions)


@schedule_bp.route("/session/<int:id>")
@login_required
def session_detail(id):
    session = ScheduleSession.query.get_or_404(id)
    configs = NotificationConfig.query.filter(
        NotificationConfig.enabled == True,  # noqa: E712
    ).all()
    target_map = {
        t.id: t
        for t in TelegramChatTarget.query.filter(
            TelegramChatTarget.is_active == True  # noqa: E712
        ).all()
    }
    telegram_targets = []
    for cfg in configs:
        resolved_chat_id = (target_map.get(cfg.chat_target_id).chat_id if cfg.chat_target_id in target_map else cfg.chat_id) or ""
        resolved_chat_id = resolved_chat_id.strip()
        if not resolved_chat_id:
            continue
        label = target_map.get(cfg.chat_target_id).label if cfg.chat_target_id in target_map else cfg.config_type
        telegram_targets.append({"chat_id": resolved_chat_id, "label": label, "config_type": cfg.config_type})
    return render_template(
        "schedule/session.html",
        session=session,
        telegram_targets=telegram_targets,
    )


@schedule_bp.route("/session/<int:id>/checkin", methods=["POST"])
@login_required
def checkin(id):
    session = ScheduleSession.query.get_or_404(id)
    if not session.check_ins:
        db.session.add(CheckIn(session_id=session.id))
        db.session.commit()
        flash("Đã check-in thành công.", "success")
    return redirect(url_for("schedule.session_detail", id=id))


@schedule_bp.route("/session/<int:id>/task", methods=["POST"])
@login_required
def add_task(id):
    session = ScheduleSession.query.get_or_404(id)
    title = request.form.get("title")
    deadline_str = request.form.get("deadline")
    deadline = deadline_str and datetime.strptime(deadline_str, "%Y-%m-%dT%H:%M") or None
    db.session.add(Task(session_id=session.id, title=title, deadline=deadline))
    db.session.commit()
    flash("Đã thêm task.", "success")
    return redirect(url_for("schedule.session_detail", id=id))


@schedule_bp.route("/task/<int:id>/done", methods=["POST"])
@login_required
def task_done(id):
    task = Task.query.get_or_404(id)
    task.done = not task.done
    db.session.commit()
    return redirect(url_for("schedule.session_detail", id=task.session_id))


@schedule_bp.route("/session/<int:id>/task/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(id, task_id):
    task = Task.query.get_or_404(task_id)
    if task.session_id != id:
        return redirect(url_for("schedule.index"))
    db.session.delete(task)
    db.session.commit()
    flash("Đã xóa task.", "success")
    return redirect(url_for("schedule.session_detail", id=id))


@schedule_bp.route("/session/<int:id>/notify", methods=["POST"])
@login_required
def notify_session(id):
    """Gửi thông báo thủ công tới các Telegram chat đã cấu hình."""
    session = ScheduleSession.query.get_or_404(id)

    configs = NotificationConfig.query.filter(
        NotificationConfig.enabled == True,  # noqa: E712
    ).all()
    target_map = {
        t.id: t.chat_id
        for t in TelegramChatTarget.query.filter(
            TelegramChatTarget.is_active == True  # noqa: E712
        ).all()
    }
    chat_ids = sorted(
        {
            (target_map.get(c.chat_target_id) or c.chat_id or "").strip()
            for c in configs
            if (target_map.get(c.chat_target_id) or c.chat_id or "").strip()
        }
    )
    if not chat_ids:
        flash("Chưa có chat Telegram nào được bật trong cấu hình thông báo.", "warning")
        return redirect(url_for("schedule.session_detail", id=id))

    from ..services.telegram_service import send_telegram_message
    from ..services.schedule_notifier import build_schedule_reminder_message

    payload = build_schedule_reminder_message(session)

    sent_ok = 0
    for chat_id in chat_ids:
        if send_telegram_message(chat_id, payload):
            sent_ok += 1
    sent_fail = len(chat_ids) - sent_ok

    if sent_ok and sent_fail:
        flash(f"Đã gửi thành công {sent_ok}/{len(chat_ids)} chat Telegram.", "warning")
    elif sent_ok:
        flash(f"Đã gửi thông báo tới {sent_ok} chat Telegram.", "success")
    else:
        flash("Gửi thất bại. Kiểm tra BOT_TOKEN hoặc Chat ID.", "error")
    return redirect(url_for("schedule.session_detail", id=id))


@schedule_bp.route("/notifications", methods=["GET", "POST"])
@login_required
def notifications():
    flash("Cấu hình Telegram đã chuyển sang Bot Admin.", "info")
    return redirect(url_for("bot_admin.notifications"))
