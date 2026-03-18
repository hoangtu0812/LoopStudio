"""Dashboard tổng hợp đa ứng dụng."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from ..app import db
from ..models import BotAccessLog, CafeOrder, ScheduleSession, TodoTask

admin_dashboard_bp = Blueprint("admin_dashboard", __name__)


@admin_dashboard_bp.route("/")
@login_required
def index():
    if not current_user.is_admin:
        flash("Bạn không có quyền truy cập.", "error")
        return redirect(url_for("main.dashboard"))

    # Learning snapshot (đã chuyển dashboard chi tiết về schedule.dashboard)
    total_sessions = ScheduleSession.query.count()
    checked_sessions = sum(1 for s in ScheduleSession.query.all() if s.check_ins)
    overall_rate = round((checked_sessions / total_sessions) * 100, 1) if total_sessions else 0

    # Todo snapshot
    todo_active = TodoTask.query.filter(TodoTask.is_active == True).count()  # noqa: E712
    todo_status_counts = {"backlog": 0, "doing": 0, "done": 0}
    for status, count in (
        TodoTask.query.with_entities(TodoTask.status, func.count(TodoTask.id))
        .filter(TodoTask.is_active == True)  # noqa: E712
        .group_by(TodoTask.status)
        .all()
    ):
        if status in todo_status_counts:
            todo_status_counts[status] = count

    # Cafe snapshot
    today = date.today()
    month_start = today.replace(day=1)
    open_tables = CafeOrder.query.filter_by(status="open").count()
    paid_orders = CafeOrder.query.filter_by(status="paid").all()
    cafe_today_revenue = Decimal("0")
    cafe_month_revenue = Decimal("0")
    revenue_by_day = defaultdict(Decimal)
    for o in paid_orders:
        amount = Decimal(str(o.subtotal or 0))
        if o.paid_at:
            d = o.paid_at.date()
            if d == today:
                cafe_today_revenue += amount
            if d >= month_start:
                cafe_month_revenue += amount
            revenue_by_day[d.isoformat()] += amount
    revenue_day_labels = [(today - timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
    revenue_day_values = [float(revenue_by_day.get(k, Decimal("0"))) for k in revenue_day_labels]

    # Bot activity snapshot
    logs = BotAccessLog.query.order_by(BotAccessLog.created_at.desc()).limit(1000).all()
    bot_day_counts = defaultdict(int)
    for log in logs:
        bot_day_counts[log.created_at.date().isoformat()] += 1
    bot_labels = revenue_day_labels
    bot_values = [bot_day_counts.get(k, 0) for k in bot_labels]

    return render_template(
        "admin_dashboard/index.html",
        total_sessions=total_sessions,
        checked_sessions=checked_sessions,
        overall_rate=overall_rate,
        todo_active=todo_active,
        todo_backlog=todo_status_counts["backlog"],
        todo_doing=todo_status_counts["doing"],
        todo_done=todo_status_counts["done"],
        open_tables=open_tables,
        paid_orders_count=len(paid_orders),
        cafe_today_revenue=float(cafe_today_revenue),
        cafe_month_revenue=float(cafe_month_revenue),
        revenue_day_labels=revenue_day_labels,
        revenue_day_values=revenue_day_values,
        bot_labels=bot_labels,
        bot_values=bot_values,
    )
