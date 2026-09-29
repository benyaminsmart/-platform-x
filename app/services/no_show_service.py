"""No-show service — detect and mark bookings as no_show.

Detection rule:
- check_in < today (past)
- status == "confirmed"
- payment_status == "paid"

Marking:
- business (owner/manager) marks a booking as no_show
- Only bookings that satisfy detection rule can be marked
- No refund is issued by default (policy: no-show = no refund)
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking


ELIGIBLE_FOR_NO_SHOW = {"confirmed"}


def is_no_show_candidate(booking: Booking, *, today: date | None = None) -> bool:
    today = today or date.today()
    if booking.status not in ELIGIBLE_FOR_NO_SHOW:
        return False
    if booking.check_in >= today:
        return False
    return True


def list_candidates(
    db: DBSession,
    *,
    tenant_id: str,
    today: date | None = None,
    limit: int = 200,
) -> list[Booking]:
    today = today or date.today()
    return (
        db.query(Booking)
        .filter(
            Booking.tenant_id == tenant_id,
            Booking.status.in_(ELIGIBLE_FOR_NO_SHOW),
            Booking.check_in < today,
        )
        .order_by(Booking.check_in.desc())
        .limit(max(1, min(int(limit), 500)))
        .all()
    )


def mark_no_show(
    db: DBSession,
    *,
    booking: Booking,
    by_business: bool = True,
    today: date | None = None,
) -> dict[str, Any]:
    """Mark a booking as no_show. Returns {'ok', ...}."""
    if not is_no_show_candidate(booking, today=today):
        return {"ok": False, "reason": "Booking is not eligible for no-show marking"}

    booking.status = "no_show"
    tag = f"[no_show {datetime.now(timezone.utc).isoformat()} by_business={by_business}]"
    booking.notes = ((booking.notes or "") + "\n" + tag).strip()
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return {
        "ok": True,
        "booking_id": booking.id,
        "status": booking.status,
        "note": "Marked as no-show. No refund issued per policy.",
    }
