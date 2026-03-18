from datetime import datetime

from ..app import db


class CalendarEvent(db.Model):
    """Sự kiện chung trên lịch (meeting, nhắc việc thủ công, sự kiện cá nhân)."""

    __tablename__ = "calendar_events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.String(1000), nullable=True)
    event_type = db.Column(db.String(30), nullable=False, default="meeting")
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime, nullable=False)
    all_day = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), nullable=False, default="planned")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

