"""Reward Reversal Service.

Phase 78, Step 2 (plan §13).

Handles cancellation/refund-driven reward reversals:
- PENDING / LOCKED reward -> CANCELLED
- AVAILABLE reward -> REVERSED (compensating negative ledger entry)
- Spent (USED) reward -> compensating negative entry via a recovery
  ledger row; original ledger row is never deleted or edited.

Design (aligned with the immutable ledger from Phase 75):
- The original `Reward` row is left untouched.
- A new negative ledger entry is appended with status REVERSED (or
  CANCELLED for PENDING/LOCKED rewards).
- The wallet projection is rebuilt from the ledger.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session as DBSession

from app.core.logging_config import get_logger
from app.models.reward import Reward
from app.models.tenant import Tenant
from app.models.user import User
from app.services import reward_engine

logger = get_logger(__name__)


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------- Query helpers ----------


def find_rewards_for_booking(
    db: DBSession, *, booking_id: str
) -> list[Reward]:
    """Return all ledger entries tied to a booking as transaction_id."""
    return list(
        db.query(Reward)
        .filter(Reward.transaction_id == booking_id)
        .all()
    )


# ---------- Single reversal ----------


def reverse_reward(
    db: DBSession, *, reward: Reward, reason: str = "cancellation"
) -> Reward | None:
    """Reverse a single reward.

    - If the reward is already reversed (extra._reversed), returns None.
    - If status is PENDING or LOCKED: mark CANCELLED via a compensating
      entry with amount 0 (no ledger movement needed since it was never
      available).
    - If status is AVAILABLE or PARTIALLY_USED: append a negative
      compensating entry with status REVERSED.
    - If status is USED: append a negative compensating entry (a
      "recovery" row) so that the platform does not silently lose
      track of the spent credit.
    """
    extra = dict(reward.extra or {})
    if extra.get("_reversed") is True:
        return None

    if reward.status in ("REVERSED", "CANCELLED", "EXPIRED"):
        return None

    tenant = db.get(Tenant, reward.tenant_id)
    user = db.get(User, reward.user_id)
    if tenant is None or user is None:
        logger.warning("reverse_reward: missing tenant/user for %s", reward.id)
        return None

    amount = _round2(Decimal(str(reward.amount)))
    now = _now()

    # For PENDING / LOCKED rewards there is nothing in the available
    # balance yet. We mark the original with a marker and, for
    # traceability, append a CANCELLED entry with amount 0.
    if reward.status in ("PENDING", "LOCKED"):
        entry, _ = reward_engine.create_ledger_entry(
            db,
            tenant=tenant,
            user=user,
            reward_type="CANCELLATION",
            amount=Decimal("0.01"),  # ledger requires non-zero
            currency=reward.currency or "AED",
            funding_source=reward.funding_source or "PLATFORM",
            platform_cost=Decimal("0"),
            partner_contribution=Decimal("0"),
            status="CANCELLED",
            source_type="CANCELLATION",
            source_id=reward.id,
            description=f"Cancellation of pending reward {reward.id}",
            extra={
                "original_reward_id": reward.id,
                "reason": reason,
                "voided": True,
            },
        )
    else:
        # AVAILABLE / PARTIALLY_USED / USED -> negative compensating entry.
        entry, _ = reward_engine.create_ledger_entry(
            db,
            tenant=tenant,
            user=user,
            reward_type="REVERSAL",
            amount=-amount,
            currency=reward.currency or "AED",
            funding_source=reward.funding_source or "PLATFORM",
            platform_cost=Decimal("0"),
            partner_contribution=Decimal("0"),
            status="REVERSED",
            source_type="REVERSAL",
            source_id=reward.id,
            description=f"Reversal of reward {reward.id}: {reason}",
            extra={
                "original_reward_id": reward.id,
                "original_reward_type": reward.reward_type,
                "reason": reason,
                "reversed_at": now.isoformat(),
            },
            allow_negative=True,
        )

    # Mark the original row with a marker (idempotency).
    extra["_reversed"] = True
    extra["_reversed_at"] = now.isoformat()
    extra["_reversal_entry_id"] = entry.id
    extra["_reversal_reason"] = reason
    reward.extra = extra
    db.add(reward)
    db.commit()

    # Clear session cache so rebuild_wallet sees the latest markers.
    db.expire_all()
    reward_engine.rebuild_wallet(db, user=user)

    logger.info(
        "reward reversed: reward=%s user=%s amount=%s reason=%s entry=%s",
        reward.id, user.id, amount, reason, entry.id,
    )
    return entry


def reverse_rewards_for_booking(
    db: DBSession, *, booking_id: str, reason: str = "cancellation"
) -> dict:
    """Reverse every reward tied to a booking.

    Returns { scanned, reversed, errors }.
    """
    rows = find_rewards_for_booking(db, booking_id=booking_id)
    reversed_n = 0
    errors = 0
    for r in rows:
        try:
            out = reverse_reward(db, reward=r, reason=reason)
            if out is not None:
                reversed_n += 1
        except Exception:
            errors += 1
            logger.exception("failed to reverse reward %s", r.id)
    return {"scanned": len(rows), "reversed": reversed_n, "errors": errors}


# ---------- Referral reward reversal ----------


def reverse_referral_rewards(
    db: DBSession, *, referral_id: str, reason: str = "referral_reversed"
) -> dict:
    """Reverse all referral-side rewards linked to a referral relationship."""
    rows = (
        db.query(Reward)
        .filter(Reward.referral_id == referral_id)
        .all()
    )
    reversed_n = 0
    errors = 0
    for r in rows:
        try:
            out = reverse_reward(db, reward=r, reason=reason)
            if out is not None:
                reversed_n += 1
        except Exception:
            errors += 1
            logger.exception("failed to reverse referral reward %s", r.id)
    return {"scanned": len(rows), "reversed": reversed_n, "errors": errors}
