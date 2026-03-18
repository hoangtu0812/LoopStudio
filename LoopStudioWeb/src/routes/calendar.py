"""Calendar chung: xem sự kiện theo tuần/tháng/năm và tạo/sửa/xóa meeting."""
from calendar import monthrange
from datetime import date, datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..app import db
from ..models import CalendarEvent, NotificationConfig, TelegramChatTarget
from ..services.calendar_service import collect_events
from ..services.telegram_service import send_telegram_message

calendar_bp = Blueprint("calendar", __name__)

VIEW_MODES = {"week", "month", "year"}
DAY_START_HOUR = 6
DAY_END_HOUR = 22


def _parse_anchor(day_param: str | None) -> date:
    try:
        return datetime.strptime(day_param, "%Y-%m-%d").date() if day_param else date.today()
    except ValueError:
        return date.today()


def _week_range(anchor: date) -> tuple[date, date]:
    start = anchor - timedelta(days=anchor.weekday())
    end = start + timedelta(days=6)
    return start, end


def _month_range(anchor: date) -> tuple[date, date]:
    start = anchor.replace(day=1)
    end = anchor.replace(day=monthrange(anchor.year, anchor.month)[1])
    return start, end


def _year_range(anchor: date) -> tuple[date, date]:
    start = date(anchor.year, 1, 1)
    end = date(anchor.year, 12, 31)
    return start, end


def _calc_nav(anchor: date, view_mode: str) -> tuple[date, date]:
    if view_mode == "week":
        return anchor - timedelta(days=7), anchor + timedelta(days=7)
    if view_mode == "month":
        y, m = anchor.year, anchor.month
        prev_m = 12 if m == 1 else m - 1
        prev_y = y - 1 if m == 1 else y
        next_m = 1 if m == 12 else m + 1
        next_y = y + 1 if m == 12 else y
        prev_day = min(anchor.day, monthrange(prev_y, prev_m)[1])
        next_day = min(anchor.day, monthrange(next_y, next_m)[1])
        return date(prev_y, prev_m, prev_day), date(next_y, next_m, next_day)
    return date(anchor.year - 1, anchor.month, anchor.day), date(anchor.year + 1, anchor.month, anchor.day)


def _status_class(status: str) -> str:
    if status == "done":
        return "bg-emerald-500/90"
    if status == "doing":
        return "bg-amber-500/90"
    return "bg-sky-500/90"


def _event_chip_class(event_type: str) -> str:
    if event_type == "class":
        return "border-blue-300/70 bg-blue-500/95"
    if event_type == "todo":
        return "border-amber-300/70 bg-amber-500/95"
    return "border-cyan-300/70 bg-cyan-500/95"


def _notify_calendar_created(event: CalendarEvent) -> None:
    """Gửi thông báo Telegram khi tạo event từ Calendar."""
    configs = NotificationConfig.query.filter(
        NotificationConfig.enabled == True,  # noqa: E712
        NotificationConfig.config_type == "calendar_event_notify",
    ).all()
    target_map = {
        t.id: t.chat_id
        for t in TelegramChatTarget.query.filter(
            TelegramChatTarget.is_active == True  # noqa: E712
        ).all()
    }
    chat_ids = sorted(
        {
            (target_map.get(cfg.chat_target_id) or cfg.chat_id or "").strip()
            for cfg in configs
            if (target_map.get(cfg.chat_target_id) or cfg.chat_id or "").strip()
        }
    )
    if not chat_ids:
        return

    description = (event.description or "").strip()
    message = (
        "🗓️ *Sự kiện mới trên Calendar*\n"
        f"- Tiêu đề: *{event.title}*\n"
        f"- Loại: `{event.event_type}`\n"
        f"- Bắt đầu: `{event.start_at.strftime('%d/%m/%Y %H:%M')}`\n"
        f"- Kết thúc: `{event.end_at.strftime('%d/%m/%Y %H:%M')}`\n"
    )
    if description:
        message += f"- Mô tả: {description}"

    for chat_id in chat_ids:
        send_telegram_message(chat_id, message)


def _context_redirect(anchor: date, view_mode: str, edit_id: int | None = None):
    params = {"d": anchor.isoformat(), "view": view_mode}
    if edit_id:
        params["edit"] = edit_id
    return redirect(url_for("calendar.index", **params))


