from datetime import datetime

from ..app import db


class UptimeSite(db.Model):
    __tablename__ = "uptime_sites"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    url = db.Column(db.String(500), nullable=False, unique=True)
    check_interval_seconds = db.Column(db.Integer, nullable=False, default=60)
    timeout_seconds = db.Column(db.Integer, nullable=False, default=8)
    expected_status_code = db.Column(db.Integer, nullable=False, default=200)
    keyword = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    current_status = db.Column(db.String(20), nullable=False, default="unknown")  # up/down/unknown
    last_checked_at = db.Column(db.DateTime, nullable=True)
    last_status_change_at = db.Column(db.DateTime, nullable=True)
    last_response_ms = db.Column(db.Integer, nullable=True)
    last_error = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    checks = db.relationship("UptimeCheck", backref="site", cascade="all, delete-orphan")


class UptimeCheck(db.Model):
    __tablename__ = "uptime_checks"

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey("uptime_sites.id"), nullable=False, index=True)
    is_up = db.Column(db.Boolean, nullable=False, default=False)
    status_code = db.Column(db.Integer, nullable=True)
    response_ms = db.Column(db.Integer, nullable=True)
    error_message = db.Column(db.String(500), nullable=True)
    checked_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
