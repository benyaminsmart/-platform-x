"""Reward Eligibility + Calculation Engine.

Phase 76, Step 1 (plan §5, §6, §7, §8, §9, §18).

This module:
- Decides whether a transaction qualifies for a reward
- Computes the base reward from category rate
- Applies tier multiplier (only on eligible bonus components)
- Applies the category cap
- Applies the platform economic guardrail
- Returns a full breakdown WITHOUT writing to the ledger

Writing to the ledger is delegated to reward_engine.create_ledger_entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session as DBSession

from app.core.rewards_config import (
    CATEGORY_RATES,
    DEFAULT_PLATFORM_COMMISSION_RATE,
    DEFAULT_REWARD_COST_BUDGET_PCT,
    multiplier_for_tier,
)
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.reward_rule import RewardRule
from app.models.tenant import Tenant
from app.models.user import User


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------- Category mapping ----------

# Platform booking_type / tenant type → reward category
_TYPE_TO_CATEGORY: dict[str, str] = {
    "hotel": "HOTEL",
    "room": "HOTEL",
    "restaurant": "DINING",
    "table": "DINING",
    "dining": "DINING",
    "flight": "FLIGHT",
    "travel_agency": "FLIGHT",
    "package": "FLIGHT",
    "entertainment": "EXPERIENCE",
    "experience": "EXPERIENCE",
    "ticket": "EXPERIENCE",
}


def category_for(*, tenant: Tenant, booking: Booking | None = None) -> str | None:
    """Resolve the reward category for a tenant (+ optional booking)."""
    if booking is not None:
        bt = (booking.booking_type or "").lower()
        if bt in _TYPE_TO_CATEGORY:
            return _TYPE_TO_CATEGORY[bt]
    typ = ((tenant.config or {}).get("type") or "").lower()
    return _TYPE_TO_CATEGORY.get(typ)


# ---------- Eligibility ----------


@dataclass
class EligibilityResult:
    qualifies: bool
    reason: str


def is_qualifying_transaction(
    db: DBSession,
    *,
    tenant: Tenant,
    user: User,
    booking: Booking,
    payment: Payment | None = None,
) -> EligibilityResult:
    """Decide whether a booking/transaction qualifies for a reward (plan §9).

    Rules:
    - payment_status must be 'paid'
    - booking status must be 'confirmed' or 'paid'
    - not cancelled
    - not refunded (a reversed payment is disqualified)
    - category must be known
    - transaction amount must meet the category minimum
    """
    if booking.status in ("cancelled",):
        return EligibilityResult(False, "booking_cancelled")
    if booking.payment_status != "paid":
        return EligibilityResult(False, "not_paid")
    if booking.status not in ("confirmed", "paid"):
        return EligibilityResult(False, "status_not_confirmable")

    if payment is not None and payment.status in ("refunded", "reversed"):
        return EligibilityResult(False, "payment_reversed")

    category = category_for(tenant=tenant, booking=booking)
    if category is None:
        return EligibilityResult(False, "unknown_category")

    amount = Decimal(str(booking.total_amount or 0))
    if amount <= 0:
        return EligibilityResult(False, "zero_amount")

    rule = _get_rule(db, category=category)
    if rule is None or not rule.enabled:
        return EligibilityResult(False, "category_disabled")

    if amount < Decimal(str(rule.min_transaction_amount)):
        return EligibilityResult(False, "below_minimum")

    return EligibilityResult(True, "ok")


def _get_rule(db: DBSession, *, category: str) -> RewardRule | None:
    return (
        db.query(RewardRule)
        .filter(RewardRule.category == category)
        .one_or_none()
    )


# ---------- Calculation ----------


@dataclass
class CalculationResult:
    qualifies: bool
    reason: str
    category: str | None
    qualifying_amount: Decimal
    base_reward: Decimal
    tier_name: str
    tier_multiplier: Decimal
    tier_bonus: Decimal
    final_reward: Decimal
    cap_applied: bool
    economic_cap_applied: bool
    platform_cost: Decimal
    partner_contribution: Decimal
    commission_estimate: Decimal
    rule_max: Decimal | None


def _commission_estimate(amount: Decimal) -> Decimal:
    return _round2(amount * DEFAULT_PLATFORM_COMMISSION_RATE)


def calculate_reward(
    db: DBSession,
    *,
    tenant: Tenant,
    user: User,
    booking: Booking,
    payment: Payment | None = None,
) -> CalculationResult:
    """Compute the reward for a booking WITHOUT writing to the ledger."""
    elig = is_qualifying_transaction(
        db, tenant=tenant, user=user, booking=booking, payment=payment,
    )
    amount = _round2(Decimal(str(booking.total_amount or 0)))
    category = category_for(tenant=tenant, booking=booking)
    tier = getattr(user, "tier", None) or "EXPLORER"
    mult = multiplier_for_tier(tier)

    if not elig.qualifies:
        return CalculationResult(
            qualifies=False, reason=elig.reason, category=category,
            qualifying_amount=amount, base_reward=Decimal("0"),
            tier_name=tier, tier_multiplier=mult, tier_bonus=Decimal("0"),
            final_reward=Decimal("0"), cap_applied=False,
            economic_cap_applied=False, platform_cost=Decimal("0"),
            partner_contribution=Decimal("0"),
            commission_estimate=_commission_estimate(amount),
            rule_max=None,
        )

    assert category is not None
    rule = _get_rule(db, category=category)
    assert rule is not None
    rate = Decimal(str(rule.platform_reward_rate))

    base = _round2(amount * rate)
    rule_max = Decimal(str(rule.max_reward_amount))

    # Tier bonus applies only on top of the base reward (the plan allows
    # tier multipliers on eligible bonus components, not on all funding).
    # Formula: bonus = base × (multiplier − 1). Final = base + bonus.
    tier_bonus = _round2(base * (mult - Decimal("1.00")))
    combined = base + tier_bonus

    # Category cap
    cap_applied = False
    if combined > rule_max:
        combined = rule_max
        cap_applied = True

    # Economic guardrail: platform reward cost must not exceed a fraction
    # of the platform commission from this transaction.
    commission = _commission_estimate(amount)
    max_cost = _round2(commission * DEFAULT_REWARD_COST_BUDGET_PCT)
    economic_cap_applied = False
    if combined > max_cost:
        combined = max_cost
        economic_cap_applied = True

    combined = _round2(max(Decimal("0"), combined))

    return CalculationResult(
        qualifies=True, reason="ok", category=category,
        qualifying_amount=amount, base_reward=base,
        tier_name=tier, tier_multiplier=mult, tier_bonus=tier_bonus,
        final_reward=combined, cap_applied=cap_applied,
        economic_cap_applied=economic_cap_applied,
        platform_cost=combined, partner_contribution=Decimal("0"),
        commission_estimate=commission, rule_max=rule_max,
    )
