"""Notification service — DB ops + delivery stub.

Actual sending (SMTP, WhatsApp, etc.) is out of scope for now; we record
notifications and mark them 'sent' immediately for in_app channel.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.models.notification import Notification


def create(
    db: DBSession,
    *,
    tenant_id: str,
    user_id: str,
    channel: str,
    template: str,
    content: str,
    subject: str | None = None,
    metadata: dict | None = None,
) -> Notification:
    """Create a notification row and mark as sent for in_app."""
    now = datetime.now(timezone.utc)
    n = Notification(
        tenant_id=tenant_id,
        user_id=user_id,
        channel=channel,
        template=template,
        subject=subject,
        content=content,
        status="sent" if channel == "in_app" else "pending",
        sent_at=now if channel == "in_app" else None,
        metadata_json=metadata,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def list_for_user(
    db: DBSession,
    *,
    tenant_id: str,
    user_id: str,
    unread_only: bool = False,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[Notification], int]:
    """Return (notifications, total)."""
    filters = [Notification.tenant_id == tenant_id, Notification.user_id == user_id]
    if unread_only:
        filters.append(Notification.read_at.is_(None))

    total = db.execute(
        select(func.count()).select_from(Notification).where(*filters)
    ).scalar_one()

    stmt = (
        select(Notification)
        .where(*filters)
        .order_by(Notification.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all()), total


def get_owned(
    db: DBSession, *, tenant_id: str, user_id: str, notification_id: str
) -> Notification | None:
    return db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.tenant_id == tenant_id,
            Notification.user_id == user_id,
        )
    ).scalar_one_or_none()


def mark_read(
    db: DBSession, *, tenant_id: str, user_id: str, notification_id: str
) -> Notification | None:
    """Mark notification as read. Idempotent."""
    n = get_owned(
        db, tenant_id=tenant_id, user_id=user_id, notification_id=notification_id
    )
    if n is None:
        return None
    if n.read_at is None:
        n.read_at = datetime.now(timezone.utc)
        if n.status not in {"read"}:
            n.status = "read"
        db.commit()
        db.refresh(n)
    return n


def unread_count(db: DBSession, *, tenant_id: str, user_id: str) -> int:
    return db.execute(
        select(func.count()).select_from(Notification).where(
            Notification.tenant_id == tenant_id,
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
    ).scalar_one()

# ---------- Email-specific notification helpers ----------


def _render_email(template_name: str, context: dict) -> str:
    """Render an email template to HTML."""
    from datetime import datetime, timezone
    from pathlib import Path as _Path
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    base_dir = _Path(__file__).resolve().parent.parent
    env = Environment(
        loader=FileSystemLoader(str(base_dir / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tmpl = env.get_template(f"emails/{template_name}")
    context = {**context, "year": datetime.now(timezone.utc).year}
    return tmpl.render(**context)


def send_welcome_email(*, to_email: str, user_name: str, home_url: str) -> bool:
    """Send a welcome email after registration."""
    from app.services import email_service

    html = _render_email(
        "welcome.html",
        {"user_name": user_name, "home_url": home_url},
    )
    return email_service.send_email(
        to=to_email,
        subject="Welcome to Platform-X",
        html=html,
    )


def send_booking_confirmed_email(
    *,
    to_email: str,
    user_name: str,
    tenant_name: str,
    service_name: str,
    check_in: str,
    check_out: str | None,
    guests: int,
    total: str,
    currency: str,
    account_url: str,
) -> bool:
    """Send a booking confirmation email."""
    from app.services import email_service

    html = _render_email(
        "booking_confirmed.html",
        {
            "user_name": user_name,
            "tenant_name": tenant_name,
            "service_name": service_name,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "total": total,
            "currency": currency,
            "account_url": account_url,
        },
    )
    return email_service.send_email(
        to=to_email,
        subject=f"Booking confirmed — {tenant_name}",
        html=html,
    )


def send_password_reset_email(
    *, to_email: str, user_name: str, reset_url: str
) -> bool:
    """Send password reset email."""
    from app.services import email_service

    html = _render_email(
        "password_reset.html",
        {"user_name": user_name, "reset_url": reset_url},
    )
    return email_service.send_email(
        to=to_email,
        subject="Reset your Platform-X password",
        html=html,
    )
