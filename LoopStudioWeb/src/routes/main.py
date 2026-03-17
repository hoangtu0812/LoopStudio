"""Trang chủ - intro (không cần đăng nhập) và dashboard."""
from flask import Blueprint, render_template
from flask_login import current_user, login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Trang giới thiệu - không cần đăng nhập."""
    return render_template("main/index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """Trang tổng hợp các ứng dụng và dashboard cá nhân."""
    from datetime import date, datetime
    from ..models.schedule import ScheduleSession, Task
    
    today = date.today()
    
    # 1. Hôm nay có lịch gì không?
    today_sessions = ScheduleSession.query.filter(
        ScheduleSession.session_date == today
    ).order_by(ScheduleSession.start_time).all()
    
    # 2. Upcoming sessions (trong vòng 7 ngày tới)
    upcoming_sessions = ScheduleSession.query.filter(
        ScheduleSession.session_date > today
    ).order_by(ScheduleSession.session_date, ScheduleSession.start_time).limit(5).all()
    
    # 3. Tasks cần làm (chưa xong & deadline <= cuối ngày hôm nay, hoặc đã quá hạn)
    # Lấy các task chưa hoàn thành
    tasks_due_today = []
    undone_tasks = Task.query.filter_by(done=False).all()
    for task in undone_tasks:
        if task.deadline:
            # So sánh ngày
            if task.deadline.date() <= today:
                tasks_due_today.append(task)
                
    # Sort tasks by deadline
    tasks_due_today.sort(key=lambda t: t.deadline)

    return render_template(
        "main/dashboard.html", 
        today_sessions=today_sessions,
        upcoming_sessions=upcoming_sessions,
        tasks_due_today=tasks_due_today
    )
