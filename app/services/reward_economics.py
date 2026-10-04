"""Reward Economics Service.

Phase 80, Step 1 (plan §18).

Aggregates the platform's reward economics:
- gross_booking_value
- platform_commission (assumed rate from config)
- platform_reward_cost
- partner_reward_value
- referral_cost
- net_platform_value

Uses the immutable ledger as the source of truth. All numbers are
derived from `Reward` rows; no separate accounting is kept.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.core import rewards_config
from app.models.booking import Booking
from app.models.reward import Reward


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _commission_rate() -> Decimal:
    return Decimal(str(rewards_config.DEFAULT_PLATFORM_COMMISSION_RATE))


# ---------- Snapshot ----------


def snapshot(
    db: DBSession,
    *,
    tenant_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> dict:
    """Return the economic snapshot for a tenant in a time window."""
    # Gross booking value (paid bookings only)
    bq = db.query(
        func.coalesce(func.sum(Booking.total_amount), 0),
        func.count(Booking.id),
    ).filter(
        Booking.tenant_id == tenant_id,
        Booking.payment_status == "paid",
        Booking.status != "cancelled",
    )
    if start is not None:
        bq = bq.filter(Booking.created_at >= start)
    if end is not None:
        bq = bq.filter(Booking.created_at <= end)
    gbv, booking_count = bq.one()
    gbv = Decimal(str(gbv or 0))

    commission = _round2(gbv * _commission_rate())

    # Rewards tied to this tenant
    rq = db.query(Reward).filter(Reward.tenant_id == tenant_id)
    if start is not None:
        rq = rq.filter(Reward.created_at >= start)
    if end is not None:
        rq = rq.filter(Reward.created_at <= end)

    platform_cost = Decimal("0")
    partner_value = Decimal("0")
    referral_cost = Decimal("0")
    total_rewards = Decimal("0")

    for r in rq.all():
        amt = Decimal(str(r.amount))
        total_rewards += amt
        if r.funding_source == "PLATFORM":
            platform_cost += Decimal(str(r.platform_cost or 0))
        elif r.funding_source == "PARTNER":
            partner_value += Decimal(str(r.partner_contribution or 0))
        elif r.funding_source == "REFERRAL":
            referral_cost += amt if amt > 0 else Decimal("0")
        elif r.funding_source == "CAMPAIGN":
            platform_cost += Decimal(str(r.platform_cost or 0))

    net = _round2(commission - platform_cost - referral_cost)

    return {
        "tenant_id": tenant_id,
        "from": start.isoformat() if start else None,
        "to": end.isoformat() if end else None,
        "gross_booking_value": str(_round2(gbv)),
        "booking_count": int(booking_count or 0),
        "platform_commission": str(_round2(commission)),
        "platform_reward_cost": str(_round2(platform_cost)),
        "partner_reward_value": str(_round2(partner_value)),
        "referral_cost": str(_round2(referral_cost)),
        "total_reward_value": str(_round2(total_rewards)),
        "net_platform_value": str(_round2(net)),
    }


def reward_cost_ratio(
    db: DBSession,
    *,
    tenant_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> float:
    """Return reward cost as a fraction of commission (0..N).

    A value > 1.0 means the platform is paying out more in rewards than
    it earns in commission. In the current design this should never
    happen because of the economic cap.
    """
    snap = snapshot(db, tenant_id=tenant_id, start=start, end=end)
    commission = Decimal(snap["platform_commission"])
    cost = Decimal(snap["platform_reward_cost"]) + Decimal(snap["referral_cost"])
    if commission <= 0:
        return 0.0
    return float(cost / commission)
