"""Price alert service — CRUD + on-demand check."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session as DBSession

from app.models.price_alert import PriceAlert
from app.models.service import Service


MAX_ALERTS_PER_USER = 20


def list_alerts(db: DBSession, *, user_id: str, active_only: bool = False) -> list[PriceAlert]:
    q = db.query(PriceAlert).filter(PriceAlert.user_id == user_id)
    if active_only:
        q = q.filter(PriceAlert.active.is_(True))
    return q.order_by(PriceAlert.created_at.desc()).all()


def get_alert(db: DBSession, *, user_id: str, alert_id: str) -> PriceAlert | None:
    return (
        db.query(PriceAlert)
        .filter(PriceAlert.id == alert_id, PriceAlert.user_id == user_id)
        .one_or_none()
    )


def create_alert(
    db: DBSession,
    *,
    user_id: str,
    service_id: str,
    target_price: float | Decimal,
) -> PriceAlert:
    s = db.query(Service).filter(Service.id == service_id).one_or_none()
    if s is None:
        raise ValueError("service not found")
    target = Decimal(str(target_price))
    if target <= 0:
        raise ValueError("target_price must be > 0")
    if target >= Decimal(str(s.price)):
        raise ValueError("target_price must be below the current price")

    count = (
        db.query(PriceAlert)
        .filter(PriceAlert.user_id == user_id, PriceAlert.active.is_(True))
        .count()
    )
    if count >= MAX_ALERTS_PER_USER:
        raise ValueError(f"max {MAX_ALERTS_PER_USER} active alerts")

    existing = (
        db.query(PriceAlert)
        .filter(
            PriceAlert.user_id == user_id,
            PriceAlert.service_id == service_id,
            PriceAlert.active.is_(True),
        )
        .one_or_none()
    )
    if existing is not None:
        raise ValueError("already have an active alert for this service")

    a = PriceAlert(
        user_id=user_id,
        tenant_id=s.tenant_id,
        service_id=service_id,
        target_price=target,
        active=True,
        last_seen_price=Decimal(str(s.price)),
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def delete_alert(db: DBSession, *, user_id: str, alert_id: str) -> bool:
    a = get_alert(db, user_id=user_id, alert_id=alert_id)
    if a is None:
        return False
    a.active = False
    db.commit()
    return True


def check_alerts(db: DBSession, *, user_id: str) -> list[dict]:
    """Evaluate all active alerts. Return list with current + triggered."""
    now = datetime.now(timezone.utc)
    rows = (
        db.query(PriceAlert)
        .filter(PriceAlert.user_id == user_id, PriceAlert.active.is_(True))
        .all()
    )
    out: list[dict] = []
    for a in rows:
        s = db.query(Service).filter(Service.id == a.service_id).one_or_none()
        if s is None:
            continue
        current = Decimal(str(s.price))
        a.last_checked_at = now
        a.last_seen_price = current
        triggered = current <= Decimal(str(a.target_price))
        if triggered and a.notified_at is None:
            a.notified_at = now
        out.append({
            "id": a.id,
            "service_id": s.id,
            "service_name": s.name,
            "current_price": str(current),
            "target_price": str(a.target_price),
            "currency": s.currency,
            "triggered": triggered,
            "notified_at": a.notified_at.isoformat() if a.notified_at else None,
        })
    db.commit()
    return out
