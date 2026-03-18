from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..app import db
from .user_group import user_groups_users


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)  # True for existing, False for new unverified
    otp_code = db.Column(db.String(6), nullable=True)
    telegram_id = db.Column(db.String(50), nullable=True)
    reset_otp_code = db.Column(db.String(6), nullable=True)
    reset_otp_expires_at = db.Column(db.DateTime, nullable=True)

    groups = db.relationship(
        "UserGroup",
        secondary=user_groups_users,
        back_populates="users",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
