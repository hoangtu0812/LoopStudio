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
    table_names = set(inspector.get_table_names())

    from .models import TodoTaskChangeLog

    if "todo_task_change_logs" not in table_names:
        TodoTaskChangeLog.__table__.create(bind=db.engine, checkfirst=True)
    if "todo_tasks" not in table_names:
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
    if "parent_task_id" not in columns:
        alter_stmts.append("ALTER TABLE todo_tasks ADD COLUMN parent_task_id INTEGER")
    if "updated_at" not in columns:
        alter_stmts.append("ALTER TABLE todo_tasks ADD COLUMN updated_at TIMESTAMP")

    if not alter_stmts:
        return

    with db.engine.begin() as conn:
        for stmt in alter_stmts:
            conn.execute(text(stmt))


def _ensure_notification_schema() -> None:
    """Bổ sung schema cho cấu hình Telegram nếu DB cũ chưa có."""
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    if "telegram_chat_targets" not in table_names:
        from .models import TelegramChatTarget
        TelegramChatTarget.__table__.create(bind=db.engine, checkfirst=True)

    if "notification_configs" not in table_names:
        return

    columns = {c["name"] for c in inspector.get_columns("notification_configs")}
    if "chat_target_id" not in columns:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE notification_configs ADD COLUMN chat_target_id INTEGER"))


def _ensure_user_schema() -> None:
    """Bổ sung cột reset password cho users nếu DB cũ chưa có."""
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("users")}
    alter_stmts: list[str] = []
    if "reset_otp_code" not in columns:
        alter_stmts.append("ALTER TABLE users ADD COLUMN reset_otp_code VARCHAR(6)")
    if "reset_otp_expires_at" not in columns:
        alter_stmts.append("ALTER TABLE users ADD COLUMN reset_otp_expires_at TIMESTAMP")
    if not alter_stmts:
        return
    with db.engine.begin() as conn:
        for stmt in alter_stmts:
            conn.execute(text(stmt))


def _ensure_cafe_schema() -> None:
    """Bổ sung schema cho module cafe nếu DB cũ chưa có."""
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    from .models import CafeMenuItem, CafeOrder, CafeOrderItem

    if "cafe_menu_items" not in table_names:
        CafeMenuItem.__table__.create(bind=db.engine, checkfirst=True)
    if "cafe_orders" not in table_names:
        CafeOrder.__table__.create(bind=db.engine, checkfirst=True)
    if "cafe_order_items" not in table_names:
        CafeOrderItem.__table__.create(bind=db.engine, checkfirst=True)

    inspector = inspect(db.engine)

    alter_stmts: list[str] = []

    menu_columns = {c["name"] for c in inspector.get_columns("cafe_menu_items")} if "cafe_menu_items" in inspector.get_table_names() else set()
    if "image_url" not in menu_columns:
        alter_stmts.append("ALTER TABLE cafe_menu_items ADD COLUMN image_url VARCHAR(500)")
    if "price" not in menu_columns:
        alter_stmts.append("ALTER TABLE cafe_menu_items ADD COLUMN price NUMERIC(12,2) DEFAULT 0")
    if "category" not in menu_columns:
        alter_stmts.append("ALTER TABLE cafe_menu_items ADD COLUMN category VARCHAR(80)")
    if "is_active" not in menu_columns:
        alter_stmts.append("ALTER TABLE cafe_menu_items ADD COLUMN is_active BOOLEAN DEFAULT 1")

    order_columns = {c["name"] for c in inspector.get_columns("cafe_orders")} if "cafe_orders" in inspector.get_table_names() else set()
    if "status" not in order_columns:
        alter_stmts.append("ALTER TABLE cafe_orders ADD COLUMN status VARCHAR(20) DEFAULT 'open'")
    if "subtotal" not in order_columns:
        alter_stmts.append("ALTER TABLE cafe_orders ADD COLUMN subtotal NUMERIC(12,2) DEFAULT 0")
    if "payment_method" not in order_columns:
        alter_stmts.append("ALTER TABLE cafe_orders ADD COLUMN payment_method VARCHAR(30)")
    if "paid_at" not in order_columns:
        alter_stmts.append("ALTER TABLE cafe_orders ADD COLUMN paid_at TIMESTAMP")

    item_columns = {c["name"] for c in inspector.get_columns("cafe_order_items")} if "cafe_order_items" in inspector.get_table_names() else set()
    if "menu_item_id" not in item_columns:
        alter_stmts.append("ALTER TABLE cafe_order_items ADD COLUMN menu_item_id INTEGER")
    if "item_name_snapshot" not in item_columns:
        alter_stmts.append("ALTER TABLE cafe_order_items ADD COLUMN item_name_snapshot VARCHAR(150) DEFAULT ''")
    if "unit_price_snapshot" not in item_columns:
        alter_stmts.append("ALTER TABLE cafe_order_items ADD COLUMN unit_price_snapshot NUMERIC(12,2) DEFAULT 0")
    if "qty" not in item_columns:
        alter_stmts.append("ALTER TABLE cafe_order_items ADD COLUMN qty INTEGER DEFAULT 1")
    if "line_total" not in item_columns:
        alter_stmts.append("ALTER TABLE cafe_order_items ADD COLUMN line_total NUMERIC(12,2) DEFAULT 0")
    if "kitchen_status" not in item_columns:
        alter_stmts.append("ALTER TABLE cafe_order_items ADD COLUMN kitchen_status VARCHAR(20) DEFAULT 'pending'")
    if "note" not in item_columns:
        alter_stmts.append("ALTER TABLE cafe_order_items ADD COLUMN note VARCHAR(255)")

    if not alter_stmts:
        return
    with db.engine.begin() as conn:
        for stmt in alter_stmts:
            conn.execute(text(stmt))


