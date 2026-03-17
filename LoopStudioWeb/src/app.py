"""Flask Application - Loop Studio Web App."""
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from .config import SECRET_KEY, SQLALCHEMY_DATABASE_URI

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


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
    from .routes.schedule import schedule_bp
    from .routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    csrf.exempt(api_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(bot_admin_bp, url_prefix="/bot")
    app.register_blueprint(schedule_bp, url_prefix="/schedule")

    with app.app_context():
        db.create_all()
        # Tạo user admin mặc định nếu chưa có user nào
        from .models import User
        if User.query.count() == 0:
            admin = User(username="admin", is_admin=True)
            admin.set_password("admin")
            db.session.add(admin)
            db.session.commit()
            app.logger.info("Đã tạo user admin/admin - đổi mật khẩu ngay!")

    from .services.schedule_notifier import start_scheduler
    start_scheduler(app)

    return app
