"""Cancellation service — cancellation policy + refund estimation.

Design (Wave 0):
- Deterministic policy based on days-before-check-in.
- Policy (per booking):
    > 7 days before:    100% refund (full)
    3-7 days before:     50% refund (partial)
    < 72h before:         0% refund (no refund)
- Actual refund execution is deferred to Payment production (Phase 10/31).
  Here we only compute the *policy* outcome and mark cancellation.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.core.logging_config import get_logger
from app.models.tenant import Tenant
from app.models.user import User


CANCELLABLE_STATUSES = {"pending", "confirmed"}



logger = get_logger(__name__)

def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_refund_policy(
    booking: Booking,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Return the refund outcome for a booking if cancelled now.

    {
      "days_until_check_in": int,
      "refund_pct": int (0, 50, 100),
      "refund_amount": str,
      "policy_label": "full" | "partial" | "none",
      "reason": str,
    }
    """
    today = today or date.today()
    days_until = (booking.check_in - today).days
    total = Decimal(str(booking.total_amount or 0))

    if days_until > 7:
        pct, label, reason = 100, "full", "More than 7 days before check-in."
    elif days_until >= 3:
        pct, label, reason = 50, "partial", "Between 3 and 7 days before check-in."
    else:
        pct, label, reason = 0, "none", "Less than 72 hours before check-in."

    refund = _round2(total * Decimal(pct) / Decimal(100))
    return {
        "days_until_check_in": days_until,
        "refund_pct": pct,
        "refund_amount": str(refund),
        "policy_label": label,
        "reason": reason,
    }


def can_cancel(booking: Booking) -> bool:
    return booking.status in CANCELLABLE_STATUSES


def cancel_booking(
    db: DBSession,
    *,
    booking: Booking,
    by_user: User | None = None,
    by_business: bool = False,
) -> dict[str, Any]:
    """Cancel a booking and record the refund policy outcome.

    Does NOT execute real payment refund (deferred to Phase 10/31).
    Returns:
      {"ok": True, "refund": {...}, "booking_id": str}
    Raises ValueError if booking cannot be cancelled.
    """
    if not can_cancel(booking):
        raise ValueError(f"Booking in status '{booking.status}' cannot be cancelled")

    refund = compute_refund_policy(booking)

    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(timezone.utc)

    # record refund intent in extra
    extra = dict(booking.__dict__.get("extra") or {}) if hasattr(booking, "extra") else {}
    # Booking has no `extra` column — attach to notes instead
    note = booking.notes or ""
    tag = f"[cancelled by {'business' if by_business else 'user'}; refund_policy={refund['policy_label']}; refund_amount={refund['refund_amount']}]"
    booking.notes = (note + "\n" + tag).strip() if note else tag

    # capture service_id + dates BEFORE commit for waitlist hook
    _svc_id = booking.service_id
    _ci = booking.check_in
    _co = booking.check_out

    db.add(booking)
    db.commit()
    # Reverse any rewards earned on this booking (Phase 78, Step 2).
    # Never fails the cancellation (P10).
    try:
        from app.services import reward_reversal as _rr
        _rr.reverse_rewards_for_booking(
            db, booking_id=booking.id, reason="cancellation"
        )
    except Exception:
        logger.warning("Reward reversal hook failed", exc_info=True)
    db.refresh(booking)

    # best-effort waitlist notify (Phase 48, Step 4)
    try:
        from app.services import waitlist_service as _wls
        _wls.try_notify_after_cancel(db, service_id=_svc_id, check_in=_ci, check_out=_co)
    except Exception:
        logger.warning("Waitlist hook failed after cancellation", exc_info=True)

    return {"ok": True, "refund": refund, "booking_id": booking.id}
