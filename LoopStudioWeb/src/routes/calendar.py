"""Calendar chung: xem sự kiện tuần và tạo meeting."""
from datetime import date, datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..app import db
from ..models import CalendarEvent
from ..services.calendar_service import collect_events

calendar_bp = Blueprint("calendar", __name__)


@calendar_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        event_type = (request.form.get("event_type") or "meeting").strip()
        start_raw = request.form.get("start_at")
        end_raw = request.form.get("end_at")

        if not title or not start_raw or not end_raw:
            flash("Vui lòng nhập đủ tiêu đề, thời gian bắt đầu và kết thúc.", "error")
            return redirect(url_for("calendar.index"))

        try:
            start_at = datetime.strptime(start_raw, "%Y-%m-%dT%H:%M")
            end_at = datetime.strptime(end_raw, "%Y-%m-%dT%H:%M")
        except ValueError:
            flash("Định dạng thời gian không hợp lệ.", "error")
            return redirect(url_for("calendar.index"))

        if end_at < start_at:
            flash("Thời gian kết thúc phải sau thời gian bắt đầu.", "error")
            return redirect(url_for("calendar.index"))

        db.session.add(
            CalendarEvent(
                title=title,
                description=description or None,
                event_type=event_type or "meeting",
                start_at=start_at,
                end_at=end_at,
                all_day=False,
                status="planned",
            )
        )
        db.session.commit()
        flash("Đã tạo sự kiện mới.", "success")
        return redirect(url_for("calendar.index", d=start_at.date().isoformat()))

    # Chọn mốc ngày hiện tại để render tuần
    day_param = request.args.get("d")
    try:
        anchor = datetime.strptime(day_param, "%Y-%m-%d").date() if day_param else date.today()
    except ValueError:
        anchor = date.today()

    week_start = anchor - timedelta(days=anchor.weekday())
    week_days = [week_start + timedelta(days=i) for i in range(7)]

    start_dt = datetime.combine(week_days[0], datetime.min.time())
    end_dt = datetime.combine(week_days[-1], datetime.max.time())
    week_events = collect_events(start_dt, end_dt)

    events_by_day: dict[str, list[dict]] = {d.isoformat(): [] for d in week_days}
    for e in week_events:
        k = e["start_at"].date().isoformat()
        if k in events_by_day:
            events_by_day[k].append(e)

    today_events = events_by_day.get(date.today().isoformat(), [])
    return render_template(
        "calendar/index.html",
        week_days=week_days,
        events_by_day=events_by_day,
        anchor=anchor,
        today_events=today_events,
    )

