"""Booking service — DB operations for bookings."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.schemas.booking import BookingCreate

# Statuses a user may still cancel
_CANCELLABLE = {"pending", "confirmed"}


def create_booking(
    db: DBSession,
    *,
    tenant_id: str,
    user_id: str,
    payload: BookingCreate,
) -> Booking:
    """Create a booking and compute total_amount."""
    total = (payload.amount - payload.discount).quantize(Decimal("0.01"))
    booking = Booking(
        tenant_id=tenant_id,
        user_id=user_id,
        booking_type=payload.booking_type,
        service_id=payload.service_id,
        service_name=payload.service_name,
        check_in=payload.check_in,
        check_out=payload.check_out,
        guests=payload.guests,
        amount=payload.amount,
        discount=payload.discount,
        total_amount=total,
        currency=payload.currency,
        status="pending",
        payment_status="pending",
        referral_code=payload.referral_code,
        notes=payload.notes,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_booking(
    db: DBSession, *, tenant_id: str, user_id: str, booking_id: str
) -> Booking | None:
    """Return a booking owned by the user."""
    stmt = select(Booking).where(
        Booking.id == booking_id,
        Booking.tenant_id == tenant_id,
        Booking.user_id == user_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def list_bookings(
    db: DBSession,
    *,
    tenant_id: str,
    user_id: str,
    status: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[Booking], int]:
    """Return (bookings, total_count) with filters and pagination."""
    filters = [Booking.tenant_id == tenant_id, Booking.user_id == user_id]
    if status:
        filters.append(Booking.status == status)
    if from_date:
        filters.append(Booking.check_in >= from_date)
    if to_date:
        filters.append(Booking.check_in <= to_date)

    total = db.execute(
        select(func.count()).select_from(Booking).where(*filters)
    ).scalar_one()

    stmt = (
        select(Booking)
        .where(*filters)
        .order_by(Booking.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = list(db.execute(stmt).scalars().all())
    return items, total


def cancel_booking(
    db: DBSession, *, tenant_id: str, user_id: str, booking_id: str
) -> Booking | None:
    """Cancel a booking if allowed. Returns None if not found.

    Raises ValueError if the booking is not in a cancellable state.
    """
    booking = get_booking(db, tenant_id=tenant_id, user_id=user_id, booking_id=booking_id)
    if booking is None:
        return None
    if booking.status not in _CANCELLABLE:
        raise ValueError(f"Booking in status '{booking.status}' cannot be cancelled")
    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(booking)
    return booking
