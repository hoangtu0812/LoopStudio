"""Quản trị cafe: menu món và báo cáo doanh thu."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..app import db
from ..models import CafeMenuItem, CafeOrder

cafe_admin_bp = Blueprint("cafe_admin", __name__)


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


@cafe_admin_bp.route("/menu", methods=["GET", "POST"])
@login_required
def menu():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        image_url = (request.form.get("image_url") or "").strip()
        category = (request.form.get("category") or "").strip()
        price_raw = (request.form.get("price") or "0").strip()
        if not name:
            flash("Vui lòng nhập tên món.", "error")
            return redirect(url_for("cafe_admin.menu"))
        try:
            price = Decimal(price_raw)
        except Exception:
            flash("Giá món không hợp lệ.", "error")
            return redirect(url_for("cafe_admin.menu"))
        db.session.add(
            CafeMenuItem(
                name=name,
                image_url=image_url or None,
                price=max(price, Decimal("0")),
                category=category or None,
                is_active=True,
            )
        )
        db.session.commit()
        flash("Đã thêm món mới.", "success")
        return redirect(url_for("cafe_admin.menu"))

    items = CafeMenuItem.query.order_by(CafeMenuItem.category.asc(), CafeMenuItem.name.asc()).all()
    return render_template("cafe/menu.html", items=items)


@cafe_admin_bp.route("/menu/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_menu_item(item_id: int):
    item = CafeMenuItem.query.get_or_404(item_id)
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        image_url = (request.form.get("image_url") or "").strip()
        category = (request.form.get("category") or "").strip()
        price_raw = (request.form.get("price") or "0").strip()
        if not name:
            flash("Tên món không được để trống.", "error")
            return redirect(url_for("cafe_admin.edit_menu_item", item_id=item.id))
        try:
            price = Decimal(price_raw)
        except Exception:
            flash("Giá món không hợp lệ.", "error")
            return redirect(url_for("cafe_admin.edit_menu_item", item_id=item.id))

        item.name = name
        item.image_url = image_url or None
        item.category = category or None
        item.price = max(price, Decimal("0"))
        item.is_active = request.form.get("is_active") == "on"
        db.session.commit()
        flash("Đã cập nhật món.", "success")
        return redirect(url_for("cafe_admin.menu"))
    return render_template("cafe/menu_edit.html", item=item)


@cafe_admin_bp.route("/menu/<int:item_id>/toggle", methods=["POST"])
@login_required
def toggle_menu_item(item_id: int):
    item = CafeMenuItem.query.get_or_404(item_id)
    item.is_active = not item.is_active
    db.session.commit()
    flash("Đã đổi trạng thái món.", "success")
    return redirect(url_for("cafe_admin.menu"))


@cafe_admin_bp.route("/menu/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_menu_item(item_id: int):
    item = CafeMenuItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Đã xóa món.", "success")
    return redirect(url_for("cafe_admin.menu"))


@cafe_admin_bp.route("/dashboard")
@login_required
def dashboard():
    paid_orders = CafeOrder.query.filter_by(status="paid").all()

    today = date.today()
    month_start = today.replace(day=1)

    today_revenue = Decimal("0")
    month_revenue = Decimal("0")
    open_tables = CafeOrder.query.filter_by(status="open").count()

    daily_data = defaultdict(Decimal)
    monthly_data = defaultdict(Decimal)
    item_data = defaultdict(Decimal)

    for order in paid_orders:
        subtotal = _to_decimal(order.subtotal)
        if order.paid_at:
            paid_date = order.paid_at.date()
            daily_data[paid_date.isoformat()] += subtotal
            monthly_key = paid_date.strftime("%Y-%m")
            monthly_data[monthly_key] += subtotal
            if paid_date == today:
                today_revenue += subtotal
            if paid_date >= month_start:
                month_revenue += subtotal
        for item in order.items:
            item_data[item.item_name_snapshot] += _to_decimal(item.line_total)

    # 14 ngày gần nhất
    daily_labels = [(today - timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
    daily_revenue = [float(daily_data.get(k, Decimal("0"))) for k in daily_labels]

    # 12 tháng gần nhất
    month_labels = sorted(monthly_data.keys())[-12:]
    month_revenue_series = [float(monthly_data[k]) for k in month_labels]

    top_items = sorted(item_data.items(), key=lambda x: x[1], reverse=True)[:10]
    top_item_labels = [x[0] for x in top_items]
    top_item_revenue = [float(x[1]) for x in top_items]

    return render_template(
        "cafe/dashboard.html",
        today_revenue=float(today_revenue),
        month_revenue=float(month_revenue),
        open_tables=open_tables,
        paid_orders_count=len(paid_orders),
        daily_labels=daily_labels,
        daily_revenue=daily_revenue,
        month_labels=month_labels,
        month_revenue_series=month_revenue_series,
        top_item_labels=top_item_labels,
        top_item_revenue=top_item_revenue,
    )
