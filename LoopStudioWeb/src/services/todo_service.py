"""Dịch vụ Todo: lọc công việc hôm nay và format nội dung gửi Telegram."""
from datetime import datetime

from ..models import TodoTask

WEEKDAY_NAMES = [
    "Thứ 2",
    "Thứ 3",
    "Thứ 4",
    "Thứ 5",
    "Thứ 6",
    "Thứ 7",
    "Chủ nhật",
]


def get_today_todos(now: datetime | None = None) -> tuple[list[TodoTask], list[TodoTask]]:
    """Trả về (weekly_tasks_hom_nay, deadline_tasks_hom_nay)."""
    now = now or datetime.now()
    today = now.date()
    weekday = today.weekday()

    tasks = TodoTask.query.filter_by(is_active=True).all()
    weekly_tasks = []
    deadline_tasks = []

    for task in tasks:
        if task.task_type == "weekly" and task.weekday == weekday:
            weekly_tasks.append(task)
            continue
        if (
            task.task_type == "deadline"
            and task.deadline
            and (
                (task.start_at and task.start_at.date() <= today <= task.deadline.date())
                or (not task.start_at and task.deadline.date() == today)
            )
        ):
            deadline_tasks.append(task)

    weekly_tasks.sort(key=lambda t: (t.title or "").lower())
    deadline_tasks.sort(key=lambda t: t.deadline)
    return weekly_tasks, deadline_tasks


def build_today_todo_message(now: datetime | None = None) -> str:
    """Format danh sách công việc hôm nay để gửi Telegram/bot."""
    now = now or datetime.now()
    weekly_tasks, deadline_tasks = get_today_todos(now)

    lines = [
        "━━━━━━━━━━━━━━━━━━",
        "🌤️ BẢNG TODO HÔM NAY",
        "━━━━━━━━━━━━━━━━━━",
        f"📅 Ngày: {now.strftime('%d/%m/%Y')}",
    ]
    if not weekly_tasks and not deadline_tasks:
        lines.append("\n✅ Tuyệt vời! Hôm nay không có công việc nào cần xử lý.")
        return "\n".join(lines)

    if weekly_tasks:
        lines.append("\n🔁 Công việc lặp theo tuần:")
        for idx, task in enumerate(weekly_tasks, start=1):
            lines.append(f"{idx:02d}. {task.title}")
            if task.note:
                lines.append(f"    📝 {task.note}")

    if deadline_tasks:
        lines.append("\n⏰ Công việc theo deadline:")
        for idx, task in enumerate(deadline_tasks, start=1):
            from_str = task.start_at.strftime("%d/%m")
            to_str = task.deadline.strftime("%d/%m %H:%M")
            lines.append(f"{idx:02d}. {task.title}")
            lines.append(f"    ⏳ {from_str} -> {to_str}")
            if task.note:
                lines.append(f"    📝 {task.note}")

    lines.append("\n💡 Mẹo: Ưu tiên xử lý các mục deadline trước.")

    return "\n".join(lines)


def get_today_todo_timeline(now: datetime | None = None) -> list[dict]:
    """Dữ liệu timeline hiển thị trên dashboard."""
    now = now or datetime.now()
    weekly_tasks, deadline_tasks = get_today_todos(now)

    items = []
    for task in weekly_tasks:
        items.append(
            {
                "title": task.title,
                "time_label": "Trong ngày",
                "kind": "weekly",
                "note": task.note,
            }
        )
    for task in deadline_tasks:
        items.append(
            {
                "title": task.title,
                "time_label": task.deadline.strftime("%H:%M"),
                "kind": "deadline",
                "note": task.note,
            }
        )

    # deadline ưu tiên lên trước theo giờ gần nhất
    items.sort(key=lambda x: (0 if x["kind"] == "deadline" else 1, x["time_label"]))
    return items
