"""Reward Analytics Service.

Phase 80, Step 2 (plan §22).

Aggregates the three metric families required by the plan:
- User metrics: earned, redeemed, expired, reversed, active users,
  redemption rate.
- Financial metrics: total liability, platform cost, partner value,
  referral cost, cost/GMV, cost/revenue.
- Campaign metrics: uses, revenue influenced, reward cost.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, distinct
from sqlalchemy.orm import Session as DBSession

from app.core import rewards_config
from app.models.booking import Booking
from app.models.reward import Reward
from app.models.reward_campaign import RewardCampaign, RewardCampaignUse
from app.models.reward_wallet import RewardWallet


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def user_metrics(db: DBSession, *, tenant_id: str) -> dict:
    earned = int(
        db.query(func.count(Reward.id))
        .filter(Reward.tenant_id == tenant_id, Reward.status == "AVAILABLE")
        .scalar()
        or 0
    )
    redeemed = int(
        db.query(func.count(Reward.id))
        .filter(Reward.tenant_id == tenant_id, Reward.reward_type == "REDEMPTION")
        .scalar()
        or 0
    )
    expired = int(
        db.query(func.count(Reward.id))
        .filter(Reward.tenant_id == tenant_id, Reward.reward_type == "EXPIRATION")
        .scalar()
        or 0
    )
    reversed_n = int(
        db.query(func.count(Reward.id))
        .filter(Reward.tenant_id == tenant_id, Reward.reward_type == "REVERSAL")
        .scalar()
        or 0
    )
    active_users = int(
        db.query(func.count(distinct(Reward.user_id)))
        .filter(Reward.tenant_id == tenant_id)
        .scalar()
        or 0
    )
    redemption_rate = (redeemed / earned) if earned else 0.0

    return {
        "rewards_earned": earned,
        "rewards_redeemed": redeemed,
        "rewards_expired": expired,
        "rewards_reversed": reversed_n,
        "active_reward_users": active_users,
        "redemption_rate": round(redemption_rate, 4),
    }


def financial_metrics(db: DBSession, *, tenant_id: str) -> dict:
    total_liability = Decimal("0")
    platform_cost = Decimal("0")
    partner_value = Decimal("0")
    referral_cost = Decimal("0")

    rows = db.query(Reward).filter(Reward.tenant_id == tenant_id).all()
    for r in rows:
        amt = Decimal(str(r.amount))
        if r.status == "AVAILABLE" and amt > 0:
            total_liability += amt
        if r.funding_source == "PLATFORM":
            platform_cost += Decimal(str(r.platform_cost or 0))
        elif r.funding_source == "PARTNER":
            partner_value += Decimal(str(r.partner_contribution or 0))
        elif r.funding_source == "REFERRAL" and amt > 0:
            referral_cost += amt

    gbv = Decimal(str(
        db.query(func.coalesce(func.sum(Booking.total_amount), 0))
        .filter(
            Booking.tenant_id == tenant_id,
            Booking.payment_status == "paid",
        )
        .scalar() or 0
    ))
    commission_rate = Decimal(str(rewards_config.DEFAULT_PLATFORM_COMMISSION_RATE))
    commission = _round2(gbv * commission_rate)

    cost_over_gmv = float((platform_cost + referral_cost) / gbv) if gbv > 0 else 0.0
    cost_over_revenue = (
        float((platform_cost + referral_cost) / commission) if commission > 0 else 0.0
    )

    return {
        "total_reward_liability": str(_round2(total_liability)),
        "platform_reward_cost": str(_round2(platform_cost)),
        "partner_reward_value": str(_round2(partner_value)),
        "referral_cost": str(_round2(referral_cost)),
        "gross_booking_value": str(_round2(gbv)),
        "platform_commission": str(commission),
        "reward_cost_over_gmv": round(cost_over_gmv, 6),
        "reward_cost_over_revenue": round(cost_over_revenue, 6),
    }


def campaign_metrics(db: DBSession, *, tenant_id: str) -> list[dict]:
    out = []
    campaigns = (
        db.query(RewardCampaign)
        .filter(RewardCampaign.tenant_id == tenant_id)
        .all()
    )
    for c in campaigns:
        uses = int(
            db.query(func.count(RewardCampaignUse.id))
            .filter(RewardCampaignUse.campaign_id == c.id)
            .scalar()
            or 0
        )
        spent = Decimal(str(c.budget_used or 0))
        out.append({
            "campaign_id": c.id,
            "name": c.name,
            "active": bool(c.active),
            "uses": uses,
            "budget_total": str(_round2(Decimal(str(c.budget_total or 0)))),
            "budget_used": str(_round2(spent)),
            "usage_count": int(c.usage_count or 0),
        })
    return out


def snapshot(db: DBSession, *, tenant_id: str) -> dict:
    return {
        "user": user_metrics(db, tenant_id=tenant_id),
        "financial": financial_metrics(db, tenant_id=tenant_id),
        "campaigns": campaign_metrics(db, tenant_id=tenant_id),
    }
