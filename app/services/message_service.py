"""Message service — thread-based guest ↔ business messaging."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.message import Message


def _now():
    return datetime.now(timezone.utc)


def thread_for_booking(booking_id: str) -> str:
    """For now, thread_id = booking_id."""
    return booking_id


def list_thread_messages(db: DBSession, *, tenant_id: str, thread_id: str, limit: int = 200) -> list[Message]:
    return (
        db.query(Message)
        .filter(Message.tenant_id == tenant_id, Message.thread_id == thread_id)
        .order_by(Message.created_at.asc())
        .limit(max(1, min(int(limit), 500)))
        .all()
    )


def send_message(
    db: DBSession,
    *,
    tenant_id: str,
    thread_id: str,
    sender_role: str,
    body: str,
    sender_user_id: str | None = None,
    booking_id: str | None = None,
) -> Message:
    body = (body or "").strip()
    if not body:
        raise ValueError("body is required")
    if sender_role not in ("user", "business"):
        raise ValueError("sender_role must be 'user' or 'business'")

    m = Message(
        tenant_id=tenant_id,
        thread_id=thread_id,
        booking_id=booking_id,
        sender_user_id=sender_user_id,
        sender_role=sender_role,
        body=body,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def mark_read_for_user(db: DBSession, *, tenant_id: str, thread_id: str) -> int:
    rows = (
        db.query(Message)
        .filter(
            Message.tenant_id == tenant_id,
            Message.thread_id == thread_id,
            Message.sender_role == "business",
            Message.read_at_user.is_(None),
        )
        .all()
    )
    now = _now()
    for r in rows:
        r.read_at_user = now
    db.commit()
    return len(rows)


def mark_read_for_business(db: DBSession, *, tenant_id: str, thread_id: str) -> int:
    rows = (
        db.query(Message)
        .filter(
            Message.tenant_id == tenant_id,
            Message.thread_id == thread_id,
            Message.sender_role == "user",
            Message.read_at_business.is_(None),
        )
        .all()
    )
    now = _now()
    for r in rows:
        r.read_at_business = now
    db.commit()
    return len(rows)


def user_threads(db: DBSession, *, tenant_id: str, user_id: str) -> list[dict]:
    """Return user's threads (grouped by booking)."""
    # Get user's bookings for this tenant
    bookings = (
        db.query(Booking)
        .filter(Booking.tenant_id == tenant_id, Booking.user_id == user_id)
        .all()
    )
    out: list[dict] = []
    for b in bookings:
        last = (
            db.query(Message)
            .filter(Message.tenant_id == tenant_id, Message.thread_id == b.id)
            .order_by(Message.created_at.desc())
            .first()
        )
        unread = (
            db.query(Message)
            .filter(
                Message.tenant_id == tenant_id,
                Message.thread_id == b.id,
                Message.sender_role == "business",
                Message.read_at_user.is_(None),
            )
            .count()
        )
        out.append({
            "thread_id": b.id,
            "booking_id": b.id,
            "service_name": b.service_name,
            "check_in": str(b.check_in),
            "unread": int(unread),
            "last_message": (last.body[:100] if last else None),
            "last_at": (last.created_at.isoformat() if last and last.created_at else None),
        })
    # sort: most recent first (with last_at null last)
    out.sort(key=lambda x: (x["last_at"] or ""), reverse=True)
    return out


def business_threads(db: DBSession, *, tenant_id: str, limit: int = 100) -> list[dict]:
    """Return threads on the business side."""
    rows = (
        db.query(Booking)
        .filter(Booking.tenant_id == tenant_id)
        .order_by(Booking.created_at.desc())
        .limit(max(1, min(int(limit), 200)))
        .all()
    )
    out: list[dict] = []
    for b in rows:
        last = (
            db.query(Message)
            .filter(Message.tenant_id == tenant_id, Message.thread_id == b.id)
            .order_by(Message.created_at.desc())
            .first()
        )
        unread = (
            db.query(Message)
            .filter(
                Message.tenant_id == tenant_id,
                Message.thread_id == b.id,
                Message.sender_role == "user",
                Message.read_at_business.is_(None),
            )
            .count()
        )
        out.append({
            "thread_id": b.id,
            "booking_id": b.id,
            "customer_id": b.user_id,
            "service_name": b.service_name,
            "check_in": str(b.check_in),
            "unread": int(unread),
            "last_message": (last.body[:100] if last else None),
            "last_at": (last.created_at.isoformat() if last and last.created_at else None),
        })
    out.sort(key=lambda x: (x["last_at"] or ""), reverse=True)
    return out
