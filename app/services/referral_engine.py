"""Referral Engine — lifecycle service for the user referral module.

Phase 77, Step 2 (plan §9-§11).

Lifecycle (plan §10):
    INVITED → REGISTERED → VERIFIED → QUALIFIED → REWARDED
                                                        → REVERSED
                                                        → EXPIRED

Design rules (plan §23):
- Rewards are server-authoritative; the client cannot create them.
- Every transition creates a ReferralEvent (append-only audit).
- Rewards require a qualifying transaction (min AED 300).
- Reward credits go through the immutable Reward ledger
  (funding_source="REFERRAL") via reward_engine.create_ledger_entry.
- Awarding is idempotent: a relationship can only be REWARDED once.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.core import rewards_config
from app.core.logging_config import get_logger
from app.models.booking import Booking
from app.models.referral_code import ReferralCode
from app.models.referral_event import ReferralEvent
from app.models.referral_relationship import (
    ReferralRelationship,
    REFERRAL_STATUSES,
)
from app.models.referral_reward import ReferralReward
from app.models.tenant import Tenant
from app.models.user import User
from app.services import reward_engine

logger = get_logger(__name__)


# ---------- helpers ----------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_code() -> str:
    """Generate a unique referral code (10 chars, uppercase)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # avoid I/O/0/1 confusion
    return "".join(secrets.choice(alphabet) for _ in range(10))


def _emit(
    db: DBSession,
    *,
    tenant_id: str,
    relationship: ReferralRelationship,
    event_type: str,
    from_status: str | None,
    to_status: str | None,
    actor_user_id: str | None = None,
    extra: dict | None = None,
) -> ReferralEvent:
    ev = ReferralEvent(
        tenant_id=tenant_id,
        relationship_id=relationship.id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        actor_user_id=actor_user_id,
        extra=extra or {},
    )
    db.add(ev)
    return ev


# ---------- codes ----------


def generate_code(
    db: DBSession,
    *,
    tenant: Tenant,
    user: User,
    label: str | None = None,
) -> ReferralCode:
    """Return the user's default referral code (create if absent).

    If the user already has a default code, it is returned as-is.
    A brand new code is generated only the first time.
    """
    existing = (
        db.query(ReferralCode)
        .filter(
            ReferralCode.user_id == user.id,
            ReferralCode.is_default.is_(True),
            ReferralCode.is_active.is_(True),
        )
        .one_or_none()
    )
    if existing is not None:
        return existing

    # Try a few times in the unlikely case of collision.
    for _ in range(8):
        code = _make_code()
        if db.query(ReferralCode).filter(ReferralCode.code == code).one_or_none() is None:
            break
    else:
        raise RuntimeError("could not generate a unique referral code")

    rc = ReferralCode(
        tenant_id=tenant.id,
        user_id=user.id,
        code=code,
        label=label,
        is_default=True,
        is_active=True,
    )
    db.add(rc)
    db.commit()
    db.refresh(rc)

    # Also mirror onto User.referral_code for legacy compatibility.
    if not user.referral_code:
        user.referral_code = code
        db.add(user)
        db.commit()

    return rc


def find_code(db: DBSession, *, code: str) -> ReferralCode | None:
    c = (code or "").strip().upper()
    if not c:
        return None
    return (
        db.query(ReferralCode)
        .filter(
            ReferralCode.code == c,
            ReferralCode.is_active.is_(True),
        )
        .one_or_none()
    )


# ---------- lifecycle: apply ----------


def get_relationship_for_referred(
    db: DBSession, *, referred_user_id: str
) -> ReferralRelationship | None:
    """Return the (single) relationship where this user is the referred one."""
    return (
        db.query(ReferralRelationship)
        .filter(ReferralRelationship.referred_user_id == referred_user_id)
        .order_by(ReferralRelationship.created_at.desc())
        .first()
    )


