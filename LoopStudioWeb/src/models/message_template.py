from datetime import datetime

from ..app import db


class MessageTemplate(db.Model):
    """Mẫu tin nhắn dùng lại trong Bot Admin."""

    __tablename__ = "message_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    content = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
