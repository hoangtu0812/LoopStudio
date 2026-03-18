from datetime import datetime

from ..app import db


class CafeMenuItem(db.Model):
    __tablename__ = "cafe_menu_items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    category = db.Column(db.String(80), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CafeOrder(db.Model):
    __tablename__ = "cafe_orders"

    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="open")  # open/paid
    subtotal = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    payment_method = db.Column(db.String(30), nullable=True)  # cash/bank_transfer
    paid_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("CafeOrderItem", backref="order", cascade="all, delete-orphan")


class CafeOrderItem(db.Model):
    __tablename__ = "cafe_order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("cafe_orders.id"), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey("cafe_menu_items.id"), nullable=True)
    item_name_snapshot = db.Column(db.String(150), nullable=False)
    unit_price_snapshot = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    qty = db.Column(db.Integer, nullable=False, default=1)
    line_total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    kitchen_status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
    )  # pending/cooking/done/served
    note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    menu_item = db.relationship("CafeMenuItem", lazy="joined")