def apply_code(
    db: DBSession,
    *,
    tenant: Tenant,
    current_user: User,
    code: str,
    actor_user_id: str | None = None,
) -> ReferralRelationship:
    """Apply a referral code for the current user.

    Idempotent: if a relationship already exists for this referred user,
    it is returned as-is (never duplicated).

    Raises ValueError on invalid states (self-referral, unknown code,
    inactive code).
    """
    rc = find_code(db, code=code)
    if rc is None:
        raise ValueError("Referral code not found")
    if rc.user_id == current_user.id:
        raise ValueError("Cannot refer yourself")

    existing = get_relationship_for_referred(db, referred_user_id=current_user.id)
    if existing is not None:
        return existing

    rel = ReferralRelationship(
        tenant_id=tenant.id,
        referral_code_id=rc.id,
        referrer_user_id=rc.user_id,
        referred_user_id=current_user.id,
        status="REGISTERED",
        registered_at=_now(),
    )
    db.add(rel)
    db.flush()

    _emit(
        db,
        tenant_id=tenant.id,
        relationship=rel,
        event_type="REGISTERED",
        from_status="INVITED",
        to_status="REGISTERED",
        actor_user_id=actor_user_id or current_user.id,
        extra={"code": rc.code},
    )
    db.commit()
    db.refresh(rel)
    return rel


# ---------- lifecycle: verify ----------


def mark_verified(
    db: DBSession, *, relationship: ReferralRelationship, actor_user_id: str | None = None
) -> ReferralRelationship:
    """Move a relationship from REGISTERED → VERIFIED.

    Idempotent: a VERIFIED (or beyond) relationship is returned as-is.
    """
    if relationship.status in ("VERIFIED", "QUALIFIED", "REWARDED"):
        return relationship
    if relationship.status not in ("INVITED", "REGISTERED"):
        raise ValueError(f"cannot verify from status {relationship.status}")

    prev = relationship.status
    relationship.status = "VERIFIED"
    relationship.verified_at = _now()
    db.add(relationship)
    _emit(
        db,
        tenant_id=relationship.tenant_id,
        relationship=relationship,
        event_type="VERIFIED",
        from_status=prev,
        to_status="VERIFIED",
        actor_user_id=actor_user_id,
    )
    db.commit()
    db.refresh(relationship)
    return relationship


# ---------- lifecycle: qualify ----------


def evaluate_qualification(
    db: DBSession, *, relationship: ReferralRelationship, booking: Booking
) -> tuple[bool, str]:
    """Decide whether this booking qualifies the referral.

    Requirements (plan §9, §11):
    - relationship in VERIFIED (or REGISTERED if user already verified)
    - booking is paid and confirmed
    - booking.total_amount >= REFERRAL_MIN_QUALIFYING_AMOUNT
    - booking not cancelled / refunded
    """
    if relationship.status in ("REWARDED", "REVERSED", "EXPIRED", "CANCELLED", "REVIEW"):
        return False, f"relationship_status_{relationship.status.lower()}"

    if relationship.status not in ("VERIFIED", "REGISTERED", "QUALIFIED"):
        return False, "relationship_not_verified"

    if booking.status in ("cancelled",):
        return False, "booking_cancelled"
    if booking.payment_status != "paid":
        return False, "not_paid"
    if booking.status not in ("confirmed", "paid"):
        return False, "status_not_confirmable"

    amount = Decimal(str(booking.total_amount or 0))
    min_amt = Decimal(str(rewards_config.REFERRAL_MIN_QUALIFYING_AMOUNT))
    if amount < min_amt:
        return False, "below_minimum"

    return True, "ok"


def mark_qualified(
    db: DBSession,
    *,
    relationship: ReferralRelationship,
    booking: Booking,
    actor_user_id: str | None = None,
) -> ReferralRelationship:
    """Move a relationship to QUALIFIED using the given booking."""
    if relationship.status == "QUALIFIED":
        return relationship
    ok, reason = evaluate_qualification(db, relationship=relationship, booking=booking)
    if not ok:
        raise ValueError(f"not qualifying: {reason}")

    prev = relationship.status
    relationship.status = "QUALIFIED"
    relationship.qualified_at = _now()
    relationship.qualifying_booking_id = booking.id
    db.add(relationship)
    _emit(
        db,
        tenant_id=relationship.tenant_id,
        relationship=relationship,
        event_type="QUALIFIED",
        from_status=prev,
        to_status="QUALIFIED",
        actor_user_id=actor_user_id,
        extra={"booking_id": booking.id, "amount": str(booking.total_amount)},
    )
    db.commit()
    db.refresh(relationship)
    return relationship


# ---------- lifecycle: reward ----------


