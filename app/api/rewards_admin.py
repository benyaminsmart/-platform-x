"""Rewards Admin API (Phase 80, Step 2).

Endpoints:
    GET  /platform/rewards/analytics
    GET  /platform/rewards/campaigns
    POST /platform/rewards/campaigns
    POST /platform/rewards/campaigns/{id}/toggle

All endpoints require a platform admin.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps_admin import get_current_admin
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.reward_campaign import RewardCampaign
from app.services import reward_analytics


router = APIRouter(prefix="/platform/rewards", tags=["rewards-admin"])


class CampaignCreate(BaseModel):
    tenant_id: str
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    reward_type: str = "fixed"
    reward_value: Decimal
    conditions: dict = Field(default_factory=dict)
    budget_total: Decimal | None = None
    usage_limit: int | None = None
    user_limit: int | None = None
    economic_cap_pct: Decimal = Decimal("0.50")
    start_at: datetime | None = None
    end_at: datetime | None = None


class CampaignPublic(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: str | None
    active: bool
    reward_type: str
    reward_value: Decimal
    funding_source: str
    budget_total: Decimal | None
    budget_used: Decimal
    usage_limit: int | None
    usage_count: int
    user_limit: int | None
    economic_cap_pct: Decimal

    model_config = {"from_attributes": True}


@limiter.limit("60/minute")
@router.get("/analytics")
def get_analytics(
    request: Request,
    tenant_id: str,
    _admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
) -> dict:
    return reward_analytics.snapshot(db, tenant_id=tenant_id)


@limiter.limit("60/minute")
@router.get("/campaigns", response_model=list[CampaignPublic])
def list_campaigns(
    request: Request,
    tenant_id: str,
    _admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
) -> list[CampaignPublic]:
    rows = (
        db.query(RewardCampaign)
        .filter(RewardCampaign.tenant_id == tenant_id)
        .order_by(RewardCampaign.created_at.desc())
        .all()
    )
    return [CampaignPublic.model_validate(r) for r in rows]


@limiter.limit("20/minute")
@router.post("/campaigns", response_model=CampaignPublic, status_code=status.HTTP_201_CREATED)
def create_campaign(
    request: Request,
    payload: CampaignCreate,
    _admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
) -> CampaignPublic:
    c = RewardCampaign(
        tenant_id=payload.tenant_id,
        name=payload.name,
        description=payload.description,
        active=True,
        conditions=payload.conditions or {},
        reward_type=payload.reward_type,
        reward_value=payload.reward_value,
        funding_source="CAMPAIGN",
        budget_total=payload.budget_total,
        usage_limit=payload.usage_limit,
        user_limit=payload.user_limit,
        economic_cap_pct=payload.economic_cap_pct,
        start_at=payload.start_at,
        end_at=payload.end_at,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return CampaignPublic.model_validate(c)


@limiter.limit("30/minute")
@router.post("/campaigns/{campaign_id}/toggle", response_model=CampaignPublic)
def toggle_campaign(
    request: Request,
    campaign_id: str,
    _admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
) -> CampaignPublic:
    c = db.query(RewardCampaign).filter(RewardCampaign.id == campaign_id).one_or_none()
    if c is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    c.active = not c.active
    db.add(c)
    db.commit()
    db.refresh(c)
    return CampaignPublic.model_validate(c)
