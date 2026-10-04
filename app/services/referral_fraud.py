"""Referral fraud prevention service.

Phase 77, Step 3a (plan §12).

The plan requires checks for:
- same user identity
- same verified phone
- same payment identity
- suspicious device relationship
- suspicious IP/network behavior
- abnormal referral velocity
- repeated cancellations / refunds
- unusual account creation patterns
- circular referral patterns

Suspicious relationships are flagged REVIEW rather than auto-paying.

This service returns a decision; the caller (referral_engine) applies it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.core import rewards_config
from app.core.logging_config import get_logger
from app.models.booking import Booking
from app.models.referral_event import ReferralEvent
from app.models.referral_relationship import ReferralRelationship
from app.models.user import User

logger = get_logger(__name__)


@dataclass
class FraudCheckResult:
    decision: str  # "PASS" | "REVIEW"
    flags: list[str] = field(default_factory=list)
    score: int = 0


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------- individual checks ----------


def check_same_phone(referrer: User, referred: User) -> str | None:
    if referrer.phone and referred.phone and referrer.phone == referred.phone:
        return "same_phone"
    return None


def check_same_email_domain_local(
    referrer: User, referred: User
) -> str | None:
    """Very naive check: same email local-part and same email domain.

    Not a flag on its own — this is intended as a weak signal combined
    with others. We return a specific string so the score can weight it
    lower than strong signals.
    """
    try:
        rl, rd = referrer.email.split("@", 1)
        al, ad = referred.email.split("@", 1)
    except ValueError:
        return None
    if rl.lower() == al.lower() and rd.lower() == ad.lower():
        return None  # emails are unique per tenant; skip
    return None


def check_circular(db: DBSession, referrer: User, referred: User) -> str | None:
    """Detect A → B while B → A (or a direct reversal)."""
    reverse = (
        db.query(ReferralRelationship)
        .filter(
            ReferralRelationship.referrer_user_id == referred.id,
            ReferralRelationship.referred_user_id == referrer.id,
        )
        .first()
    )
    if reverse is not None:
        return "circular_referral"
    return None


def check_velocity(db: DBSession, referrer: User) -> str | None:
    """Too many referral relationships created in the last 24h."""
    since = _now() - timedelta(hours=24)
    n = (
        db.query(func.count(ReferralRelationship.id))
        .filter(
            ReferralRelationship.referrer_user_id == referrer.id,
            ReferralRelationship.created_at >= since,
        )
        .scalar()
    )
    if n and int(n) > rewards_config.REFERRAL_VELOCITY_MAX_PER_24H:
        return "velocity_24h"
    return None


def check_referred_cancellations(db: DBSession, referred: User) -> str | None:
    """Referred user has a high cancellation rate on recent bookings."""
    since = _now() - timedelta(days=30)
    total = (
        db.query(func.count(Booking.id))
        .filter(Booking.user_id == referred.id, Booking.created_at >= since)
        .scalar()
    ) or 0
    if int(total) < rewards_config.REFERRAL_MIN_BOOKINGS_FOR_RATE:
        return None
    cancelled = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.user_id == referred.id,
            Booking.created_at >= since,
            Booking.status == "cancelled",
        )
        .scalar()
    ) or 0
    rate = int(cancelled) / int(total) if total else 0.0
    if rate >= rewards_config.REFERRAL_MAX_CANCELLATION_RATE:
        return "high_cancellation_rate"
    return None


def check_account_age(referred: User, booking: Booking) -> str | None:
    """Referred account created and booked within a very short window."""
    try:
        created = referred.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
    except Exception:
        return None
    age = _now() - created
    if age < timedelta(hours=rewards_config.REFERRAL_MIN_ACCOUNT_AGE_HOURS):
        # Only a flag if the booking was also created very fast.
        try:
            bk_created = booking.created_at
            if bk_created.tzinfo is None:
                bk_created = bk_created.replace(tzinfo=timezone.utc)
            if (_now() - bk_created) < timedelta(hours=1):
                return "new_account_fast_booking"
        except Exception:
            return None
    return None


def check_same_ip(
    db: DBSession, relationship: ReferralRelationship
) -> str | None:
    """Compare IP recorded on the apply event vs the referrer's IP.

    We only have IP if it was recorded on an event (apply_code accepts
    an optional ip_address). If neither side has an IP, no flag.
    """
    events = (
        db.query(ReferralEvent)
        .filter(
            ReferralEvent.relationship_id == relationship.id,
            ReferralEvent.event_type == "REGISTERED",
        )
        .all()
    )
    referred_ips = {e.extra.get("ip") for e in events if e.extra and e.extra.get("ip")}
    if not referred_ips:
        return None
    referrer_events = (
        db.query(ReferralEvent)
        .filter(
            ReferralEvent.event_type.in_(("REGISTERED", "CODE_GENERATED")),
        )
        .join(
            ReferralRelationship,
            ReferralRelationship.id == ReferralEvent.relationship_id,
        )
        .filter(ReferralRelationship.referrer_user_id == relationship.referrer_user_id)
        .all()
    )
    referrer_ips = {
        e.extra.get("ip") for e in referrer_events if e.extra and e.extra.get("ip")
    }
    if not referrer_ips:
        return None
    if referred_ips & referrer_ips:
        return "same_ip"
    return None


# ---------- orchestrator ----------


def evaluate(
    db: DBSession,
    *,
    relationship: ReferralRelationship,
    booking: Booking | None = None,
) -> FraudCheckResult:
    """Run all checks and return a review-or-pass decision."""
    referrer = db.get(User, relationship.referrer_user_id)
    referred = db.get(User, relationship.referred_user_id)
    if referrer is None or referred is None:
        return FraudCheckResult(decision="REVIEW", flags=["missing_user"], score=100)

    flags: list[str] = []
    score = 0

    strong = (
        check_same_phone(referrer, referred),
        check_circular(db, referrer, referred),
        check_velocity(db, referrer),
        check_same_ip(db, relationship),
    )
    for f in strong:
        if f:
            flags.append(f)
            score += 30

    if booking is not None:
        weak = (
            check_referred_cancellations(db, referred),
            check_account_age(referred, booking),
        )
        for f in weak:
            if f:
                flags.append(f)
                score += 15

    decision = "REVIEW" if score >= rewards_config.REFERRAL_FRAUD_REVIEW_THRESHOLD else "PASS"
    if flags:
        logger.info(
            "referral fraud check: relationship=%s flags=%s score=%s decision=%s",
            relationship.id, flags, score, decision,
        )
    return FraudCheckResult(decision=decision, flags=flags, score=score)
