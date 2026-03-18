"""Quản trị group người dùng và quyền ứng dụng."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..app import db
from ..models import AppPermission, User, UserGroup

group_admin_bp = Blueprint("group_admin", __name__)

APP_DEFINITIONS = [
    ("calendar", "Calendar chung"),
    ("schedule", "Thời khóa biểu"),
    ("todo", "Công việc"),
    ("dashboard", "Dashboard quản trị"),
    ("bot_admin", "Bot Admin"),
]


@group_admin_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if not current_user.is_admin:
        flash("Bạn không có quyền truy cập.", "error")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        description = (request.form.get("description") or "").strip()
        if not name:
            flash("Vui lòng nhập tên group.", "error")
            return redirect(url_for("group_admin.index"))
        if UserGroup.query.filter_by(name=name).first():
            flash("Tên group đã tồn tại.", "error")
            return redirect(url_for("group_admin.index"))
        g = UserGroup(name=name, description=description or None)
        db.session.add(g)
        db.session.flush()
        # tạo permission mặc định: off
        for key, _label in APP_DEFINITIONS:
            db.session.add(AppPermission(group_id=g.id, app_key=key, can_access=False))
        db.session.commit()
        flash("Đã tạo group mới.", "success")
        return redirect(url_for("group_admin.index"))

    groups = UserGroup.query.order_by(UserGroup.id.asc()).all()
    return render_template("group_admin/index.html", groups=groups)


@group_admin_bp.route("/<int:id>", methods=["GET", "POST"])
@login_required
def detail(id: int):
    if not current_user.is_admin:
        flash("Bạn không có quyền truy cập.", "error")
        return redirect(url_for("main.dashboard"))

    group = UserGroup.query.get_or_404(id)

    if request.method == "POST":
        # cập nhật quyền app
        for app_key, _label in APP_DEFINITIONS:
            field = f"app_{app_key}"
            can = request.form.get(field) == "on"
            perm = AppPermission.query.filter_by(group_id=group.id, app_key=app_key).first()
            if not perm:
                perm = AppPermission(group_id=group.id, app_key=app_key, can_access=can)
                db.session.add(perm)
            else:
                perm.can_access = can

        # cập nhật user trong group
        selected_ids = {
            int(uid)
            for uid in request.form.getlist("users")
            if uid.isdigit()
        }
        all_users = User.query.order_by(User.id.asc()).all()
        group.users.clear()
        for u in all_users:
            if u.id in selected_ids:
                group.users.append(u)

        db.session.commit()
        flash("Đã lưu cấu hình group.", "success")
        return redirect(url_for("group_admin.detail", id=group.id))

    # view
    perms = {p.app_key: p.can_access for p in group.app_permissions}
    all_users = User.query.order_by(User.id.asc()).all()
    member_ids = {u.id for u in group.users}
    return render_template(
        "group_admin/detail.html",
        group=group,
        app_definitions=APP_DEFINITIONS,
        perms=perms,
        users=all_users,
        member_ids=member_ids,
    )


@group_admin_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id: int):
    if not current_user.is_admin:
        flash("Bạn không có quyền truy cập.", "error")
        return redirect(url_for("main.dashboard"))
    group = UserGroup.query.get_or_404(id)
    if group.name == "default":
        flash("Không thể xóa group mặc định.", "error")
        return redirect(url_for("group_admin.index"))
    db.session.delete(group)
    db.session.commit()
    flash("Đã xóa group.", "success")
    return redirect(url_for("group_admin.index"))

