"""Instant Refund AI — propose an AI-adjusted refund on top of base policy.

Phase 54 (Wave 3, Blue-Ocean B5).

Design principles:
- Numbers are computed in Python. AI writes the rationale only.
- Base policy is unchanged (cancellation_service.compute_refund_policy).
- The AI-adjustment is a *recommendation* — never applied automatically.
- Adjustments are bounded by platform caps:
    max +25% above base (never > 100)
    max -25% below base (never < 0)
- Signals used to compute the suggested delta (deterministic):
    - user loyalty tier (from user.tier)
    - tenure (# of past completed bookings by the user, any tenant)
    - notice window (days_until_check_in)
    - booking value (total_amount)
    - whether the user has had prior cancellations in the last 90 days
- The AI receives the base refund and the suggested delta, and writes
  a short rationale. Provider-neutral, with deterministic fallback.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.user import User
from app.services import cancellation_service
from app.services.ai import service as ai_service


SUPPORTED_LANGUAGES = {"en", "ar", "fil", "hi"}
_LANGUAGE_NAMES = {
    "en": "English", "ar": "Arabic (Modern Standard Arabic)",
    "fil": "Filipino (Tagalog)", "hi": "Hindi",
}

# Platform caps for the AI adjustment (percentage points)
MAX_POSITIVE_DELTA = 25
MAX_NEGATIVE_DELTA = 25

# Loyalty tier bonus (points toward positive delta)
_TIER_BONUS = {
    "royal": 15,
    "platinum": 10,
    "gold": 7,
    "silver": 4,
    "welcome": 0,
}


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _past_completed_bookings(db: DBSession, user_id: str) -> int:
    return int(
        db.query(func.count(Booking.id))
        .filter(Booking.user_id == user_id, Booking.status == "confirmed")
        .scalar() or 0
    )


def _recent_cancellations_90d(db: DBSession, user_id: str) -> int:
    since = datetime.now(timezone.utc) - timedelta(days=90)
    return int(
        db.query(func.count(Booking.id))
        .filter(
            Booking.user_id == user_id,
            Booking.status == "cancelled",
            Booking.cancelled_at.isnot(None),
            Booking.cancelled_at >= since,
        )
        .scalar() or 0
    )


def suggest_delta(
    db: DBSession, *, booking: Booking, user: User | None, base_pct: int
) -> dict[str, Any]:
    """Return {delta, signals} for the AI adjustment (percentage points).

    Bounded by platform caps. Never pushes base + delta outside [0, 100].
    """
    signals: dict[str, Any] = {}

    tier = (getattr(user, "tier", None) or "welcome") if user else "welcome"
    signals["tier"] = tier
    delta = _TIER_BONUS.get(tier, 0)

    if user is not None:
        tenure = _past_completed_bookings(db, user.id)
        signals["tenure_bookings"] = tenure
        if tenure >= 10:
            delta += 5
        elif tenure >= 3:
            delta += 2

        recent_cx = _recent_cancellations_90d(db, user.id)
        signals["recent_cancellations_90d"] = recent_cx
        if recent_cx >= 3:
            delta -= 10
        elif recent_cx >= 1:
            delta -= 4

    days_until = (booking.check_in - date.today()).days
    signals["days_until_check_in"] = days_until
    if days_until <= 0:
        delta -= 5

    try:
        amount = float(booking.total_amount or 0)
    except (TypeError, ValueError):
        amount = 0.0
    signals["total_amount"] = round(amount, 2)

    # clamp the raw delta to platform caps
    delta = _clamp(delta, -MAX_NEGATIVE_DELTA, MAX_POSITIVE_DELTA)

    # ensure the final suggested pct stays within [0, 100]
    suggested_pct = _clamp(base_pct + delta, 0, 100)
    # recompute the applied delta after clamping, so we report what we use
    applied_delta = suggested_pct - base_pct

    return {
        "delta": applied_delta,
        "suggested_pct": suggested_pct,
        "signals": signals,
    }


def evaluate(
    db: DBSession,
    *,
    booking: Booking,
    user: User | None,
    language: str = "en",
) -> dict[str, Any]:
    """Return base policy + AI-adjusted recommendation + rationale."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")

    base = cancellation_service.compute_refund_policy(booking)
    base_pct = int(base["refund_pct"])
    total = Decimal(str(booking.total_amount or 0))

    suggestion = suggest_delta(db, booking=booking, user=user, base_pct=base_pct)
    suggested_pct = int(suggestion["suggested_pct"])
    suggested_amount = _round2(total * Decimal(suggested_pct) / Decimal(100))

    lines = [
        f"BOOKING_TOTAL: {total} {booking.currency}",
        f"DAYS_UNTIL_CHECK_IN: {base['days_until_check_in']}",
        f"BASE_POLICY: {base['policy_label']} ({base_pct}%)",
        f"SUGGESTED_REFUND: {suggested_pct}% ({suggested_amount} {booking.currency})",
        f"DELTA_PP: {suggestion['delta']}",
        "SIGNALS:",
    ]
    for k, v in suggestion["signals"].items():
        lines.append(f"  - {k}={v}")

    lang = _LANGUAGE_NAMES.get(language, "English")
    prompt = (
        "You are a customer-fairness analyst for Platform-X. Based ONLY on "
        "the numbers below, write a short, professional rationale (max 3 "
        "sentences) that explains the suggested refund adjustment. If the "
        "adjustment is positive, justify the goodwill. If negative, explain "
        "the risk factors. Do NOT invent any numbers or promises. Write in "
        + lang + ".\n\n" + "\n".join(lines)
    )

    rationale = None
    provider = "fallback"
    try:
        result = ai_service.chat(prompt, history=[])
        rationale = (result or {}).get("content", "").strip() or None
        if rationale:
            provider = "ai"
    except Exception:
        rationale = None

    if not rationale:
        if suggestion["delta"] > 0:
            rationale = (
                f"Goodwill adjustment of +{suggestion['delta']} percentage points "
                f"applied for a {suggestion['signals'].get('tier', 'valued')} customer "
                f"with {suggestion['signals'].get('tenure_bookings', 0)} past completed bookings."
            )
        elif suggestion["delta"] < 0:
            rationale = (
                f"Adjusted by {suggestion['delta']} percentage points to account for "
                f"recent cancellations ({suggestion['signals'].get('recent_cancellations_90d', 0)} in 90d)."
            )
        else:
            rationale = "Standard policy applies with no adjustment."

    return {
        "base_pct": base_pct,
        "base_amount": base["refund_amount"],
        "suggested_pct": suggested_pct,
        "suggested_amount": str(suggested_amount),
        "delta_pp": suggestion["delta"],
        "currency": booking.currency,
        "policy_label": base["policy_label"],
        "signals": suggestion["signals"],
        "rationale": rationale,
        "provider": provider,
    }
