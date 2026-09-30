"""Waitlist service — join / list / leave / check availability.

Phase 48, Step 1.

A waitlist is FIFO: entries ordered by created_at ascending. When capacity
frees up (via cancellation or manual call), the earliest active entry for
that service + overlapping date range is marked as "notified".
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.service import Service
from app.models.waitlist_entry import WaitlistEntry


_ACTIVE_BOOKING_STATUSES = {"pending", "confirmed", "paid"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _occupied_units(
    db: DBSession, *, service_id: str, check_in: date, check_out: date
) -> int:
    rows = (
        db.query(Booking)
        .filter(Booking.service_id == service_id)
        .filter(Booking.status.in_(list(_ACTIVE_BOOKING_STATUSES)))
        .all()
    )
    used = 0
    for b in rows:
        b_in = b.check_in
        b_out = b.check_out or b.check_in
        if b_out <= check_in or b_in >= check_out:
            continue
        used += 1
    return used


def is_full(
    db: DBSession, *, service_id: str, check_in: date, check_out: date
) -> bool:
    s = db.query(Service).filter(Service.id == service_id).one_or_none()
    if s is None:
        return False
    cap = s.capacity if s.capacity and s.capacity > 0 else 1
    return _occupied_units(db, service_id=service_id,
                           check_in=check_in, check_out=check_out) >= cap


def join(
    db: DBSession,
    *,
    user_id: str,
    service_id: str,
    check_in: date,
    check_out: date,
    guests: int = 1,
) -> tuple[WaitlistEntry | None, str]:
    """status: 'ok' | 'already' | 'not_full' | 'not_found' | 'bad_dates'."""
    if check_out <= check_in:
        return None, "bad_dates"

    s = db.query(Service).filter(Service.id == service_id).one_or_none()
    if s is None or s.status != "active":
        return None, "not_found"

    if not is_full(db, service_id=service_id, check_in=check_in, check_out=check_out):
        return None, "not_full"

    existing = (
        db.query(WaitlistEntry)
        .filter(
            WaitlistEntry.user_id == user_id,
            WaitlistEntry.service_id == service_id,
            WaitlistEntry.check_in == check_in,
            WaitlistEntry.check_out == check_out,
        )
        .one_or_none()
    )
    if existing is not None and existing.active:
        return existing, "already"

    pos = (
        db.query(WaitlistEntry)
        .filter(
            WaitlistEntry.service_id == service_id,
            WaitlistEntry.check_in == check_in,
            WaitlistEntry.check_out == check_out,
            WaitlistEntry.active == True,  # noqa: E712
        )
        .count()
    ) + 1

    if existing is not None:
        existing.active = True
        existing.guests = guests
        existing.notified_at = None
        existing.position_at_join = pos
        db.commit()
        db.refresh(existing)
        return existing, "ok"

    row = WaitlistEntry(
        user_id=user_id,
        tenant_id=s.tenant_id,
        service_id=service_id,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        active=True,
        position_at_join=pos,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, "ok"


def list_entries(db: DBSession, *, user_id: str, active_only: bool = True) -> list[dict]:
    from app.models.tenant import Tenant

    q = db.query(WaitlistEntry).filter(WaitlistEntry.user_id == user_id)
    if active_only:
        q = q.filter(WaitlistEntry.active == True)  # noqa: E712
    rows = q.order_by(WaitlistEntry.created_at.desc()).all()

    out: list[dict] = []
    for r in rows:
        s = db.query(Service).filter(Service.id == r.service_id).one_or_none()
        t = db.query(Tenant).filter(Tenant.id == r.tenant_id).one_or_none()
        pos = None
        if r.active:
            pos = (
                db.query(WaitlistEntry)
                .filter(
                    WaitlistEntry.service_id == r.service_id,
                    WaitlistEntry.check_in == r.check_in,
                    WaitlistEntry.check_out == r.check_out,
                    WaitlistEntry.active == True,  # noqa: E712
                    WaitlistEntry.created_at <= r.created_at,
                )
                .count()
            )
        out.append({
            "id": r.id,
            "service_id": r.service_id,
            "service_name": s.name if s is not None else "—",
            "tenant_slug": t.slug if t is not None else None,
            "tenant_name": t.name if t is not None else "—",
            "check_in": r.check_in.isoformat() if r.check_in else None,
            "check_out": r.check_out.isoformat() if r.check_out else None,
            "guests": r.guests,
            "active": bool(r.active),
            "position": pos,
            "notified_at": r.notified_at.isoformat() if r.notified_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return out


def leave(db: DBSession, *, user_id: str, entry_id: str) -> bool:
    row = (
        db.query(WaitlistEntry)
        .filter(WaitlistEntry.id == entry_id, WaitlistEntry.user_id == user_id)
        .one_or_none()
    )
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def check_and_notify(
    db: DBSession, *, service_id: str, check_in: date, check_out: date
) -> dict | None:
    if is_full(db, service_id=service_id, check_in=check_in, check_out=check_out):
        return None

    first = (
        db.query(WaitlistEntry)
        .filter(
            WaitlistEntry.service_id == service_id,
            WaitlistEntry.check_in == check_in,
            WaitlistEntry.check_out == check_out,
            WaitlistEntry.active == True,  # noqa: E712
            WaitlistEntry.notified_at == None,  # noqa: E711
        )
        .order_by(WaitlistEntry.created_at.asc())
        .first()
    )
    if first is None:
        return None

    first.notified_at = _now()
    db.commit()
    db.refresh(first)
    return {
        "entry_id": first.id,
        "user_id": first.user_id,
        "service_id": first.service_id,
        "check_in": first.check_in.isoformat(),
        "check_out": first.check_out.isoformat(),
        "notified_at": first.notified_at.isoformat() if first.notified_at else None,
    }

def try_notify_after_cancel(db: DBSession, *, service_id: str | None,
                            check_in, check_out) -> dict | None:
    """Best-effort notify after a booking was cancelled. Never raises.

    Safe to call from cancellation paths; if anything fails, returns None.
    """
    if service_id is None or check_in is None or check_out is None:
        return None
    try:
        return check_and_notify(
            db, service_id=service_id, check_in=check_in, check_out=check_out
        )
    except Exception:
        return None
