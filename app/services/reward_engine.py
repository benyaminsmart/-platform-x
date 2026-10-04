"""Reward Engine — central service for the immutable reward ledger.

Phase 75, Step 2 (plan §3, §4, §5, §23).

Design rules (from the plan):
1. Rewards are server-authoritative.
2. Every reward operation creates a ledger entry (never edited).
3. Every transaction reward is idempotent — one reward per (user,
   transaction_id, reward_type).
4. Corrections create compensating entries, not mutations.
5. Wallet is a projection of the ledger; never trust client-supplied
   balances.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.reward import Reward
from app.models.reward_wallet import RewardWallet
from app.models.tenant import Tenant
from app.models.user import User


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------- Idempotency ----------


def find_existing_reward(
    db: DBSession, *, user_id: str, transaction_id: str, reward_type: str
) -> Reward | None:
    """Return the existing ledger entry for a transaction, if any.

    Idempotency key = (user_id, transaction_id, reward_type).
    """
    return (
        db.query(Reward)
        .filter(
            Reward.user_id == user_id,
            Reward.transaction_id == transaction_id,
            Reward.reward_type == reward_type,
        )
        .one_or_none()
    )


# ---------- Ledger append ----------


def create_ledger_entry(
    db: DBSession,
    *,
    tenant: Tenant,
    user: User,
    reward_type: str,
    amount: Decimal,
    currency: str = "AED",
    funding_source: str = "PLATFORM",
    platform_cost: Decimal | None = None,
    partner_contribution: Decimal | None = None,
    status: str = "PENDING",
    available_at: datetime | None = None,
    expires_at: datetime | None = None,
    transaction_id: str | None = None,
    referral_id: str | None = None,
    campaign_id: str | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    description: str | None = None,
    extra: dict | None = None,
    allow_negative: bool = False,
) -> tuple[Reward, str]:
    """Append a ledger entry.

    status: 'created' | 'exists' (idempotent for transaction-bound rewards).

    allow_negative: when True, a negative `amount` is accepted. This is
    used exclusively for compensating entries (expiration, reversal).
    A positive amount must still be > 0. A negative amount must be < 0.
    """
    amount = _round2(amount)
    if amount == 0:
        raise ValueError("amount must be non-zero")
    if amount < 0 and not allow_negative:
        raise ValueError("negative amount requires allow_negative=True")

    # Idempotency: only for rewards tied to a transaction
    if transaction_id is not None:
        existing = find_existing_reward(
            db, user_id=user.id, transaction_id=transaction_id, reward_type=reward_type,
        )
        if existing is not None:
            return existing, "exists"

    if platform_cost is None:
        platform_cost = amount if funding_source == "PLATFORM" else Decimal("0")
    if partner_contribution is None:
        partner_contribution = amount if funding_source == "PARTNER" else Decimal("0")

    r = Reward(
        tenant_id=tenant.id,
        user_id=user.id,
        reward_type=reward_type,
        source_type=source_type,
        source_id=source_id,
        amount=amount,
        currency=currency,
        funding_source=funding_source,
        platform_cost=_round2(platform_cost),
        partner_contribution=_round2(partner_contribution),
        status=status,
        created_at=_now(),
        available_at=available_at,
        expires_at=expires_at,
        transaction_id=transaction_id,
        referral_id=referral_id,
        campaign_id=campaign_id,
        points=int(amount),  # legacy compatibility
        description=description,
        extra=extra or {},
    )
    db.add(r)
    db.commit()
    db.refresh(r)

    # Project the change into the wallet
    _project_reward_into_wallet(db, user=user, reward=r)
    return r, "created"


# ---------- Wallet projection ----------


def get_or_create_wallet(db: DBSession, *, user: User) -> RewardWallet:
    w = db.query(RewardWallet).filter(RewardWallet.user_id == user.id).one_or_none()
    if w is None:
        w = RewardWallet(
            tenant_id=user.tenant_id,
            user_id=user.id,
            currency="AED",
        )
        db.add(w)
        db.commit()
        db.refresh(w)
    return w


def _project_reward_into_wallet(db: DBSession, *, user: User, reward: Reward) -> None:
    """Apply one ledger entry into the wallet projection.

    Idempotent when called on the same reward twice (checks extra marker).
    """
    marker = reward.extra or {}
    if marker.get("_wallet_projected") is True:
        return

    w = get_or_create_wallet(db, user=user)

    amt = Decimal(str(reward.amount))
    status = reward.status

    if status == "AVAILABLE":
        w.available_balance = _round2(Decimal(str(w.available_balance)) + amt)
        if reward.funding_source == "REFERRAL":
            w.referral_balance = _round2(Decimal(str(w.referral_balance)) + amt)
        elif reward.reward_type == "EXPERIENCE_CREDIT":
            w.experience_balance = _round2(Decimal(str(w.experience_balance)) + amt)
        elif reward.funding_source == "BONUS" or reward.funding_source == "CAMPAIGN":
            w.bonus_balance = _round2(Decimal(str(w.bonus_balance)) + amt)
    elif status == "LOCKED":
        w.locked_balance = _round2(Decimal(str(w.locked_balance)) + amt)
    elif status in ("USED", "PARTIALLY_USED", "EXPIRED", "REVERSED", "CANCELLED"):
        # For reversals/expirations we subtract from available if this is
        # a compensating negative entry; positive USED entries should have
        # already been deducted at redemption time.
        if amt < 0:
            w.available_balance = _round2(Decimal(str(w.available_balance)) + amt)
            if w.available_balance < 0:
                w.available_balance = Decimal("0")

    # Track platform / partner liabilities (informational)
    if reward.status == "AVAILABLE":
        w.platform_cost_balance = _round2(
            Decimal(str(w.platform_cost_balance)) + Decimal(str(reward.platform_cost))
        )
        w.partner_cost_balance = _round2(
            Decimal(str(w.partner_cost_balance)) + Decimal(str(reward.partner_contribution))
        )

    # Mark as projected (so a rebuild won't double-apply)
    extra = dict(reward.extra or {})
    extra["_wallet_projected"] = True
    reward.extra = extra
    db.add(reward)

    w.last_rebuilt_at = _now()
    db.add(w)
    db.commit()


def rebuild_wallet(db: DBSession, *, user: User) -> RewardWallet:
    """Full rebuild of the wallet from the ledger (plan §4).

    Safe to run any time. Idempotent.
    """
    w = get_or_create_wallet(db, user=user)
    w.available_balance = Decimal("0")
    w.locked_balance = Decimal("0")
    w.expiring_balance = Decimal("0")
    w.referral_balance = Decimal("0")
    w.experience_balance = Decimal("0")
    w.bonus_balance = Decimal("0")
    w.platform_cost_balance = Decimal("0")
    w.partner_cost_balance = Decimal("0")

    rows = db.query(Reward).filter(Reward.user_id == user.id).all()
    for r in rows:
        amt = Decimal(str(r.amount))
        if r.status == "AVAILABLE":
            w.available_balance += amt
            if r.funding_source == "REFERRAL":
                w.referral_balance += amt
            elif r.reward_type == "EXPERIENCE_CREDIT":
                w.experience_balance += amt
            elif r.funding_source in ("BONUS", "CAMPAIGN"):
                w.bonus_balance += amt
            w.platform_cost_balance += Decimal(str(r.platform_cost))
            w.partner_cost_balance += Decimal(str(r.partner_contribution))
        elif r.status == "LOCKED":
            w.locked_balance += amt
        elif r.status in ("USED", "PARTIALLY_USED", "EXPIRED", "REVERSED", "CANCELLED"):
            if amt < 0:
                w.available_balance += amt

    w.available_balance = _round2(max(Decimal("0"), w.available_balance))
    w.last_rebuilt_at = _now()
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


# ---------- Queries ----------


def wallet_summary(db: DBSession, *, user: User) -> dict:
    """Return the wallet balances as a dict."""
    w = get_or_create_wallet(db, user=user)

    # expiring within 7 days
    soon = _now() + __import__("datetime").timedelta(days=7)
    expiring = (
        db.query(func.coalesce(func.sum(Reward.amount), 0))
        .filter(
            Reward.user_id == user.id,
            Reward.status == "AVAILABLE",
            Reward.expires_at.isnot(None),
            Reward.expires_at <= soon,
        )
        .scalar()
    )
    w.expiring_balance = _round2(Decimal(str(expiring or 0)))
    db.add(w); db.commit(); db.refresh(w)

    return {
        "available_balance": float(w.available_balance),
        "locked_balance": float(w.locked_balance),
        "expiring_balance": float(w.expiring_balance),
        "referral_balance": float(w.referral_balance),
        "experience_balance": float(w.experience_balance),
        "bonus_balance": float(w.bonus_balance),
        "currency": w.currency,
    }


def list_ledger(
    db: DBSession, *, user_id: str, status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    q = db.query(Reward).filter(Reward.user_id == user_id)
    if status:
        q = q.filter(Reward.status == status)
    rows = q.order_by(Reward.created_at.desc()).limit(max(1, min(limit, 200))).all()
    return [
        {
            "id": r.id,
            "reward_type": r.reward_type,
            "amount": float(r.amount),
            "currency": r.currency,
            "funding_source": r.funding_source,
            "status": r.status,
            "transaction_id": r.transaction_id,
            "referral_id": r.referral_id,
            "campaign_id": r.campaign_id,
            "available_at": r.available_at.isoformat() if r.available_at else None,
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "description": r.description,
        }
        for r in rows
    ]
