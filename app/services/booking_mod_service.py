"""Booking modification service — change dates with policy + refund recalc.

Design (Wave 1):
- User can modify check_in / check_out before check-in.
- If modification happens within 7 days of the NEW check-in and the NEW
  window overlaps existing bookings on same service, reject.
- Price delta: if service has a per-night price, recalculate total:
    new_total = price * nights
  For services without capacity, or when client provides explicit amount,
  we keep the original amount and just change dates.
- Refund / extra charge: computed but not executed (payment production
  is a later phase). Store the delta in the booking notes for audit.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.service import Service


CANCELLABLE_STATUSES = {"pending", "confirmed"}
_EXCLUDED_STATUSES = ("cancelled", "checked_out", "no_show")


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def can_modify(booking: Booking, *, today: date | None = None) -> tuple[bool, str]:
    """Return (allowed, reason)."""
    today = today or date.today()
    if booking.status not in CANCELLABLE_STATUSES:
        return False, f"Booking in status '{booking.status}' cannot be modified"
    if booking.check_in <= today:
        return False, "Cannot modify a booking that has already started"
    return True, "OK"


def _overlaps_existing(
    db: DBSession,
    *,
    booking: Booking,
    new_ci: date,
    new_co: date,
) -> bool:
    """Check if the new window overlaps existing active bookings on same service.

    We treat service.capacity as 1 for the overlap check on this booking's
    own service line (no double-booking of the same booking).
    """
    if not booking.service_id:
        return False
    rows = (
        db.query(Booking)
        .filter(
            Booking.service_id == booking.service_id,
            Booking.id != booking.id,
            Booking.status.notin_(_EXCLUDED_STATUSES),
            Booking.check_in < new_co,
        )
        .all()
    )
    for b in rows:
        end = b.check_out or (b.check_in + (date.resolution if hasattr(date, 'resolution') else __import__('datetime').timedelta(days=1)))
        # simpler: use datetime timedelta
        from datetime import timedelta as _td
        end = b.check_out or (b.check_in + _td(days=1))
        if end > new_ci:
            return True
    return False


def modify_booking(
    db: DBSession,
    *,
    booking: Booking,
    new_check_in: date,
    new_check_out: date | None,
    today: date | None = None,
) -> dict:
    """Modify dates. Return {'ok', 'reason', 'delta_amount', 'new_total'}.

    Raises ValueError on invalid input; returns {'ok': False} on policy rejection.
    """
    today = today or date.today()
    allowed, reason = can_modify(booking, today=today)
    if not allowed:
        return {"ok": False, "reason": reason}

    if new_check_out is not None and new_check_out <= new_check_in:
        raise ValueError("new_check_out must be after new_check_in")

    if new_check_in <= today:
        raise ValueError("new_check_in must be in the future")

    if _overlaps_existing(db, booking=booking, new_ci=new_check_in, new_co=new_check_out or new_check_in):
        return {"ok": False, "reason": "The requested dates overlap another booking for this service"}

    # Price recalculation
    delta_amount = Decimal("0.00")
    new_total = Decimal(str(booking.total_amount or 0))

    if booking.service_id:
        s = db.query(Service).filter(Service.id == booking.service_id).one_or_none()
        if s is not None and new_check_out is not None and s.capacity is not None:
            nights = (new_check_out - new_check_in).days
            if nights > 0:
                price = Decimal(str(s.price))
                calc_total = _round2(price * Decimal(nights))
                delta_amount = _round2(calc_total - Decimal(str(booking.total_amount or 0)))
                new_total = calc_total

    old_ci, old_co = booking.check_in, booking.check_out

    booking.check_in = new_check_in
    booking.check_out = new_check_out
    booking.total_amount = new_total

    # Audit note
    tag = (
        f"[modified {datetime.now(timezone.utc).isoformat()}] "
        f"dates: {old_ci}->{new_check_in}, {old_co}->{new_check_out}, "
        f"delta={delta_amount}"
    )
    booking.notes = ((booking.notes or "") + "\n" + tag).strip()

    db.add(booking)
    db.commit()
    db.refresh(booking)

    return {
        "ok": True,
        "booking_id": booking.id,
        "old_check_in": str(old_ci),
        "new_check_in": str(new_check_in),
        "old_check_out": str(old_co) if old_co else None,
        "new_check_out": str(new_check_out) if new_check_out else None,
        "delta_amount": str(delta_amount),
        "new_total": str(new_total),
        "currency": booking.currency,
    }
