"""Dashboard quản trị với biểu đồ thống kê."""
from collections import defaultdict

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from ..models import ScheduleSession

admin_dashboard_bp = Blueprint("admin_dashboard", __name__)


@admin_dashboard_bp.route("/")
@login_required
def index():
    if not current_user.is_admin:
        flash("Bạn không có quyền truy cập.", "error")
        return redirect(url_for("main.dashboard"))

    sessions = ScheduleSession.query.order_by(ScheduleSession.session_date.asc()).all()
    week_stats = defaultdict(lambda: {"total": 0, "checked": 0})
    subject_stats = defaultdict(lambda: {"total": 0, "checked": 0})

    for session in sessions:
        year, week, _ = session.session_date.isocalendar()
        week_key = f"{year}-W{week:02d}"
        week_stats[week_key]["total"] += 1
        week_stats[week_key]["checked"] += 1 if session.check_ins else 0

        subject_name = session.schedule.name
        subject_stats[subject_name]["total"] += 1
        subject_stats[subject_name]["checked"] += 1 if session.check_ins else 0

    week_labels = sorted(week_stats.keys())[-12:]
    week_rates = []
    for wk in week_labels:
        total = week_stats[wk]["total"]
        checked = week_stats[wk]["checked"]
        rate = round((checked / total) * 100, 1) if total else 0
        week_rates.append(rate)

    subject_items = []
    for subject, values in subject_stats.items():
        total = values["total"]
        checked = values["checked"]
        rate = round((checked / total) * 100, 1) if total else 0
        subject_items.append((subject, rate))
    subject_items.sort(key=lambda x: x[1], reverse=True)
    subject_labels = [x[0] for x in subject_items[:10]]
    subject_rates = [x[1] for x in subject_items[:10]]

    total_all = sum(v["total"] for v in week_stats.values())
    checked_all = sum(v["checked"] for v in week_stats.values())
    overall_rate = round((checked_all / total_all) * 100, 1) if total_all else 0

    return render_template(
        "admin_dashboard/index.html",
        week_labels=week_labels,
        week_rates=week_rates,
        subject_labels=subject_labels,
        subject_rates=subject_rates,
        overall_rate=overall_rate,
        total_sessions=total_all,
        checked_sessions=checked_all,
    )