def _apply_week_layout(day_events: list[dict], minute_span: int, day_start_minutes: int, day_end_minutes: int) -> list[dict]:
    """Tính vị trí và lane theo overlap để block dễ nhìn hơn."""
    prepared: list[dict] = []
    for e in day_events:
        start_minutes = e["start_at"].hour * 60 + e["start_at"].minute
        end_minutes = e["end_at"].hour * 60 + e["end_at"].minute
        s = max(start_minutes, day_start_minutes)
        en = min(max(end_minutes, s + 20), day_end_minutes)
        top_pct = ((s - day_start_minutes) / minute_span) * 100
        height_pct = max(((en - s) / minute_span) * 100, 4)
        prepared.append(
            {
                **e,
                "_start_minutes": s,
                "_end_minutes": en,
                "top_pct": round(top_pct, 3),
                "height_pct": round(height_pct, 3),
                "status_class": _status_class(e["status"]),
                "chip_class": _event_chip_class(e["event_type"]),
            }
        )

    prepared.sort(key=lambda x: (x["_start_minutes"], x["_end_minutes"], x["title"].lower()))
    lane_end_times: list[int] = []
    for ev in prepared:
        lane_index = None
        for i, lane_end in enumerate(lane_end_times):
            if lane_end <= ev["_start_minutes"]:
                lane_index = i
                lane_end_times[i] = ev["_end_minutes"]
                break
        if lane_index is None:
            lane_index = len(lane_end_times)
            lane_end_times.append(ev["_end_minutes"])
        ev["_lane_index"] = lane_index

    lane_count = max(len(lane_end_times), 1)
    for ev in prepared:
        ev["lane_left_pct"] = round((ev["_lane_index"] / lane_count) * 100, 3)
        ev["lane_width_pct"] = round(100 / lane_count, 3)
    return prepared


@calendar_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    view_mode = (request.args.get("view") or "week").lower()
    if view_mode not in VIEW_MODES:
        view_mode = "week"
    anchor = _parse_anchor(request.args.get("d"))

    edit_id = request.args.get("edit", type=int)
    edit_event = CalendarEvent.query.get(edit_id) if edit_id else None

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        event_type = (request.form.get("event_type") or "meeting").strip()
        start_raw = request.form.get("start_at")
        end_raw = request.form.get("end_at")

        if not title or not start_raw or not end_raw:
            flash("Vui lòng nhập đủ tiêu đề, thời gian bắt đầu và kết thúc.", "error")
            return _context_redirect(anchor, view_mode, edit_id=edit_id)

        try:
            start_at = datetime.strptime(start_raw, "%Y-%m-%dT%H:%M")
            end_at = datetime.strptime(end_raw, "%Y-%m-%dT%H:%M")
        except ValueError:
            flash("Định dạng thời gian không hợp lệ.", "error")
            return _context_redirect(anchor, view_mode, edit_id=edit_id)

        if end_at < start_at:
            flash("Thời gian kết thúc phải sau thời gian bắt đầu.", "error")
            return _context_redirect(anchor, view_mode, edit_id=edit_id)

        event = CalendarEvent(
            title=title,
            description=description or None,
            event_type=event_type or "meeting",
            start_at=start_at,
            end_at=end_at,
            all_day=False,
            status="planned",
        )
        db.session.add(event)
        db.session.commit()
        _notify_calendar_created(event)
        flash("Đã tạo sự kiện mới.", "success")
        return _context_redirect(anchor, view_mode)

    if view_mode == "week":
        range_start, range_end = _week_range(anchor)
    elif view_mode == "month":
        range_start, range_end = _month_range(anchor)
    else:
        range_start, range_end = _year_range(anchor)

    start_dt = datetime.combine(range_start, datetime.min.time())
    end_dt = datetime.combine(range_end, datetime.max.time())
    events = collect_events(start_dt, end_dt)

    # Sự kiện hôm nay luôn dùng cho block tóm tắt
    today_iso = date.today().isoformat()
    today_events = [e for e in events if e["start_at"].date().isoformat() == today_iso]

    prev_anchor, next_anchor = _calc_nav(anchor, view_mode)

    # Dữ liệu cho WEEK view: mỗi ngày có lane giờ với block theo thời lượng
    week_days: list[date] = []
    week_day_columns: list[dict] = []
    if view_mode == "week":
        week_days = [range_start + timedelta(days=i) for i in range(7)]
        minute_span = (DAY_END_HOUR - DAY_START_HOUR) * 60
        day_start_minutes = DAY_START_HOUR * 60
        day_end_minutes = DAY_END_HOUR * 60
        for d in week_days:
            day_events = [e for e in events if e["start_at"].date() == d]
            week_day_columns.append(
                {
                    "date": d,
                    "events": _apply_week_layout(
                        day_events=day_events,
                        minute_span=minute_span,
                        day_start_minutes=day_start_minutes,
                        day_end_minutes=day_end_minutes,
                    ),
                }
            )

    # Dữ liệu cho MONTH view: grid ngày
    month_cells: list[dict] = []
    if view_mode == "month":
        first_day = range_start
        grid_start = first_day - timedelta(days=first_day.weekday())
        for i in range(42):
            d = grid_start + timedelta(days=i)
            day_events = [e for e in events if e["start_at"].date() == d]
            month_cells.append(
                {
                    "date": d,
                    "in_month": d.month == anchor.month,
                    "events": day_events[:4],
                    "more_count": max(len(day_events) - 4, 0),
                }
            )

    # Dữ liệu cho YEAR view: tổng hợp theo tháng
    year_months: list[dict] = []
    if view_mode == "year":
        for m in range(1, 13):
            month_start = date(anchor.year, m, 1)
            month_end = date(anchor.year, m, monthrange(anchor.year, m)[1])
            month_events = [
                e for e in events
                if month_start <= e["start_at"].date() <= month_end
            ]
            type_counts: dict[str, int] = {}
            for e in month_events:
                type_counts[e["event_type"]] = type_counts.get(e["event_type"], 0) + 1
            year_months.append(
                {
                    "month": month_start.strftime("%B"),
                    "event_count": len(month_events),
                    "type_counts": type_counts,
                }
            )

    return render_template(
        "calendar/index.html",
        view_mode=view_mode,
        anchor=anchor,
        prev_anchor=prev_anchor,
        next_anchor=next_anchor,
        today_iso=today_iso,
        week_days=week_days,
        week_day_columns=week_day_columns,
        month_cells=month_cells,
        year_months=year_months,
        today_events=today_events,
        day_start_hour=DAY_START_HOUR,
        day_end_hour=DAY_END_HOUR,
        edit_event=edit_event,
    )


