"""API cho bot ghi log truy cập."""
from flask import Blueprint, request

from ..app import db
from ..models import BotAccessLog

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
