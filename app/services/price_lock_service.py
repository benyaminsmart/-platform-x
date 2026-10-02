"""Price Lock service — create / check / consume price locks.

Phase 47, Step 1.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.price_lock import PriceLock
from app.models.service import Service


DEFAULT_WINDOW_HOURS = 48
MIN_WINDOW_HOURS = 1
MAX_WINDOW_HOURS = 168  # 7 days


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_active(lock: PriceLock, now: datetime | None = None) -> bool:
    if not lock.active:
        return False
    if lock.consumed_at is not None:
        return False
    n = now or _now()
    exp = lock.expires_at
    if exp is None:
        return False
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp > n


def create_lock(
    db: DBSession,
    *,
    user_id: str,
    service_id: str,
    window_hours: int = DEFAULT_WINDOW_HOURS,
) -> tuple[PriceLock | None, str]:
    """Create (or replace) a price lock. status: 'ok' | 'not_found' | 'bad_window'."""
    if window_hours < MIN_WINDOW_HOURS or window_hours > MAX_WINDOW_HOURS:
        return None, "bad_window"

    s = db.query(Service).filter(Service.id == service_id).one_or_none()
    if s is None or s.status != "active":
        return None, "not_found"

    now = _now()
    expires = now + timedelta(hours=window_hours)

    existing = (
        db.query(PriceLock)
        .filter(PriceLock.user_id == user_id, PriceLock.service_id == service_id)
        .one_or_none()
    )
    if existing is not None:
        existing.locked_price = _round2(Decimal(str(s.price)))
        existing.currency = s.currency
        existing.expires_at = expires
        existing.active = True
        existing.consumed_at = None
        existing.consumed_booking_id = None
        db.commit()
        db.refresh(existing)
        return existing, "ok"

    lock = PriceLock(
        user_id=user_id,
        tenant_id=s.tenant_id,
        service_id=service_id,
        locked_price=_round2(Decimal(str(s.price))),
        currency=s.currency,
        active=True,
        expires_at=expires,
    )
    db.add(lock)
    db.commit()
    db.refresh(lock)
    return lock, "ok"


def get_active_lock(
    db: DBSession, *, user_id: str, service_id: str
) -> PriceLock | None:
    row = (
        db.query(PriceLock)
        .filter(PriceLock.user_id == user_id, PriceLock.service_id == service_id)
        .one_or_none()
    )
    if row is None:
        return None
    if not _is_active(row):
        return None
    return row


def list_locks(db: DBSession, *, user_id: str, active_only: bool = True) -> list[dict]:
    q = db.query(PriceLock).filter(PriceLock.user_id == user_id)
    if active_only:
        q = q.filter(PriceLock.active == True)  # noqa: E712
    rows = q.order_by(PriceLock.created_at.desc()).all()

    now = _now()
    # Batch-fetch services once (avoids N+1)
    service_ids = list({row.service_id for row in rows if row.service_id})
    services = (
        db.query(Service).filter(Service.id.in_(service_ids)).all()
        if service_ids else []
    )
    service_map = {s.id: s for s in services}

    out: list[dict] = []
    for row in rows:
        s = service_map.get(row.service_id)
        current_price = float(s.price) if s is not None else None
        out.append({
            "id": row.id,
            "service_id": row.service_id,
            "service_name": s.name if s is not None else "—",
            "tenant_id": row.tenant_id,
            "locked_price": float(row.locked_price),
            "current_price": current_price,
            "currency": row.currency,
            "active": _is_active(row, now),
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        })
    return out


def consume_lock(
    db: DBSession, *, user_id: str, service_id: str, booking_id: str
) -> tuple[Decimal | None, str]:
    row = (
        db.query(PriceLock)
        .filter(PriceLock.user_id == user_id, PriceLock.service_id == service_id)
        .one_or_none()
    )
    if row is None:
        return None, "not_found"
    if not _is_active(row):
        return None, "not_active"

    b = db.query(Booking).filter(Booking.id == booking_id).one_or_none()
    if b is None or b.user_id != user_id:
        return None, "not_found"

    row.active = False
    row.consumed_at = _now()
    row.consumed_booking_id = booking_id
    db.commit()
    return row.locked_price, "ok"


def delete_lock(db: DBSession, *, user_id: str, lock_id: str) -> bool:
    row = (
        db.query(PriceLock)
        .filter(PriceLock.id == lock_id, PriceLock.user_id == user_id)
        .one_or_none()
    )
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True
