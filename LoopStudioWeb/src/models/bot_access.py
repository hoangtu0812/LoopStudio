from datetime import datetime

from ..app import db


class BotAccessLog(db.Model):
    """Lịch sử truy cập bot - user_id, command, thời gian."""

    __tablename__ = "bot_access_logs"

    id = db.Column(db.Integer, primary_key=True)
    telegram_user_id = db.Column(db.BigInteger, nullable=False)
    telegram_username = db.Column(db.String(100))
    telegram_first_name = db.Column(db.String(100))
    command = db.Column(db.String(50), nullable=False)
    chat_id = db.Column(db.BigInteger, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
