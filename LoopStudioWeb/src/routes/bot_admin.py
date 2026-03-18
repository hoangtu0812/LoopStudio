"""Quản trị Telegram bot - lịch sử truy cập, gửi thông báo."""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from ..app import db
from ..models import BotAccessLog, MessageTemplate, NotificationConfig, TelegramChatTarget, User
from ..services.telegram_service import send_telegram_message_verbose

bot_admin_bp = Blueprint("bot_admin", __name__)


@bot_admin_bp.route("/")
@login_required
def index():
    if not current_user.is_admin:
        flash("Bạn không có quyền truy cập.", "error")
        return redirect(url_for("main.dashboard"))
    logs = BotAccessLog.query.order_by(BotAccessLog.created_at.desc()).limit(200).all()
    return render_template("bot_admin/index.html", logs=logs)


@bot_admin_bp.route("/send", methods=["GET", "POST"])
@login_required
def send_notification():
    if not current_user.is_admin:
        flash("Bạn không có quyền.", "error")
        return redirect(url_for("main.dashboard"))
    targets = TelegramChatTarget.query.filter_by(is_active=True).order_by(TelegramChatTarget.label.asc()).all()
    users_with_telegram = User.query.filter(
        User.telegram_id.isnot(None),
        User.telegram_id != "",
    ).order_by(User.username.asc()).all()
    message_templates = MessageTemplate.query.filter_by(is_active=True).order_by(MessageTemplate.name.asc()).all()

    if request.method == "POST":
        action = (request.form.get("action") or "send").strip()

        if action == "add_template":
            tpl_name = (request.form.get("template_name") or "").strip()
            tpl_content = (request.form.get("template_content") or "").strip()
            if not tpl_name or not tpl_content:
                flash("Vui lòng nhập tên mẫu và nội dung mẫu.", "error")
                return redirect(url_for("bot_admin.send_notification"))
            exists = MessageTemplate.query.filter_by(name=tpl_name).first()
            if exists:
                flash("Tên mẫu đã tồn tại. Vui lòng chọn tên khác.", "warning")
                return redirect(url_for("bot_admin.send_notification"))
            db.session.add(MessageTemplate(name=tpl_name, content=tpl_content, is_active=True))
            db.session.commit()
            flash("Đã thêm mẫu tin nhắn.", "success")
            return redirect(url_for("bot_admin.send_notification"))

        if action == "delete_template":
            template_id = request.form.get("template_id")
            if template_id and template_id.isdigit():
                template = MessageTemplate.query.get(int(template_id))
                if template:
                    db.session.delete(template)
                    db.session.commit()
                    flash("Đã xóa mẫu tin nhắn.", "success")
            return redirect(url_for("bot_admin.send_notification"))

        chat_id = (request.form.get("chat_id") or "").strip()

        picked_target = request.form.get("target_id")
        if picked_target and picked_target.isdigit():
            target = TelegramChatTarget.query.get(int(picked_target))
            if target and target.is_active:
                chat_id = target.chat_id

        picked_user = request.form.get("recipient_user_id")
        if picked_user and picked_user.isdigit():
            recipient_user = User.query.get(int(picked_user))
            if recipient_user and (recipient_user.telegram_id or "").strip():
                chat_id = recipient_user.telegram_id.strip()

        message = (request.form.get("message") or "").strip()
        template_id = request.form.get("message_template_id")
        if template_id and template_id.isdigit():
            template = MessageTemplate.query.get(int(template_id))
            if template and template.is_active:
                message = template.content

        if chat_id and message:
            ok, error_message = send_telegram_message_verbose(chat_id, message)
            if ok:
                flash("Đã gửi thông báo thành công.", "success")
            else:
                flash(
                    f"Gửi thất bại: {error_message or 'Kiểm tra Chat ID và BOT_TOKEN.'}",
                    "error",
                )
        else:
            flash("Vui lòng chọn người nhận (danh bạ / người dùng / nhập tay) và nhập nội dung.", "error")
    return render_template(
        "bot_admin/send.html",
        chat_targets=targets,
        users_with_telegram=users_with_telegram,
        message_templates=message_templates,
    )


