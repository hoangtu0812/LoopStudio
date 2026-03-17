"""Quản trị Telegram bot - lịch sử truy cập, gửi thông báo."""
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from ..app import db
from ..models import BotAccessLog
from ..services.telegram_service import send_telegram_message

bot_admin_bp = Blueprint("bot_admin", __name__)


@bot_admin_bp.route("/")
@login_required
def index():
    if not current_user.is_admin:
        flash("Bạn không có quyền truy cập.", "error")
        return redirect(url_for("main.dashboard"))
    logs = BotAccessLog.query.order_by(BotAccessLog.created_at.desc()).limit(200).all()
    return render_template("bot_admin/index.html", logs=logs)


@bot_admin_bp.route("/send", methods=["GET", "POST"])
@login_required
def send_notification():
    if not current_user.is_admin:
        flash("Bạn không có quyền.", "error")
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        chat_id = request.form.get("chat_id")
        message = request.form.get("message")
        if chat_id and message:
            ok = send_telegram_message(chat_id, message)
            if ok:
                flash("Đã gửi thông báo thành công.", "success")
            else:
                flash("Gửi thất bại. Kiểm tra Chat ID và BOT_TOKEN.", "error")
        else:
            flash("Vui lòng nhập Chat ID và nội dung.", "error")
    return render_template("bot_admin/send.html")
