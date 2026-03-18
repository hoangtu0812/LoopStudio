"""Cafe POS: mở bàn, tạo order, thêm món, thanh toán và in hóa đơn."""
from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..app import db
from ..models import CafeMenuItem, CafeOrder, CafeOrderItem

cafe_order_bp = Blueprint("cafe_order", __name__)


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def _query_menu_items(q: str):
    menu_query = CafeMenuItem.query.filter(CafeMenuItem.is_active.is_(True))
    if q:
        for token in [t for t in q.split() if t]:
            menu_query = menu_query.filter(CafeMenuItem.name.ilike(f"%{token}%"))
    return menu_query.order_by(CafeMenuItem.category.asc(), CafeMenuItem.name.asc()).all()


def _recalc_order_subtotal(order: CafeOrder) -> None:
    subtotal = Decimal("0")
    for item in order.items:
        subtotal += _to_decimal(item.line_total)
    order.subtotal = subtotal


def _is_htmx_request() -> bool:
    return request.headers.get("HX-Request") == "true"


def _render_order_updates(selected_order_id: int):
    open_orders = CafeOrder.query.filter_by(status="open").order_by(CafeOrder.created_at.desc()).all()
    selected_order = CafeOrder.query.filter_by(id=selected_order_id, status="open").first()
    return render_template(
        "cafe/_order_updates.html",
        open_orders=open_orders,
        selected_order=selected_order,
    )


@cafe_order_bp.route("/", methods=["GET"])
@login_required
def index():
    q = (request.args.get("q") or "").strip()
    selected_order_id = request.args.get("order_id", type=int)

    menu_items = _query_menu_items(q)

    open_orders = CafeOrder.query.filter_by(status="open").order_by(CafeOrder.created_at.desc()).all()
    selected_order = None
    if selected_order_id:
        selected_order = CafeOrder.query.filter_by(id=selected_order_id, status="open").first()
    if not selected_order and open_orders:
        selected_order = open_orders[0]

    return render_template(
        "cafe/order.html",
        menu_items=menu_items,
        open_orders=open_orders,
        selected_order=selected_order,
        q=q,
    )


@cafe_order_bp.route("/history", methods=["GET"])
@login_required
def history():
    paid_orders = CafeOrder.query.filter_by(status="paid").order_by(CafeOrder.paid_at.desc()).all()
    return render_template("cafe/history.html", paid_orders=paid_orders)


@cafe_order_bp.route("/menu-panel", methods=["GET"])
@login_required
def menu_panel():
    q = (request.args.get("q") or "").strip()
    selected_order_id = request.args.get("order_id", type=int)
    selected_order = None
    if selected_order_id:
        selected_order = CafeOrder.query.filter_by(id=selected_order_id, status="open").first()
    menu_items = _query_menu_items(q)
    return render_template("cafe/_menu_items.html", menu_items=menu_items, selected_order=selected_order)


@cafe_order_bp.route("/open-table", methods=["POST"])
@login_required
def open_table():
    table_name = (request.form.get("table_name") or "").strip()
    if not table_name:
        flash("Vui lòng nhập tên bàn.", "error")
        return redirect(url_for("cafe_order.index"))

    order = CafeOrder(table_name=table_name, status="open")
    db.session.add(order)
    db.session.commit()
    flash(f"Đã mở bàn '{table_name}'.", "success")
    return redirect(url_for("cafe_order.index", order_id=order.id))


@cafe_order_bp.route("/<int:order_id>/add-item", methods=["POST"])
@login_required
def add_item(order_id: int):
    order = CafeOrder.query.get_or_404(order_id)
    if order.status != "open":
        flash("Bàn này đã thanh toán.", "warning")
        return redirect(url_for("cafe_order.index", order_id=order.id))

    menu_item_id = request.form.get("menu_item_id", type=int)
    qty = max(1, request.form.get("qty", type=int) or 1)
    note = (request.form.get("note") or "").strip()
    menu_item = CafeMenuItem.query.get_or_404(menu_item_id)

    unit_price = _to_decimal(menu_item.price)
    line_total = unit_price * qty
    order_item = CafeOrderItem(
        order_id=order.id,
        menu_item_id=menu_item.id,
        item_name_snapshot=menu_item.name,
        unit_price_snapshot=unit_price,
        qty=qty,
        line_total=line_total,
        kitchen_status="pending",
        note=note or None,
    )
    db.session.add(order_item)
    db.session.flush()

    _recalc_order_subtotal(order)
    db.session.commit()
    if _is_htmx_request():
        return _render_order_updates(order.id)
    flash(f"Đã thêm {qty} x {menu_item.name}.", "success")
    return redirect(url_for("cafe_order.index", order_id=order.id))


@cafe_order_bp.route("/<int:order_id>/close", methods=["POST"])
@login_required
def close_table(order_id: int):
    order = CafeOrder.query.get_or_404(order_id)
    if order.status != "open":
        flash("Chỉ có thể đóng bàn đang mở.", "warning")
        return redirect(url_for("cafe_order.index"))
    order.status = "canceled"
    db.session.commit()
    flash(f"Đã đóng bàn '{order.table_name}'.", "success")
    return redirect(url_for("cafe_order.index"))


@cafe_order_bp.route("/<int:order_id>/remove-item/<int:item_id>", methods=["POST"])
@login_required
def remove_item(order_id: int, item_id: int):
    order = CafeOrder.query.get_or_404(order_id)
    item = CafeOrderItem.query.get_or_404(item_id)
    if item.order_id != order.id:
        flash("Món không thuộc bàn này.", "error")
        return redirect(url_for("cafe_order.index", order_id=order.id))
    if order.status != "open":
        flash("Bàn này đã thanh toán.", "warning")
        return redirect(url_for("cafe_order.index", order_id=order.id))

    db.session.delete(item)
    db.session.flush()
    _recalc_order_subtotal(order)
    db.session.commit()
    if _is_htmx_request():
        return _render_order_updates(order.id)
    flash("Đã xóa món khỏi order.", "success")
    return redirect(url_for("cafe_order.index", order_id=order.id))


@cafe_order_bp.route("/<int:order_id>/checkout", methods=["POST"])
@login_required
def checkout(order_id: int):
    order = CafeOrder.query.get_or_404(order_id)
    if order.status == "paid":
        flash("Bàn này đã thanh toán trước đó.", "info")
        return redirect(url_for("cafe_order.invoice", order_id=order.id))

    payment_method = (request.form.get("payment_method") or "").strip()
    if payment_method not in {"cash", "bank_transfer"}:
        flash("Phương thức thanh toán không hợp lệ.", "error")
        return redirect(url_for("cafe_order.index", order_id=order.id))
    if not order.items:
        flash("Bàn chưa có món để thanh toán.", "warning")
        return redirect(url_for("cafe_order.index", order_id=order.id))

    _recalc_order_subtotal(order)
    order.payment_method = payment_method
    order.status = "paid"
    from datetime import datetime

    order.paid_at = datetime.utcnow()
    db.session.commit()
    flash("Thanh toán thành công.", "success")
    return redirect(url_for("cafe_order.invoice", order_id=order.id))


@cafe_order_bp.route("/<int:order_id>/invoice")
@login_required
def invoice(order_id: int):
    order = CafeOrder.query.get_or_404(order_id)
    return render_template("cafe/invoice.html", order=order)


@cafe_order_bp.route("/<int:order_id>/invoice/print")
@login_required
def invoice_print(order_id: int):
    order = CafeOrder.query.get_or_404(order_id)
    return render_template("cafe/invoice.html", order=order)
