"""Uptime monitor routes."""
from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func

from ..app import db
from ..models import UptimeCheck, UptimeSite
from ..services.uptime_service import check_site_once, uptime_percentage_24h

uptime_bp = Blueprint("uptime", __name__)


@uptime_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        url = (request.form.get("url") or "").strip()
        interval = request.form.get("check_interval_seconds", type=int) or 60
        timeout = request.form.get("timeout_seconds", type=int) or 8
        expected_status_code = request.form.get("expected_status_code", type=int) or 200
        keyword = (request.form.get("keyword") or "").strip()

        if not name or not url:
            flash("Vui lòng nhập tên và URL website.", "error")
            return redirect(url_for("uptime.index"))
        if UptimeSite.query.filter_by(url=url).first():
            flash("URL này đã tồn tại trong danh sách theo dõi.", "warning")
            return redirect(url_for("uptime.index"))

        site = UptimeSite(
            name=name,
            url=url,
            check_interval_seconds=max(interval, 30),
            timeout_seconds=max(timeout, 1),
            expected_status_code=expected_status_code,
            keyword=keyword or None,
            is_active=True,
        )
        db.session.add(site)
        db.session.commit()
        flash("Đã thêm website theo dõi uptime.", "success")
        return redirect(url_for("uptime.index", site_id=site.id))

    sites = UptimeSite.query.order_by(UptimeSite.name.asc()).all()
    selected_site_id = request.args.get("site_id", type=int)
    selected_site = None
    if sites:
        selected_site = next((s for s in sites if s.id == selected_site_id), None) or sites[0]
        selected_site_id = selected_site.id

    site_stats = {}
    site_mini_bars = {}
    for site in sites:
        uptime_24h = uptime_percentage_24h(site.id)
        site_stats[site.id] = {"uptime_24h": uptime_24h}
        recent_for_list = (
            UptimeCheck.query.filter_by(site_id=site.id)
            .order_by(UptimeCheck.checked_at.desc())
            .limit(28)
            .all()
        )
        site_mini_bars[site.id] = list(reversed([c.is_up for c in recent_for_list]))

    selected_bars = []
    recent_events = []
    selected_stats = {
        "current_ping": None,
        "avg_ping_24h": None,
        "uptime_24h": 0.0,
        "uptime_30d": 0.0,
    }
    if selected_site:
        selected_recent = (
            UptimeCheck.query.filter_by(site_id=selected_site.id)
            .order_by(UptimeCheck.checked_at.desc())
            .limit(54)
            .all()
        )
        selected_bars = list(reversed(selected_recent))
        recent_events = (
            UptimeCheck.query.filter_by(site_id=selected_site.id)
            .order_by(UptimeCheck.checked_at.desc())
            .limit(30)
            .all()
        )
        since_24h = datetime.utcnow() - timedelta(hours=24)
        since_30d = datetime.utcnow() - timedelta(days=30)
        avg_ping_24h = (
            db.session.query(func.avg(UptimeCheck.response_ms))
            .filter(UptimeCheck.site_id == selected_site.id, UptimeCheck.checked_at >= since_24h)
            .scalar()
        )
        total_30d = (
            db.session.query(func.count(UptimeCheck.id))
            .filter(UptimeCheck.site_id == selected_site.id, UptimeCheck.checked_at >= since_30d)
            .scalar()
            or 0
        )
        up_30d = (
            db.session.query(func.count(UptimeCheck.id))
            .filter(
                UptimeCheck.site_id == selected_site.id,
                UptimeCheck.checked_at >= since_30d,
                UptimeCheck.is_up == True,  # noqa: E712
            )
            .scalar()
            or 0
        )
        uptime_30d = round((up_30d / total_30d) * 100, 2) if total_30d else 0.0
        selected_stats = {
            "current_ping": selected_site.last_response_ms,
            "avg_ping_24h": round(float(avg_ping_24h), 1) if avg_ping_24h is not None else None,
            "uptime_24h": site_stats[selected_site.id]["uptime_24h"],
            "uptime_30d": uptime_30d,
        }

    total_up = sum(1 for s in sites if s.current_status == "up")
    total_down = sum(1 for s in sites if s.current_status == "down")
    total_unknown = sum(1 for s in sites if s.current_status == "unknown")
    total_pause = sum(1 for s in sites if not s.is_active)

    return render_template(
        "uptime/index.html",
        sites=sites,
        selected_site=selected_site,
        selected_site_id=selected_site_id,
        selected_bars=selected_bars,
        recent_events=recent_events,
        selected_stats=selected_stats,
        site_stats=site_stats,
        site_mini_bars=site_mini_bars,
        total_up=total_up,
        total_down=total_down,
        total_unknown=total_unknown,
        total_pause=total_pause,
    )


@uptime_bp.route("/<int:site_id>/toggle", methods=["POST"])
@login_required
def toggle_site(site_id: int):
    site = UptimeSite.query.get_or_404(site_id)
    site.is_active = not site.is_active
    db.session.commit()
    flash("Đã cập nhật trạng thái monitor.", "success")
    selected_site_id = request.form.get("selected_site_id", type=int) or site.id
    return redirect(url_for("uptime.index", site_id=selected_site_id))


@uptime_bp.route("/<int:site_id>/delete", methods=["POST"])
@login_required
def delete_site(site_id: int):
    site = UptimeSite.query.get_or_404(site_id)
    selected_site_id = request.form.get("selected_site_id", type=int)
    db.session.delete(site)
    db.session.commit()
    flash("Đã xóa monitor website.", "success")
    return redirect(url_for("uptime.index", site_id=selected_site_id))


@uptime_bp.route("/<int:site_id>/check-now", methods=["POST"])
@login_required
def check_now(site_id: int):
    site = UptimeSite.query.get_or_404(site_id)
    check_site_once(site)
    flash(f"Đã check thủ công {site.name}.", "success")
    selected_site_id = request.form.get("selected_site_id", type=int) or site.id
    return redirect(url_for("uptime.index", site_id=selected_site_id))


@uptime_bp.route("/<int:site_id>/history")
@login_required
def history(site_id: int):
    site = UptimeSite.query.get_or_404(site_id)
    checks = (
        UptimeCheck.query.filter_by(site_id=site.id)
        .order_by(UptimeCheck.checked_at.desc())
        .limit(200)
        .all()
    )
    return render_template("uptime/history.html", site=site, checks=checks)