@calendar_bp.route("/event/<int:id>/update", methods=["POST"])
@login_required
def update_event(id):
    view_mode = (request.args.get("view") or "week").lower()
    if view_mode not in VIEW_MODES:
        view_mode = "week"
    anchor = _parse_anchor(request.args.get("d"))

    event = CalendarEvent.query.get_or_404(id)
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    event_type = (request.form.get("event_type") or "meeting").strip()
    start_raw = request.form.get("start_at")
    end_raw = request.form.get("end_at")

    if not title or not start_raw or not end_raw:
        flash("Vui lòng nhập đủ tiêu đề, thời gian bắt đầu và kết thúc.", "error")
        return _context_redirect(anchor, view_mode, edit_id=id)

    try:
        start_at = datetime.strptime(start_raw, "%Y-%m-%dT%H:%M")
        end_at = datetime.strptime(end_raw, "%Y-%m-%dT%H:%M")
    except ValueError:
        flash("Định dạng thời gian không hợp lệ.", "error")
        return _context_redirect(anchor, view_mode, edit_id=id)

    if end_at < start_at:
        flash("Thời gian kết thúc phải sau thời gian bắt đầu.", "error")
        return _context_redirect(anchor, view_mode, edit_id=id)

    event.title = title
    event.description = description or None
    event.event_type = event_type or "meeting"
    event.start_at = start_at
    event.end_at = end_at
    db.session.commit()
    flash("Đã cập nhật sự kiện.", "success")
    return _context_redirect(anchor, view_mode)


@calendar_bp.route("/event/<int:id>/delete", methods=["POST"])
@login_required
def delete_event(id):
    view_mode = (request.args.get("view") or "week").lower()
    if view_mode not in VIEW_MODES:
        view_mode = "week"
    anchor = _parse_anchor(request.args.get("d"))

    event = CalendarEvent.query.get_or_404(id)
    db.session.delete(event)
    db.session.commit()
    flash("Đã xóa sự kiện.", "success")
    return _context_redirect(anchor, view_mode)

