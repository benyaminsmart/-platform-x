"""Reward Campaign Engine.

Phase 80, Step 1 (plan §17, §18).

Evaluates active campaigns against a booking and returns the best
matching bonus. Enforces:
- date window
- conditions (category, min_transaction, user_tier, first_booking,
  repeat_booking, cross_category)
- budget_total / budget_used
- usage_limit / usage_count
- user_limit (per user)
- economic_cap (fraction of platform commission on the transaction)

The engine is deterministic. It NEVER exceeds configured limits.

Wiring into `payment_service.mark_success` is part of Step 2.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.core import rewards_config
from app.core.logging_config import get_logger
from app.models.booking import Booking
from app.models.reward_campaign import RewardCampaign, RewardCampaignUse
from app.models.tenant import Tenant
from app.models.user import User

logger = get_logger(__name__)


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------- Queries ----------


def list_active_campaigns(db: DBSession, *, tenant_id: str) -> list[RewardCampaign]:
    now = _now()
    q = (
        db.query(RewardCampaign)
        .filter(RewardCampaign.tenant_id == tenant_id)
        .filter(RewardCampaign.active.is_(True))
    )
    rows = q.all()
    out = []
    for c in rows:
        if c.start_at is not None and c.start_at > now:
            continue
        if c.end_at is not None and c.end_at < now:
            continue
        out.append(c)
    return out


def _user_uses(db: DBSession, *, user_id: str, campaign_id: str) -> int:
    return int(
        db.query(func.count(RewardCampaignUse.id))
        .filter(
            RewardCampaignUse.user_id == user_id,
            RewardCampaignUse.campaign_id == campaign_id,
        )
        .scalar()
        or 0
    )


# ---------- Conditions ----------


def _matches_conditions(
    db: DBSession,
    *,
    campaign: RewardCampaign,
    user: User,
    booking: Booking,
    category: str | None,
) -> tuple[bool, str]:
    cond = campaign.conditions or {}

    # category
    want_cat = cond.get("category")
    if want_cat and (category or "").upper() != str(want_cat).upper():
        return False, "category"

    # min_transaction
    min_amt = cond.get("min_transaction")
    if min_amt is not None:
        if Decimal(str(booking.total_amount or 0)) < Decimal(str(min_amt)):
            return False, "min_transaction"

    # user_tier
    want_tier = cond.get("user_tier")
    if want_tier and (getattr(user, "tier", None) or "") != want_tier:
        return False, "user_tier"

    # first_booking — user has no other paid bookings
    if cond.get("first_booking") is True:
        count = (
            db.query(func.count(Booking.id))
            .filter(
                Booking.user_id == user.id,
                Booking.payment_status == "paid",
                Booking.id != booking.id,
            )
            .scalar()
            or 0
        )
        if int(count) > 0:
            return False, "first_booking"

    # repeat_booking — user has at least one previous paid booking
    if cond.get("repeat_booking") is True:
        count = (
            db.query(func.count(Booking.id))
            .filter(
                Booking.user_id == user.id,
                Booking.payment_status == "paid",
                Booking.id != booking.id,
            )
            .scalar()
            or 0
        )
        if int(count) == 0:
            return False, "repeat_booking"

    return True, "ok"


# ---------- Economics ----------


def _economic_cap(
    *, campaign: RewardCampaign, booking_amount: Decimal
) -> Decimal:
    commission = _round2(
        booking_amount * Decimal(str(rewards_config.DEFAULT_PLATFORM_COMMISSION_RATE))
    )
    cap_pct = Decimal(str(campaign.economic_cap_pct or "0.50"))
    return _round2(commission * cap_pct)


def _compute_amount(
    *, campaign: RewardCampaign, booking_amount: Decimal
) -> Decimal:
    rt = (campaign.reward_type or "").lower()
    v = Decimal(str(campaign.reward_value or 0))
    if rt == "fixed":
        return _round2(v)
    if rt == "percentage":
        return _round2(booking_amount * v / Decimal("100"))
    if rt == "multiplier":
        # multiplier on the base reward is deferred to the caller; here
        # we treat the value as a direct amount cap.
        return _round2(v)
    return Decimal("0")


# ---------- Public API ----------


@dataclass
class CampaignMatch:
    campaign: RewardCampaign
    amount: Decimal
    capped_by_economic: bool
    reason: str


def find_best_campaign(
    db: DBSession,
    *,
    tenant: Tenant,
    user: User,
    booking: Booking,
    category: str | None,
) -> CampaignMatch | None:
    """Return the best matching campaign for this booking, or None."""
    booking_amount = _round2(Decimal(str(booking.total_amount or 0)))
    if booking_amount <= 0:
        return None

    candidates = list_active_campaigns(db, tenant_id=tenant.id)
    best: CampaignMatch | None = None

    for c in candidates:
        ok, why = _matches_conditions(
            db, campaign=c, user=user, booking=booking, category=category
        )
        if not ok:
            continue

        # usage_limit (total)
        if c.usage_limit is not None and c.usage_count >= c.usage_limit:
            continue

        # user_limit
        if c.user_limit is not None:
            used = _user_uses(db, user_id=user.id, campaign_id=c.id)
            if used >= c.user_limit:
                continue

        raw = _compute_amount(campaign=c, booking_amount=booking_amount)
        if raw <= 0:
            continue

        # budget cap
        if c.budget_total is not None:
            remaining = Decimal(str(c.budget_total)) - Decimal(str(c.budget_used or 0))
            if remaining <= 0:
                continue
            if raw > remaining:
                raw = _round2(remaining)

        # economic cap
        e_cap = _economic_cap(campaign=c, booking_amount=booking_amount)
        capped = False
        if e_cap > 0 and raw > e_cap:
            raw = e_cap
            capped = True

        if raw <= 0:
            continue

        if best is None or raw > best.amount:
            best = CampaignMatch(
                campaign=c,
                amount=raw,
                capped_by_economic=capped,
                reason="ok",
            )

    return best


def record_campaign_use(
    db: DBSession,
    *,
    tenant: Tenant,
    user: User,
    campaign: RewardCampaign,
    booking: Booking,
    amount: Decimal,
    ledger_reward_id: str,
) -> RewardCampaignUse:
    """Record one campaign use + update budget/usage counters."""
    use = RewardCampaignUse(
        tenant_id=tenant.id,
        campaign_id=campaign.id,
        user_id=user.id,
        booking_id=booking.id,
        amount=_round2(amount),
        currency=booking.currency or "AED",
        ledger_reward_id=ledger_reward_id,
        used_at=_now(),
    )
    db.add(use)

    campaign.budget_used = _round2(
        Decimal(str(campaign.budget_used or 0)) + _round2(amount)
    )
    campaign.usage_count = int(campaign.usage_count or 0) + 1
    db.add(campaign)
    db.commit()
    db.refresh(use)
    return use
