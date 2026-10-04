"""Referral monthly-limit service.

Phase 77, Step 3c (plan §11).

The plan sets: max referral credit per user per month = AED 100.

This applies to each user individually — whether as referrer or as
referred — since a user can receive referral credits from either side.

The check is called by referral_engine.award_referral BEFORE writing
the ledger. If the limit would be exceeded, the award is deferred (the
relationship stays QUALIFIED and the caller can retry in a later month).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.core import rewards_config
from app.models.referral_reward import ReferralReward


def _month_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


def monthly_credit_used(db: DBSession, *, user_id: str) -> Decimal:
    """Sum of ISSUED referral rewards for the user in the current month."""
    total = (
        db.query(func.coalesce(func.sum(ReferralReward.amount), 0))
        .filter(
            ReferralReward.user_id == user_id,
            ReferralReward.status == "ISSUED",
            ReferralReward.issued_at.isnot(None),
            ReferralReward.issued_at >= _month_start_utc(),
        )
        .scalar()
    )
    return Decimal(str(total or 0))


def can_credit(db: DBSession, *, user_id: str, amount: Decimal) -> tuple[bool, Decimal]:
    """Return (allowed, remaining_headroom_after).

    If `amount` would push the user's monthly referral credit above the
    cap, `allowed` is False and `remaining_headroom_after` is the
    headroom that remains under the cap (>= 0).
    """
    cap = Decimal(str(rewards_config.REFERRAL_MAX_CREDIT_PER_USER_MONTH))
    used = monthly_credit_used(db, user_id=user_id)
    headroom = cap - used
    if headroom <= 0:
        return False, Decimal("0")
    if amount > headroom:
        return False, headroom
    return True, headroom - amount