def award_referral(
    db: DBSession, *, relationship: ReferralRelationship
) -> tuple[ReferralReward, ReferralReward] | None:
    """Issue the two referral rewards (referrer + referred).

    Idempotent: returns None if already REWARDED.

    The actual credit is written to the Reward ledger via
    reward_engine.create_ledger_entry with funding_source="REFERRAL".
    """
    if relationship.status == "REWARDED":
        return None
    if relationship.status != "QUALIFIED":
        raise ValueError(f"cannot award from status {relationship.status}")

    referrer = db.get(User, relationship.referrer_user_id)
    referred = db.get(User, relationship.referred_user_id)
    tenant = db.get(Tenant, relationship.tenant_id)
    if referrer is None or referred is None or tenant is None:
        raise ValueError("referrer, referred or tenant not found")

    referrer_amt = Decimal(str(rewards_config.REFERRAL_REFERRER_CREDIT))
    referred_amt = Decimal(str(rewards_config.REFERRAL_REFERRED_CREDIT))

    # 1. Ledger entries (idempotent by (user, transaction=None, reward_type)
    #    We cannot use transaction_id here (referral is not a transaction),
    #    so we rely on the ReferralReward row + relationship status for
    #    idempotency.
    ref_ledger, _ = reward_engine.create_ledger_entry(
        db,
        tenant=tenant,
        user=referrer,
        reward_type="REFERRAL_BONUS",
        amount=referrer_amt,
        currency="AED",
        funding_source="REFERRAL",
        status="AVAILABLE",
        available_at=_now(),
        referral_id=relationship.id,
        source_type="REFERRAL",
        source_id=relationship.id,
        description=f"Referral bonus (referrer) for {referred.email}",
        extra={"side": "REFERRER", "relationship_id": relationship.id},
    )
    rw_ref = ReferralReward(
        tenant_id=relationship.tenant_id,
        relationship_id=relationship.id,
        user_id=referrer.id,
        side="REFERRER",
        amount=referrer_amt,
        status="ISSUED",
        ledger_reward_id=ref_ledger.id,
        issued_at=_now(),
    )
    db.add(rw_ref)

    refd_ledger, _ = reward_engine.create_ledger_entry(
        db,
        tenant=tenant,
        user=referred,
        reward_type="REFERRAL_BONUS",
        amount=referred_amt,
        currency="AED",
        funding_source="REFERRAL",
        status="AVAILABLE",
        available_at=_now(),
        referral_id=relationship.id,
        source_type="REFERRAL",
        source_id=relationship.id,
        description="Welcome referral bonus",
        extra={"side": "REFERRED", "relationship_id": relationship.id},
    )
    rw_refd = ReferralReward(
        tenant_id=relationship.tenant_id,
        relationship_id=relationship.id,
        user_id=referred.id,
        side="REFERRED",
        amount=referred_amt,
        status="ISSUED",
        ledger_reward_id=refd_ledger.id,
        issued_at=_now(),
    )
    db.add(rw_refd)

    prev = relationship.status
    relationship.status = "REWARDED"
    relationship.rewarded_at = _now()
    db.add(relationship)
    _emit(
        db,
        tenant_id=relationship.tenant_id,
        relationship=relationship,
        event_type="REWARDED",
        from_status=prev,
        to_status="REWARDED",
        extra={
            "referrer_amount": str(referrer_amt),
            "referred_amount": str(referred_amt),
            "referrer_ledger_id": ref_ledger.id,
            "referred_ledger_id": refd_ledger.id,
        },
    )
    db.commit()
    db.refresh(rw_ref)
    db.refresh(rw_refd)
    return rw_ref, rw_refd


# ---------- queries ----------


def list_my_referrals(
    db: DBSession, *, referrer_user_id: str
) -> list[ReferralRelationship]:
    return list(
        db.query(ReferralRelationship)
        .filter(ReferralRelationship.referrer_user_id == referrer_user_id)
        .order_by(ReferralRelationship.created_at.desc())
        .all()
    )


def count_by_status(
    db: DBSession, *, referrer_user_id: str
) -> dict[str, int]:
    rows = (
        db.query(
            ReferralRelationship.status,
            func.count(ReferralRelationship.id),
        )
        .filter(ReferralRelationship.referrer_user_id == referrer_user_id)
        .group_by(ReferralRelationship.status)
        .all()
    )
    return {status: int(n) for status, n in rows}
