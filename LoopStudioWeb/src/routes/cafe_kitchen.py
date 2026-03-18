"""Màn hình bếp cho cafe (polling realtime)."""
from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import login_required

from ..app import db
from ..models import CafeOrder, CafeOrderItem

cafe_kitchen_bp = Blueprint("cafe_kitchen", __name__)

KITCHEN_STATUSES = ["pending", "cooking", "done", "served"]


def _get_kitchen_items():
    items = (
        CafeOrderItem.query.join(CafeOrder, CafeOrderItem.order_id == CafeOrder.id)
        .filter(
            CafeOrder.status == "open",
            CafeOrderItem.kitchen_status.in_(KITCHEN_STATUSES),
        )
        .order_by(CafeOrderItem.created_at.asc())
        .all()
    )
    columns = {k: [] for k in KITCHEN_STATUSES}
    for item in items:
        key = item.kitchen_status if item.kitchen_status in columns else "pending"
        columns[key].append(item)
    return columns


@cafe_kitchen_bp.route("/", methods=["GET"])
@login_required
def index():
    return render_template("cafe/kitchen.html", columns=_get_kitchen_items())


@cafe_kitchen_bp.route("/panel", methods=["GET"])
@login_required
def panel():
    # Endpoint này dùng cho partial refresh (polling). Nếu mở trực tiếp trên browser
    # thì chuyển về trang bếp đầy đủ để tránh giao diện "thô".
    if request.headers.get("HX-Request") != "true":
        return redirect(url_for("cafe_kitchen.index"))
    return render_template("cafe/_kitchen_panel.html", columns=_get_kitchen_items())


@cafe_kitchen_bp.route("/item/<int:item_id>/status", methods=["POST"])
@login_required
def update_status(item_id: int):
    item = CafeOrderItem.query.get_or_404(item_id)
    new_status = (request.form.get("status") or "").strip()
    if new_status in KITCHEN_STATUSES:
        item.kitchen_status = new_status
        db.session.commit()
    next_url = request.form.get("next_url") or url_for("cafe_kitchen.index")
    return redirect(next_url)
