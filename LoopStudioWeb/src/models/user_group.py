from ..app import db


user_groups_users = db.Table(
    "user_groups_users",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("group_id", db.Integer, db.ForeignKey("user_groups.id"), primary_key=True),
)


class UserGroup(db.Model):
    __tablename__ = "user_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    users = db.relationship(
        "User",
        secondary=user_groups_users,
        back_populates="groups",
    )
    app_permissions = db.relationship(
        "AppPermission",
        backref="group",
        cascade="all, delete-orphan",
    )


class AppPermission(db.Model):
    __tablename__ = "app_permissions"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("user_groups.id"), nullable=False)
    app_key = db.Column(db.String(50), nullable=False)
    can_access = db.Column(db.Boolean, default=True)

