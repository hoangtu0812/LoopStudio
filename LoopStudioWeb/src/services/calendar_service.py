"""Service tổng hợp sự kiện từ schedule, todo và calendar_events."""
from datetime import date, datetime, time, timedelta

from ..models import CalendarEvent, ScheduleSession, TodoTask


def _event(
    title: str,
    event_type: str,
    start_at: datetime,
    end_at: datetime,
    status: str = "planned",
    source_url: str | None = None,
    description: str | None = None,
    event_id: int | None = None,
) -> dict:
    return {
        "title": title,
        "event_type": event_type,
        "start_at": start_at,
        "end_at": end_at,
        "status": status,
        "source_url": source_url,
        "description": description,
        "event_id": event_id,
    }


def collect_events(start_dt: datetime, end_dt: datetime) -> list[dict]:
    """Gom toàn bộ sự kiện trong khoảng thời gian."""
    events: list[dict] = []
    start_day = start_dt.date()
    end_day = end_dt.date()

    # 1) Schedule sessions
    sessions = ScheduleSession.query.filter(
        ScheduleSession.session_date >= start_day,
        ScheduleSession.session_date <= end_day,
    ).all()
    for s in sessions:
        st = datetime.combine(s.session_date, s.start_time)
        et = datetime.combine(s.session_date, s.end_time)
        events.append(
            _event(
                title=s.schedule.name,
                event_type="class",
                start_at=st,
                end_at=et,
                status="done" if s.check_ins else "planned",
                source_url=f"/schedule/session/{s.id}",
            )
        )

    # 2) Todo tasks
    todo_tasks = TodoTask.query.filter_by(is_active=True).all()
    total_days = (end_day - start_day).days
    for t in todo_tasks:
        if t.task_type == "weekly" and t.weekday is not None:
            for i in range(total_days + 1):
                d = start_day + timedelta(days=i)
                if d.weekday() == t.weekday:
                    st = datetime.combine(d, time(9, 0))
                    et = datetime.combine(d, time(10, 0))
                    events.append(
                        _event(
                            title=t.title,
                            event_type="todo",
                            start_at=st,
                            end_at=et,
                            status=t.status or "planned",
                            source_url="/todo/",
                            description=t.note,
                        )
                    )
        # TODO deadline dạng từ ngày-đến ngày không hiển thị trên Calendar chung.

    # 3) Calendar events (meeting/custom)
    custom_events = CalendarEvent.query.filter(
        CalendarEvent.end_at >= start_dt,
        CalendarEvent.start_at <= end_dt,
    ).all()
    for e in custom_events:
        events.append(
            _event(
                title=e.title,
                event_type=e.event_type,
                start_at=e.start_at,
                end_at=e.end_at,
                status=e.status or "planned",
                source_url="/calendar/",
                description=e.description,
                event_id=e.id,
            )
        )

    events.sort(key=lambda x: (x["start_at"], x["title"].lower()))
    return events


def collect_events_for_day(target_day: date) -> list[dict]:
    start = datetime.combine(target_day, time.min)
    end = datetime.combine(target_day, time.max)
    return collect_events(start, end)

