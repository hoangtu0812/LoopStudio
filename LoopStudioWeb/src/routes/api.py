"""API cho bot ghi log truy cập."""
from flask import Blueprint, request

from ..app import db
from ..models import BotAccessLog
from ..services.todo_service import build_today_todo_message
from ..services.uptime_service import build_uptime_bot_message

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/bot/log", methods=["POST"])
def bot_log():
    """Bot gọi để ghi log truy cập."""
    data = request.get_json() or {}
    log = BotAccessLog(
        telegram_user_id=data.get("telegram_user_id"),
        telegram_username=data.get("telegram_username"),
        telegram_first_name=data.get("telegram_first_name"),
        command=data.get("command", ""),
        chat_id=data.get("chat_id"),
    )
    if log.telegram_user_id and log.chat_id is not None:
        db.session.add(log)
        db.session.commit()
    return "", 204

@api_bp.route("/bot/otp", methods=["POST"])
def bot_otp():
    """Bot gọi để lấy mã OTP cho user đăng ký."""
    import random
    from ..models import User

    data = request.get_json() or {}
    username = data.get("username")
    telegram_id = data.get("telegram_user_id")

    if not username:
        return {"error": "Thiếu username."}, 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return {"error": f"Không tìm thấy người dùng '{username}'."}, 404
    
    if user.is_active:
        return {"error": f"Tài khoản '{username}' đã kích hoạt."}, 400

    otp = str(random.randint(100000, 999999))
    user.otp_code = otp
    if telegram_id:
        user.telegram_id = str(telegram_id)
    db.session.commit()

    return {"status": "ok", "otp": otp}, 200


@api_bp.route("/bot/todo", methods=["GET"])
def bot_todo():
    """Bot gọi để lấy danh sách todo trong ngày."""
    text = build_today_todo_message()
    return {"status": "ok", "text": text}, 200


@api_bp.route("/bot/uptime", methods=["GET"])
def bot_uptime():
    """Bot gọi để lấy trạng thái uptime website."""
    text = build_uptime_bot_message()
    return {"status": "ok", "text": text}, 200