@bot_admin_bp.route("/notifications", methods=["GET", "POST"])
@login_required
def notifications():
    if not current_user.is_admin:
        flash("Bạn không có quyền.", "error")
        return redirect(url_for("main.dashboard"))

    configs = NotificationConfig.query.order_by(NotificationConfig.id).all()
    targets = TelegramChatTarget.query.order_by(TelegramChatTarget.label.asc()).all()
    target_by_id = {t.id: t for t in targets}
    target_id_by_chat_id = {t.chat_id: t.id for t in targets}

    if request.method == "POST":
        action = (request.form.get("action") or "save_configs").strip()

        if action == "add_target":
            label = (request.form.get("target_label") or "").strip()
            chat_id = (request.form.get("target_chat_id") or "").strip()
            if not label or not chat_id:
                flash("Vui lòng nhập đủ tên hiển thị và Chat ID.", "error")
                return redirect(url_for("bot_admin.notifications"))
            exists = TelegramChatTarget.query.filter(
                (TelegramChatTarget.label == label) | (TelegramChatTarget.chat_id == chat_id)
            ).first()
            if exists:
                flash("Tên hiển thị hoặc Chat ID đã tồn tại trong danh bạ.", "warning")
                return redirect(url_for("bot_admin.notifications"))
            db.session.add(TelegramChatTarget(label=label, chat_id=chat_id, is_active=True))
            db.session.commit()
            flash("Đã thêm Chat ID vào danh bạ Telegram.", "success")
            return redirect(url_for("bot_admin.notifications"))

        for cfg in configs:
            picked_target = request.form.get(f"target_{cfg.id}")
            picked_target_id = int(picked_target) if picked_target and picked_target.isdigit() else None
            manual_chat_id = (request.form.get(f"chat_{cfg.id}") or "").strip()

            cfg.chat_target_id = picked_target_id
            if picked_target_id and picked_target_id in target_by_id:
                cfg.chat_id = target_by_id[picked_target_id].chat_id
            elif manual_chat_id:
                cfg.chat_id = manual_chat_id

            cfg.minutes_before = int(request.form.get(f"min_{cfg.id}", 15))
            cfg.enabled = request.form.get(f"enabled_{cfg.id}") == "on"

        new_type = (request.form.get("new_type") or "").strip()
        if new_type:
            new_target = request.form.get("new_target")
            new_target_id = int(new_target) if new_target and new_target.isdigit() else None
            new_chat_id = (request.form.get("new_chat_id") or "").strip()
            if new_target_id and new_target_id in target_by_id:
                new_chat_id = target_by_id[new_target_id].chat_id
            nc = NotificationConfig(
                config_type=new_type,
                chat_id=new_chat_id,
                chat_target_id=new_target_id,
                minutes_before=int(request.form.get("new_minutes", 15)),
            )
            db.session.add(nc)
        db.session.commit()
        flash("Đã lưu cấu hình thông báo Telegram.", "success")
        return redirect(url_for("bot_admin.notifications"))

    required_defaults = {
        "schedule_reminder": 15,
        "task_reminder": 60,
        "todo_daily_digest": 0,
        "todo_deadline_reminder": 30,
        "calendar_event_notify": 0,
        "uptime_down_alert": 0,
    }
    existing_types = {c.config_type for c in configs}
    created = False
    for config_type, minutes in required_defaults.items():
        if config_type not in existing_types:
            db.session.add(
                NotificationConfig(
                    config_type=config_type,
                    chat_id="",
                    minutes_before=minutes,
                )
            )
            created = True
    if created:
        db.session.commit()
        configs = NotificationConfig.query.order_by(NotificationConfig.id).all()

    for cfg in configs:
        if not cfg.chat_target_id and cfg.chat_id:
            cfg.chat_target_id = target_id_by_chat_id.get(cfg.chat_id)

    return render_template(
        "schedule/notifications.html",
        configs=configs,
        chat_targets=targets,
    )


@bot_admin_bp.route("/notifications/targets/<int:id>/delete", methods=["POST"])
@login_required
def delete_chat_target(id):
    if not current_user.is_admin:
        flash("Bạn không có quyền.", "error")
        return redirect(url_for("main.dashboard"))
    target = TelegramChatTarget.query.get_or_404(id)
    NotificationConfig.query.filter_by(chat_target_id=target.id).update({"chat_target_id": None})
    db.session.delete(target)
    db.session.commit()
    flash("Đã xóa Chat ID khỏi danh bạ.", "success")
    return redirect(url_for("bot_admin.notifications"))


@bot_admin_bp.route("/users")
@login_required
def users_list():
    if not current_user.is_admin:
        flash("Bạn không có quyền truy cập.", "error")
        return redirect(url_for("main.dashboard"))
    users = User.query.order_by(User.id).all()
    return render_template("bot_admin/users.html", users=users)


@bot_admin_bp.route("/users/<int:id>/telegram", methods=["POST"])
@login_required
def update_user_telegram_id(id):
    if not current_user.is_admin:
        flash("Bạn không có quyền.", "error")
        return redirect(url_for("main.dashboard"))
    user = User.query.get_or_404(id)
    telegram_user_id = (request.form.get("telegram_user_id") or "").strip()
    user.telegram_id = telegram_user_id or None
    db.session.commit()
    flash(f"Đã cập nhật Telegram User ID cho {user.username}.", "success")
    return redirect(url_for("bot_admin.users_list"))


@bot_admin_bp.route("/users/<int:id>/toggle_admin", methods=["POST"])
@login_required
def toggle_admin(id):
    if not current_user.is_admin:
        flash("Bạn không có quyền.", "error")
        return redirect(url_for("main.dashboard"))
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash("Không thể tự gỡ quyền admin của chính mình.", "warning")
        return redirect(url_for("bot_admin.users_list"))
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f"Đã cập nhật quyền cho {user.username}.", "success")
    return redirect(url_for("bot_admin.users_list"))


@bot_admin_bp.route("/users/<int:id>/delete", methods=["POST"])
@login_required
def delete_user(id):
    if not current_user.is_admin:
        flash("Bạn không có quyền.", "error")
        return redirect(url_for("main.dashboard"))
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash("Không thể tự xóa chính mình.", "warning")
        return redirect(url_for("bot_admin.users_list"))
    db.session.delete(user)
    db.session.commit()
    flash(f"Đã xóa tài khoản {user.username}.", "success")
    return redirect(url_for("bot_admin.users_list"))
