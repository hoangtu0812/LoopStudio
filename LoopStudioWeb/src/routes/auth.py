"""Đăng nhập / Đăng ký."""
from datetime import datetime, timedelta
from random import randint

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required

from ..app import db
from ..models import User
from ..services.telegram_service import send_telegram_message_verbose

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash("Tài khoản chưa được kích hoạt. Nhập mã OTP từ bot để tiếp tục.", "warning")
                return redirect(url_for("auth.verify_otp", username=username))
            login_user(user)
            next_url = request.args.get("next") or url_for("main.dashboard")
            return redirect(next_url)
        flash("Tên đăng nhập hoặc mật khẩu không đúng.", "error")
    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password")
        telegram_user_id = (request.form.get("telegram_user_id") or "").strip()
        if User.query.filter_by(username=username).first():
            flash("Tên đăng nhập đã tồn tại.", "error")
        else:
            user = User(
                username=username,
                is_active=False,
                telegram_id=telegram_user_id or None,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Đăng ký thành công. Vui lòng nhận mã OTP từ LoopStudioBot bằng lệnh /otp để kích hoạt.", "success")
            return redirect(url_for("auth.verify_otp", username=username))
    return render_template("auth/register.html")


@auth_bp.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    username = request.args.get("username") or request.form.get("username")
    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("Người dùng không tồn tại.", "error")
        elif user.is_active:
            flash("Tài khoản đã được kích hoạt, vui lòng đăng nhập.", "info")
            return redirect(url_for("auth.login"))
        elif user.otp_code and user.otp_code == otp:
            user.is_active = True
            user.otp_code = None
            db.session.commit()
            login_user(user)
            flash("Kích hoạt tài khoản thành công!", "success")
            return redirect(url_for("main.dashboard"))
        else:
            flash("Mã OTP không hợp lệ hoặc đã hết hạn.", "error")
    return render_template("auth/verify_otp.html", username=username)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        user = User.query.filter_by(username=username).first()

        if not user:
            flash("Không tìm thấy tài khoản tương ứng.", "error")
            return render_template("auth/forgot_password.html")

        telegram_id = (user.telegram_id or "").strip()
        if not telegram_id:
            flash(
                "Tài khoản chưa có Telegram User ID. Vui lòng liên hệ admin hoặc cập nhật Telegram ID trước.",
                "warning",
            )
            return render_template("auth/forgot_password.html")

        otp = f"{randint(0, 999999):06d}"
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        otp_message = (
            "🔐 *Loop Studio - Reset mật khẩu*\n"
            f"Mã OTP của bạn là: `{otp}`\n"
            "Mã có hiệu lực trong 10 phút."
        )
        ok, err = send_telegram_message_verbose(telegram_id, otp_message)
        if not ok:
            flash(
                f"Gửi OTP thất bại: {err or 'lỗi không xác định'}. "
                "Hãy mở Telegram và /start bot trước khi thử lại.",
                "error",
            )
            return render_template("auth/forgot_password.html")

        user.reset_otp_code = otp
        user.reset_otp_expires_at = expires_at
        db.session.commit()
        flash("Đã gửi OTP reset mật khẩu tới Telegram của bạn.", "success")
        return redirect(url_for("auth.reset_password", username=user.username))
    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    username = (request.args.get("username") or request.form.get("username") or "").strip()
    if request.method == "POST":
        otp = (request.form.get("otp") or "").strip()
        new_password = request.form.get("new_password") or ""
        confirm_password = request.form.get("confirm_password") or ""
        user = User.query.filter_by(username=username).first()

        if not user:
            flash("Không tìm thấy tài khoản.", "error")
            return render_template("auth/reset_password.html", username=username)

        if new_password != confirm_password:
            flash("Mật khẩu xác nhận không khớp.", "error")
            return render_template("auth/reset_password.html", username=username)

        if (
            not user.reset_otp_code
            or user.reset_otp_code != otp
            or not user.reset_otp_expires_at
            or user.reset_otp_expires_at < datetime.utcnow()
        ):
            flash("OTP không hợp lệ hoặc đã hết hạn.", "error")
            return render_template("auth/reset_password.html", username=username)

        user.set_password(new_password)
        user.reset_otp_code = None
        user.reset_otp_expires_at = None
        db.session.commit()
        flash("Đặt lại mật khẩu thành công. Vui lòng đăng nhập lại.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", username=username)