def _ensure_uptime_schema() -> None:
    """Bổ sung schema cho uptime monitor nếu DB cũ chưa có."""
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    from .models import UptimeCheck, UptimeSite

    if "uptime_sites" not in table_names:
        UptimeSite.__table__.create(bind=db.engine, checkfirst=True)
    if "uptime_checks" not in table_names:
        UptimeCheck.__table__.create(bind=db.engine, checkfirst=True)

    inspector = inspect(db.engine)
    alter_stmts: list[str] = []

    site_cols = {c["name"] for c in inspector.get_columns("uptime_sites")} if "uptime_sites" in inspector.get_table_names() else set()
    if "check_interval_seconds" not in site_cols:
        alter_stmts.append("ALTER TABLE uptime_sites ADD COLUMN check_interval_seconds INTEGER DEFAULT 60")
    if "timeout_seconds" not in site_cols:
        alter_stmts.append("ALTER TABLE uptime_sites ADD COLUMN timeout_seconds INTEGER DEFAULT 8")
    if "expected_status_code" not in site_cols:
        alter_stmts.append("ALTER TABLE uptime_sites ADD COLUMN expected_status_code INTEGER DEFAULT 200")
    if "keyword" not in site_cols:
        alter_stmts.append("ALTER TABLE uptime_sites ADD COLUMN keyword VARCHAR(255)")
    if "is_active" not in site_cols:
        alter_stmts.append("ALTER TABLE uptime_sites ADD COLUMN is_active BOOLEAN DEFAULT 1")
    if "current_status" not in site_cols:
        alter_stmts.append("ALTER TABLE uptime_sites ADD COLUMN current_status VARCHAR(20) DEFAULT 'unknown'")
    if "last_checked_at" not in site_cols:
        alter_stmts.append("ALTER TABLE uptime_sites ADD COLUMN last_checked_at TIMESTAMP")
    if "last_status_change_at" not in site_cols:
        alter_stmts.append("ALTER TABLE uptime_sites ADD COLUMN last_status_change_at TIMESTAMP")
    if "last_response_ms" not in site_cols:
        alter_stmts.append("ALTER TABLE uptime_sites ADD COLUMN last_response_ms INTEGER")
    if "last_error" not in site_cols:
        alter_stmts.append("ALTER TABLE uptime_sites ADD COLUMN last_error VARCHAR(500)")

    check_cols = {c["name"] for c in inspector.get_columns("uptime_checks")} if "uptime_checks" in inspector.get_table_names() else set()
    if "status_code" not in check_cols:
        alter_stmts.append("ALTER TABLE uptime_checks ADD COLUMN status_code INTEGER")
    if "response_ms" not in check_cols:
        alter_stmts.append("ALTER TABLE uptime_checks ADD COLUMN response_ms INTEGER")
    if "error_message" not in check_cols:
        alter_stmts.append("ALTER TABLE uptime_checks ADD COLUMN error_message VARCHAR(500)")

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
    from .routes.cafe_admin import cafe_admin_bp
    from .routes.cafe_order import cafe_order_bp
    from .routes.cafe_kitchen import cafe_kitchen_bp
    from .routes.uptime import uptime_bp
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
    app.register_blueprint(cafe_admin_bp, url_prefix="/cafe/admin")
    app.register_blueprint(cafe_order_bp, url_prefix="/cafe/order")
    app.register_blueprint(cafe_kitchen_bp, url_prefix="/cafe/kitchen")
    app.register_blueprint(uptime_bp, url_prefix="/uptime")

    from .models import AppPermission

    APP_KEY_BY_BLUEPRINT = {
        "calendar": "calendar",
        "schedule": "schedule",
        "todo": "todo",
        "admin_dashboard": "dashboard",
        "bot_admin": "bot_admin",
        "cafe_admin": "cafe",
        "cafe_order": "cafe",
        "cafe_kitchen": "cafe",
        "uptime": "uptime",
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
        _ensure_notification_schema()
        _ensure_user_schema()
        _ensure_cafe_schema()
        _ensure_uptime_schema()
        # Tạo user admin mặc định nếu chưa có user nào
        from .models import User, UserGroup, AppPermission
        if User.query.count() == 0:
            admin = User(username="admin", is_admin=True)
            admin.set_password("admin")
            db.session.add(admin)
            db.session.commit()
            app.logger.info("Đã tạo user admin/admin - đổi mật khẩu ngay!")

        app_keys = ["calendar", "schedule", "todo", "dashboard", "bot_admin", "cafe", "uptime"]

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
