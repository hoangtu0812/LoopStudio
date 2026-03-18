"""Service theo dõi uptime website."""
from datetime import datetime, timedelta
import time

import requests
from sqlalchemy import func

from ..app import db
from ..models import NotificationConfig, TelegramChatTarget, UptimeCheck, UptimeSite
from .telegram_service import send_telegram_message


def _resolve_chat_id(cfg, target_map: dict[int, str]) -> str:
    return (target_map.get(cfg.chat_target_id) or cfg.chat_id or "").strip()


def get_uptime_alert_chat_ids() -> list[str]:
    """Lấy danh sách chat nhận cảnh báo uptime down."""
    configs = NotificationConfig.query.filter(
        NotificationConfig.enabled == True,  # noqa: E712
    ).all()
    if not configs:
        return []

    target_map = {
        t.id: t.chat_id
        for t in TelegramChatTarget.query.filter(
            TelegramChatTarget.is_active == True  # noqa: E712
        ).all()
    }

    preferred = {
        _resolve_chat_id(c, target_map)
        for c in configs
        if c.config_type == "uptime_down_alert" and _resolve_chat_id(c, target_map)
    }
    if preferred:
        return sorted(preferred)

    fallback_types = {"todo_daily_digest", "todo_deadline_reminder", "schedule_reminder"}
    fallback = {
        _resolve_chat_id(c, target_map)
        for c in configs
        if c.config_type in fallback_types and _resolve_chat_id(c, target_map)
    }
    return sorted(fallback)


def _build_down_alert_message(site: UptimeSite, status_code: int | None, response_ms: int | None, error_message: str | None) -> str:
    checked_at = datetime.utcnow().strftime("%H:%M:%S %d/%m/%Y")
    response_text = f"{response_ms} ms" if response_ms is not None else "-"
    code_text = str(status_code) if status_code is not None else "-"
    err = (error_message or "Không có chi tiết lỗi.")[:220]
    return (
        "━━━━━━━━━━━━━━━━━━\n"
        "🚨 UPTIME ALERT: SITE DOWN\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"• Website: {site.name}\n"
        f"• URL: {site.url}\n"
        f"• HTTP code: {code_text}\n"
        f"• Response: {response_text}\n"
        f"• Thời điểm: {checked_at}\n"
        f"• Chi tiết: {err}"
    )


def check_site_once(site: UptimeSite) -> UptimeCheck:
    """Check 1 website và lưu kết quả."""
    started = time.perf_counter()
    is_up = False
    status_code = None
    response_ms = None
    error_message = None

    try:
        resp = requests.get(
            site.url,
            timeout=max(site.timeout_seconds, 1),
            allow_redirects=True,
            headers={"User-Agent": "LoopStudioUptimeBot/1.0"},
        )
        status_code = resp.status_code
        response_ms = int((time.perf_counter() - started) * 1000)
        status_ok = status_code == site.expected_status_code
        keyword_ok = True
        if site.keyword:
            keyword_ok = site.keyword in (resp.text or "")
        is_up = status_ok and keyword_ok
        if not is_up and not keyword_ok:
            error_message = f"Không tìm thấy keyword '{site.keyword}'."
        elif not is_up:
            error_message = f"HTTP {status_code} != {site.expected_status_code}."
    except Exception as exc:
        response_ms = int((time.perf_counter() - started) * 1000)
        error_message = str(exc)

    prev_status = site.current_status
    new_status = "up" if is_up else "down"

    check = UptimeCheck(
        site_id=site.id,
        is_up=is_up,
        status_code=status_code,
        response_ms=response_ms,
        error_message=error_message,
        checked_at=datetime.utcnow(),
    )
    db.session.add(check)

    site.current_status = new_status
    site.last_checked_at = check.checked_at
    site.last_response_ms = response_ms
    site.last_error = error_message
    if prev_status != new_status:
        site.last_status_change_at = check.checked_at
    db.session.commit()

    # Chỉ báo động khi vừa chuyển sang DOWN để tránh spam mỗi chu kỳ check.
    if site.is_active and prev_status != "down" and new_status == "down":
        alert_chat_ids = get_uptime_alert_chat_ids()
        if alert_chat_ids:
            alert_msg = _build_down_alert_message(site, status_code, response_ms, error_message)
            for chat_id in alert_chat_ids:
                send_telegram_message(chat_id, alert_msg)
    return check


def check_due_sites() -> int:
    """Check các site đến hạn theo check interval. Trả số site đã check."""
    now = datetime.utcnow()
    checked_count = 0
    sites = UptimeSite.query.filter_by(is_active=True).all()
    for site in sites:
        if not site.last_checked_at:
            check_site_once(site)
            checked_count += 1
            continue
        due_at = site.last_checked_at + timedelta(seconds=max(site.check_interval_seconds, 30))
        if now >= due_at:
            check_site_once(site)
            checked_count += 1
    return checked_count


def cleanup_old_checks(days: int = 7) -> int:
    """Xóa lịch sử check quá cũ để DB gọn nhẹ."""
    cutoff = datetime.utcnow() - timedelta(days=max(days, 1))
    deleted = UptimeCheck.query.filter(UptimeCheck.checked_at < cutoff).delete()
    db.session.commit()
    return deleted


def uptime_percentage_24h(site_id: int) -> float:
    """Tính uptime 24h theo số lần check."""
    since = datetime.utcnow() - timedelta(hours=24)
    total = (
        db.session.query(func.count(UptimeCheck.id))
        .filter(UptimeCheck.site_id == site_id, UptimeCheck.checked_at >= since)
        .scalar()
        or 0
    )
    if total == 0:
        return 0.0
    up_count = (
        db.session.query(func.count(UptimeCheck.id))
        .filter(
            UptimeCheck.site_id == site_id,
            UptimeCheck.checked_at >= since,
            UptimeCheck.is_up == True,  # noqa: E712
        )
        .scalar()
        or 0
    )
    return round((up_count / total) * 100, 1)


def build_uptime_bot_message() -> str:
    """Sinh nội dung cho lệnh /uptime."""
    sites = UptimeSite.query.order_by(UptimeSite.name.asc()).all()
    if not sites:
        return "🛰️ Uptime Monitor\nChưa có website nào được cấu hình."

    lines = ["🛰️ Uptime Monitor", "━━━━━━━━━━━━━━━━━━"]
    for site in sites:
        icon = "🟢" if site.current_status == "up" else ("🔴" if site.current_status == "down" else "⚪")
        uptime24 = uptime_percentage_24h(site.id)
        latency = f"{site.last_response_ms}ms" if site.last_response_ms is not None else "-"
        checked_at = site.last_checked_at.strftime("%H:%M %d/%m") if site.last_checked_at else "-"
        lines.append(
            f"{icon} {site.name}\n"
            f"   • Status: {site.current_status.upper()}\n"
            f"   • Uptime 24h: {uptime24}%\n"
            f"   • Latency: {latency}\n"
            f"   • Last check: {checked_at}"
        )
        if site.last_error and site.current_status != "up":
            lines.append(f"   • Error: {site.last_error[:120]}")
    return "\n".join(lines)
