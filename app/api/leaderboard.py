"""Leaderboard API (Phase 29, Step 4).

Public:
  GET  /leaderboard                     — overall + per category
  GET  /leaderboard/categories          — list categories + tenant counts

Business:
  GET  /business/api/score              — current tenant's score + rewards

Platform admin:
  POST /platform/api/leaderboard/recompute   — recompute for a period
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.api.deps_admin import get_current_admin
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.business_score import BusinessScore
from app.models.tenant import Tenant
from app.models.user import User
from app.services import leaderboard as lb_service
from app.services import leaderboard_tips
from app.services import scoring_engine


router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])
business_router = APIRouter(prefix="/business/api", tags=["business-score"])
platform_router = APIRouter(prefix="/platform/api", tags=["platform-leaderboard"])


_ALLOWED_CATEGORIES = {"hotels", "restaurants", "travel", "entertainment", "other"}


# ---------- Schemas ----------


class LeaderboardEntry(BaseModel):
    rank: int | None
    rank_overall: int | None
    rank_in_category: int | None
    tenant_id: str
    tenant_slug: str
    tenant_name: str
    category: str
    overall_score: float
    customer_satisfaction: float
    service_quality: float
    pricing_competitiveness: float
    engagement: float
    loyalty: float
    rewards: dict[str, Any] | None = None
    location: str | None = None
    rating: float | None = None
    cover_image: str | None = None


class CategoryInfo(BaseModel):
    category: str
    tenants: int
    top_slug: str | None
    top_score: float | None


class TenantScoreResponse(BaseModel):
    tenant_id: str
    category: str
    period_start: str
    period_end: str
    overall_score: float
    customer_satisfaction: float
    service_quality: float
    pricing_competitiveness: float
    engagement: float
    loyalty: float
    rank_overall: int | None
    rank_in_category: int | None
    rewards: dict[str, Any] | None
    criteria_breakdown: dict[str, Any]
    computed_at: str | None


class RecomputeResponse(BaseModel):
    period_start: str
    period_end: str
    tenants_total: int
    created: int
    updated: int
    ranks_assigned: int


class Tip(BaseModel):
    key: str
    label: str
    score: float
    gap_to_100: float


class NextRankGap(BaseModel):
    target_rank: int
    target_overall_score: float
    gap: float


class TipsResponse(BaseModel):
    weakest: list[Tip]
    next_rank_gap: NextRankGap | None
    advice: str


# ---------- Public ----------


@router.get("", response_model=list[LeaderboardEntry])
@limiter.limit("60/minute")
def get_leaderboard(
    request: Request,
    category: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: DBSession = Depends(get_db),
) -> list[LeaderboardEntry]:
    """Return the current-period leaderboard.

    Optional ?category=hotels|restaurants|travel|entertainment|other
    """
    if category is not None and category not in _ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"category must be one of: {', '.join(sorted(_ALLOWED_CATEGORIES))}")

    rows = lb_service.get_leaderboard(db, category=category, limit=limit)
    return [LeaderboardEntry(**r) for r in rows]


@router.get("/categories", response_model=list[CategoryInfo])
@limiter.limit("60/minute")
def get_categories(
    request: Request,
    db: DBSession = Depends(get_db),
) -> list[CategoryInfo]:
    """List all leaderboard categories with tenant counts + top entry."""
    ps, pe = scoring_engine.current_period()
    out: list[CategoryInfo] = []
    for cat in sorted(_ALLOWED_CATEGORIES):
        rows = lb_service.get_leaderboard(db, category=cat, limit=1)
        count = (
            db.query(BusinessScore)
            .filter(
                BusinessScore.category == cat,
                BusinessScore.period_start == ps,
                BusinessScore.period_end == pe,
            )
            .count()
        )
        top = rows[0] if rows else None
        out.append(
            CategoryInfo(
                category=cat,
                tenants=count,
                top_slug=top["tenant_slug"] if top else None,
                top_score=top["overall_score"] if top else None,
            )
        )
    return out


# ---------- Business ----------


@business_router.get("/score", response_model=TenantScoreResponse)
@limiter.limit("30/minute")
def get_my_score(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> TenantScoreResponse:
    """Return the current tenant's score for the current period."""
    d = lb_service.get_tenant_score_dict(db, tenant_id=tenant.id)
    if d is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No score computed yet for this period. "
                "Ask a platform admin to run /platform/api/leaderboard/recompute."
            ),
        )
    return TenantScoreResponse(**d)


@business_router.get("/score/tips", response_model=TipsResponse)
@limiter.limit("20/minute")
def get_my_tips(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> TipsResponse:
    """Return AI-generated tips to improve this tenant's leaderboard score."""
    row = lb_service.get_tenant_score(db, tenant_id=tenant.id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No score computed yet for this period. "
                "Ask a platform admin to run /platform/api/leaderboard/recompute."
            ),
        )
    out = leaderboard_tips.generate_tips(db, tenant=tenant, row=row)
    return TipsResponse(**out)


# ---------- Platform admin ----------


@platform_router.post("/leaderboard/recompute", response_model=RecomputeResponse)
@limiter.limit("5/minute")
def platform_recompute(
    request: Request,
    period: str = Query(default="current", pattern="^(current|previous)$"),
    admin=Depends(get_current_admin),
    db: DBSession = Depends(get_db),
) -> RecomputeResponse:
    """Recompute all business scores + ranks for a period.

    period=current (default) or period=previous
    """
    if period == "current":
        ps, pe = scoring_engine.current_period()
    else:
        ps, pe = scoring_engine.previous_period()

    out = lb_service.recompute_scores(db, period_start=ps, period_end=pe)
    return RecomputeResponse(**out)
