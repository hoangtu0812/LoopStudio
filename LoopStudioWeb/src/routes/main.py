"""Trang chủ - intro (không cần đăng nhập) và dashboard."""
from flask import Blueprint, render_template, url_for
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
    from datetime import date, datetime, timedelta
    from ..services.calendar_service import collect_events
    from ..services.todo_service import get_today_todo_timeline

    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    week_end = datetime.combine(today + timedelta(days=7), datetime.max.time())

    events_today = collect_events(today_start, today_end)
    upcoming_events = collect_events(today_start, week_end)
    upcoming_events = [e for e in upcoming_events if e["start_at"].date() > today][:12]

    tasks_due_today = [e for e in events_today if e["event_type"] == "todo"]
    todo_timeline = get_today_todo_timeline()

    return render_template(
        "main/dashboard.html",
        events_today=events_today,
        upcoming_events=upcoming_events,
        tasks_due_today=tasks_due_today,
        todo_timeline=todo_timeline,
    )

@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """Trang quản lý hồ sơ cá nhân."""
    from flask import request, flash, redirect, url_for
    from ..app import db
    
    if request.method == "POST":
        full_name = request.form.get("full_name")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        
        # Cập nhật tên
        if full_name is not None:
            current_user.full_name = full_name.strip()
            
        # Cập nhật mật khẩu nếu có nhập
        if new_password:
            if new_password != confirm_password:
                flash("Mật khẩu xác nhận không khớp.", "error")
                return redirect(url_for("main.profile"))
            current_user.set_password(new_password)
            
        db.session.commit()
        flash("Đã cập nhật hồ sơ thành công.", "success")
        return redirect(url_for("main.profile"))
        
    return render_template("main/profile.html")


@main_bp.route("/api-docs")
def api_docs():
    """Trang tài liệu API nội bộ."""
    sections = [
        {
            "title": "Bot APIs",
            "items": [
                {"method": "POST", "path": "/api/bot/log", "desc": "Ghi log truy cập từ Telegram bot."},
                {"method": "POST", "path": "/api/bot/otp", "desc": "Lấy OTP kích hoạt tài khoản theo username."},
                {"method": "GET", "path": "/api/bot/todo", "desc": "Lấy nội dung danh sách todo hôm nay."},
                {"method": "GET", "path": "/api/bot/uptime", "desc": "Lấy trạng thái uptime hiện tại."},
            ],
        },
        {
            "title": "Todo APIs (Web Form Endpoints)",
            "items": [
                {"method": "POST", "path": "/todo/", "desc": "Tạo task mới (weekly/deadline)."},
                {"method": "POST", "path": "/todo/<id>/update", "desc": "Cập nhật task/subtask."},
                {"method": "POST", "path": "/todo/<id>/subtasks", "desc": "Tạo subtask cho task cha."},
                {"method": "POST", "path": "/todo/<id>/move", "desc": "Đổi trạng thái backlog/doing/done."},
                {"method": "GET", "path": "/todo/gantt", "desc": "Xem gantt (week/month/year/custom)."},
            ],
        },
        {
            "title": "Uptime APIs (Web + Bot integration)",
            "items": [
                {"method": "GET", "path": "/uptime/", "desc": "Trang monitor uptime."},
                {"method": "POST", "path": "/uptime/<id>/check-now", "desc": "Check website thủ công."},
                {"method": "POST", "path": "/uptime/<id>/toggle", "desc": "Pause/resume monitor."},
                {"method": "GET", "path": "/uptime/<id>/history", "desc": "Lịch sử check chi tiết."},
            ],
        },
    ]
    return render_template("main/api_docs.html", sections=sections)
