"""Reward Expiration Service.

Phase 78, Step 1 (plan §14).

The plan requires:
- Expiration windows: 30 / 60 / 90 days (configurable).
- Automated job: AVAILABLE + expires_at <= now -> EXPIRED.
- Pre-expiry notifications (7 / 3 / 1 days before).
- Never delete the original reward entry.
  Expiration creates a compensating ledger entry.

Design (aligned with the immutable ledger from Phase 75):
- The original `Reward` row is left untouched (its status stays as it
  was at creation — AVAILABLE / LOCKED / PENDING).
- A **new** ledger entry is appended with a negative amount and status
  EXPIRED. It references the original entry via `source_id` and via
  `extra.original_reward_id`.
- The wallet projection is rebuilt from the ledger. The negative
  compensating entry reduces the available balance.

This service does NOT send notifications — that is Step 3.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session as DBSession

from app.core import rewards_config
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


# ---------- Queries ----------


def find_expired_candidates(
    db: DBSession, *, tenant_id: str | None = None, limit: int = 500
) -> list[Reward]:
    """Return AVAILABLE rewards whose expires_at is in the past.

    Ordered oldest-first so the job drains the backlog predictably.
    """
    q = db.query(Reward).filter(
        Reward.status == "AVAILABLE",
        Reward.expires_at.isnot(None),
        Reward.expires_at <= _now(),
    )
    if tenant_id is not None:
        q = q.filter(Reward.tenant_id == tenant_id)
    q = q.order_by(Reward.expires_at.asc()).limit(max(1, min(limit, 5000)))
    return list(q.all())


def find_expiring_soon(
    db: DBSession,
    *,
    tenant_id: str | None = None,
    days_before: int = 7,
    limit: int = 500,
) -> list[Reward]:
    """Return AVAILABLE rewards expiring within `days_before` days."""
    now = _now()
    horizon = now + timedelta(days=days_before)
    q = db.query(Reward).filter(
        Reward.status == "AVAILABLE",
        Reward.expires_at.isnot(None),
        Reward.expires_at > now,
        Reward.expires_at <= horizon,
    )
    if tenant_id is not None:
        q = q.filter(Reward.tenant_id == tenant_id)
    q = q.order_by(Reward.expires_at.asc()).limit(max(1, min(limit, 5000)))
    return list(q.all())


# ---------- Expiration ----------


def expire_reward(db: DBSession, *, reward: Reward) -> Reward | None:
    """Expire a single AVAILABLE reward.

    Idempotent: a reward that is already expired (via the marker in
    `extra._expired`) or whose status is not AVAILABLE is skipped.

    Returns the compensating ledger entry, or None if nothing was done.
    """
    if reward.status != "AVAILABLE":
        return None

    extra = dict(reward.extra or {})
    if extra.get("_expired") is True:
        return None

    tenant = db.get(Tenant, reward.tenant_id)
    user = db.get(User, reward.user_id)
    if tenant is None or user is None:
        logger.warning("expire_reward: missing tenant/user for reward %s", reward.id)
        return None

    amount = _round2(Decimal(str(reward.amount)))
    if amount <= 0:
        return None

    # 1. Append a negative compensating ledger entry.
    #    We cannot use create_ledger_entry's idempotency on
    #    (user, transaction_id, reward_type) because the original
    #    reward may or may not have a transaction_id. Instead, we mark
    #    the original with `_expired` and use that as the idempotency key.
    compensating, _ = reward_engine.create_ledger_entry(
        db,
        tenant=tenant,
        user=user,
        reward_type="EXPIRATION",
        amount=-amount,
        currency=reward.currency or "AED",
        funding_source=reward.funding_source or "PLATFORM",
        platform_cost=Decimal("0"),
        partner_contribution=Decimal("0"),
        status="EXPIRED",
        transaction_id=None,
        source_type="EXPIRATION",
        source_id=reward.id,
        description=f"Expiration of reward {reward.id}",
        extra={
            "original_reward_id": reward.id,
            "original_reward_type": reward.reward_type,
            "expired_at": _now().isoformat(),
        },
        allow_negative=True,
    )

    # 2. Mark the original as processed (idempotency marker).
    extra["_expired"] = True
    extra["_expired_at"] = _now().isoformat()
    extra["_expiration_entry_id"] = compensating.id
    reward.extra = extra
    db.add(reward)
    db.commit()

    # 3. Clear the session cache so rebuild_wallet sees the latest
    #    _expired markers on the original reward rows.
    db.expire_all()

    # 4. Rebuild the wallet projection from the ledger (safe + auditable).
    reward_engine.rebuild_wallet(db, user=user)

    logger.info(
        "reward expired: reward=%s user=%s amount=%s entry=%s",
        reward.id, user.id, amount, compensating.id,
    )
    return compensating


def run_expiration(
    db: DBSession, *, tenant_id: str | None = None, limit: int = 500
) -> dict:
    """Batch expiration job.

    Returns { scanned, expired, errors }.
    """
    rows = find_expired_candidates(db, tenant_id=tenant_id, limit=limit)
    expired = 0
    errors = 0
    for r in rows:
        try:
            out = expire_reward(db, reward=r)
            if out is not None:
                expired += 1
        except Exception:
            errors += 1
            logger.exception("failed to expire reward %s", r.id)
    return {"scanned": len(rows), "expired": expired, "errors": errors}
