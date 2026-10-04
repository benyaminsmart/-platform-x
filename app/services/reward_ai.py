"""Reward AI Decision Interface.

Phase 80, Step 2 (plan §19).

The AI layer recommends a reward, but **never bypasses deterministic
limits**. The final amount is always re-validated by the campaign
engine and the economic cap.

This module is currently a deterministic stub that returns a
recommendation based on the user's history. A real LLM provider can be
plugged in later without changing the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.reward_campaign import RewardCampaign
from app.models.tenant import Tenant
from app.models.user import User
from app.services import reward_campaign as campaign_engine


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class RewardRecommendation:
    recommended_campaign_id: str | None
    recommended_amount: Decimal
    provider: str
    rationale: str
    deterministic_cap_applied: bool


def recommend_reward(
    db: DBSession,
    *,
    tenant: Tenant,
    user: User,
    booking: Booking,
    category: str | None,
) -> RewardRecommendation:
    """Return a recommendation.

    The recommendation is a *hint*; the caller MUST apply the campaign
    engine's `find_best_campaign` output as the authoritative amount.
    """
    # Deterministic baseline: pick the best matching campaign.
    match = campaign_engine.find_best_campaign(
        db, tenant=tenant, user=user, booking=booking, category=category
    )
    if match is None:
        return RewardRecommendation(
            recommended_campaign_id=None,
            recommended_amount=Decimal("0"),
            provider="deterministic",
            rationale="no matching campaign",
            deterministic_cap_applied=False,
        )

    return RewardRecommendation(
        recommended_campaign_id=match.campaign.id,
        recommended_amount=match.amount,
        provider="deterministic",
        rationale=f"campaign '{match.campaign.name}' matched",
        deterministic_cap_applied=match.capped_by_economic,
    )
