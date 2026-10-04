"""Reward Redemption Service.

Phase 79, Step 1 (plan §15).

Server-authoritative redemption. The client NEVER sends a balance; the
server reads the wallet from the immutable ledger, validates, and
appends a REDEMPTION ledger entry.

Validation (per plan §15):
- ownership (reward belongs to the current user)
- available balance is sufficient
- the redeem option is active
- the wallet has not expired its credit (the ledger handles expiry)
- the option is available in the target currency
- duplicate redemption guard: same (user, option, reference_id) only once

Design:
- Redemption never touches `RewardWallet` directly.
- A new REDEMPTION ledger entry is appended with a negative amount.
- Wallet projection is rebuilt from the ledger.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session as DBSession

from app.core.logging_config import get_logger
from app.models.redeem_option import RedeemOption
from app.models.reward import Reward
from app.models.reward_wallet import RewardWallet
from app.models.tenant import Tenant
from app.models.user import User
from app.services import reward_engine

logger = get_logger(__name__)


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------- Catalog ----------


def list_active_options(db: DBSession) -> list[RedeemOption]:
    return list(
        db.query(RedeemOption)
        .filter(RedeemOption.active.is_(True))
        .order_by(RedeemOption.display_order.asc(), RedeemOption.points_cost.asc())
        .all()
    )


def get_option(db: DBSession, *, option_id: str) -> RedeemOption | None:
    return (
        db.query(RedeemOption)
        .filter(RedeemOption.id == option_id, RedeemOption.active.is_(True))
        .one_or_none()
    )


# ---------- Wallet ----------


def get_wallet(db: DBSession, *, user: User) -> RewardWallet:
    return reward_engine.get_or_create_wallet(db, user=user)


# ---------- Redemption ----------


def _find_existing_redemption(
    db: DBSession, *, user_id: str, option_id: str, reference_id: str | None
) -> Reward | None:
    """Duplicate guard: one redemption per (user, option, reference_id)."""
    q = db.query(Reward).filter(
        Reward.user_id == user_id,
        Reward.reward_type == "REDEMPTION",
        Reward.source_id == option_id,
    )
    if reference_id is not None:
        q = q.filter(Reward.transaction_id == reference_id)
    else:
        q = q.filter(Reward.transaction_id.is_(None))
    return q.first()


def redeem_option(
    db: DBSession,
    *,
    tenant: Tenant,
    user: User,
    option_id: str,
    reference_id: str | None = None,
) -> Reward:
    """Redeem a catalog option using the user's available balance.

    Raises ValueError on any invalid state.
    """
    option = get_option(db, option_id=option_id)
    if option is None:
        raise ValueError("Redeem option not found")

    # Duplicate guard
    existing = _find_existing_redemption(
        db, user_id=user.id, option_id=option.id, reference_id=reference_id
    )
    if existing is not None:
        raise ValueError("This reward has already been redeemed")

    cost = _round2(Decimal(str(option.reward_value)))
    if cost <= 0:
        raise ValueError("Redeem option has invalid value")

    wallet = get_wallet(db, user=user)
    available = Decimal(str(wallet.available_balance))
    if available < cost:
        raise ValueError("Insufficient reward balance")

    # Append a REDEMPTION ledger entry (negative).
    entry, _ = reward_engine.create_ledger_entry(
        db,
        tenant=tenant,
        user=user,
        reward_type="REDEMPTION",
        amount=-cost,
        currency=wallet.currency or "AED",
        funding_source=option.funding_source or "PLATFORM",
        platform_cost=Decimal(str(option.platform_cost or 0)),
        partner_contribution=Decimal("0"),
        status="USED",
        transaction_id=reference_id,
        source_type="REDEEM_OPTION",
        source_id=option.id,
        description=f"Redeemed: {option.name}",
        extra={
            "option_name": option.name,
            "option_reward_type": option.reward_type,
            "option_reward_value": str(option.reward_value),
            "option_category": option.category,
        },
        allow_negative=True,
    )

    db.expire_all()
    reward_engine.rebuild_wallet(db, user=user)

    logger.info(
        "reward redeemed: user=%s option=%s cost=%s entry=%s",
        user.id, option.name, cost, entry.id,
    )
    return entry
