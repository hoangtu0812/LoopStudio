"""Flask Application - Loop Studio Web App."""
from flask import Flask, abort, request
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import inspect, text

from .config import SECRET_KEY, SQLALCHEMY_DATABASE_URI

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def _ensure_todo_schema() -> None:
    """Bổ sung cột mới cho todo_tasks nếu DB đã tồn tại trước đó."""
    inspector = inspect(db.engine)
    if "todo_tasks" not in inspector.get_table_names():
        return

    columns = {c["name"] for c in inspector.get_columns("todo_tasks")}
    alter_stmts: list[str] = []
    if "start_at" not in columns:
        alter_stmts.append("ALTER TABLE todo_tasks ADD COLUMN start_at TIMESTAMP")
    if "status" not in columns:
        alter_stmts.append("ALTER TABLE todo_tasks ADD COLUMN status VARCHAR(20) DEFAULT 'backlog'")
    if "priority" not in columns:
        alter_stmts.append("ALTER TABLE todo_tasks ADD COLUMN priority INTEGER DEFAULT 2")
    if "lane" not in columns:
        alter_stmts.append("ALTER TABLE todo_tasks ADD COLUMN lane VARCHAR(50)")

    if not alter_stmts:
        return

    with db.engine.begin() as conn:
        for stmt in alter_stmts:
            conn.execute(text(stmt))


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Vui lòng đăng nhập để truy cập trang này."

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from .routes.main import main_bp
    from .routes.auth import auth_bp
    from .routes.bot_admin import bot_admin_bp
    from .routes.group_admin import group_admin_bp
    from .routes.admin_dashboard import admin_dashboard_bp
    from .routes.calendar import calendar_bp
    from .routes.schedule import schedule_bp
    from .routes.todo import todo_bp
    from .routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    csrf.exempt(api_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(bot_admin_bp, url_prefix="/bot")
    app.register_blueprint(group_admin_bp, url_prefix="/groups")
    app.register_blueprint(admin_dashboard_bp, url_prefix="/admin-dashboard")
    app.register_blueprint(calendar_bp, url_prefix="/calendar")
    app.register_blueprint(schedule_bp, url_prefix="/schedule")
    app.register_blueprint(todo_bp, url_prefix="/todo")

    from .models import AppPermission

    APP_KEY_BY_BLUEPRINT = {
        "calendar": "calendar",
        "schedule": "schedule",
        "todo": "todo",
        "admin_dashboard": "dashboard",
        "bot_admin": "bot_admin",
    }

    def user_can_access(user, app_key: str) -> bool:
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "is_admin", False):
            return True
        groups = getattr(user, "groups", []) or []
        if not groups:
            return False
        group_ids = [g.id for g in groups]
        return (
            AppPermission.query.filter(
                AppPermission.group_id.in_(group_ids),
                AppPermission.app_key == app_key,
                AppPermission.can_access.is_(True),
            ).first()
            is not None
        )

    app.jinja_env.globals["user_can_access"] = user_can_access

    @app.before_request
    def check_app_permission():
        if not current_user.is_authenticated:
            return
        if getattr(current_user, "is_admin", False):
            return
        bp = request.blueprint
        app_key = APP_KEY_BY_BLUEPRINT.get(bp)
        if not app_key:
            return
        if not user_can_access(current_user, app_key):
            abort(403)

    with app.app_context():
        db.create_all()
        _ensure_todo_schema()
        # Tạo user admin mặc định nếu chưa có user nào
        from .models import User, UserGroup, AppPermission
        if User.query.count() == 0:
            admin = User(username="admin", is_admin=True)
            admin.set_password("admin")
            db.session.add(admin)
            db.session.commit()
            app.logger.info("Đã tạo user admin/admin - đổi mật khẩu ngay!")

        app_keys = ["calendar", "schedule", "todo", "dashboard", "bot_admin"]

        # tạo group default nếu chưa có: full quyền cho mọi app
        if UserGroup.query.count() == 0:
            default_group = UserGroup(name="default", description="Nhóm mặc định")
            db.session.add(default_group)
            db.session.flush()
            for key in app_keys:
                db.session.add(
                    AppPermission(
                        group_id=default_group.id,
                        app_key=key,
                        can_access=True,
                    )
                )
            db.session.commit()

        # đảm bảo mọi group đều có bản ghi permission cho các app mới
        groups = UserGroup.query.all()
        changed = False
        for g in groups:
            existing = {p.app_key for p in g.app_permissions}
            for key in app_keys:
                if key not in existing:
                    db.session.add(AppPermission(group_id=g.id, app_key=key, can_access=False))
                    changed = True
        if changed:
            db.session.commit()

    from .services.schedule_notifier import start_scheduler
    start_scheduler(app)

    return app
