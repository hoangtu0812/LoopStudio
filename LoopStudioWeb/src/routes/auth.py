"""Đăng nhập / Đăng ký."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required

from ..app import db
from ..models import User

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
        username = request.form.get("username")
        password = request.form.get("password")
        if User.query.filter_by(username=username).first():
            flash("Tên đăng nhập đã tồn tại.", "error")
        else:
            user = User(username=username, is_active=False)
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
