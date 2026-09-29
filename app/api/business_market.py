"""Business Market Insights API (Phase 27, Step 3).

Prefix: /business/api/market

All endpoints anonymize peer data: only aggregates and percentiles.
No peer identities or ids are ever returned.

NOTE: No 'from __future__ import annotations' (pydantic + FastAPI
route-body pitfall).
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services import market_insights as mi
from app.services.ai import market_analyst


router = APIRouter(prefix="/business/api/market", tags=["business-market"])


# ---------- Schemas ----------


class CategorySummaryResponse(BaseModel):
    category: str
    cohort_size: int
    metrics: dict[str, Any] | None = None
    note: str | None = None


class TenantPositionResponse(BaseModel):
    category: str
    cohort_size: int
    positions: dict[str, Any] | None = None


class RegionSummaryResponse(BaseModel):
    region: str
    cohort_size: int
    categories: dict[str, int] | None = None
    avg_price: float | None = None
    median_price: float | None = None


class InsightResponse(BaseModel):
    metrics: dict[str, Any]
    strengths: list[dict[str, Any]]
    weaknesses: list[dict[str, Any]]
    summary: str
    advice: str
    provider: str


class AIOnlyResponse(BaseModel):
    summary: str
    advice: str
    provider: str


# ---------- Endpoints ----------


@router.get("/summary", response_model=CategorySummaryResponse)
@limiter.limit("30/minute")
def market_summary(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> CategorySummaryResponse:
    """Anonymized aggregate for the tenant's category."""
    cat = mi._tenant_category(tenant)
    out = mi.category_summary(db, category=cat, exclude_tenant_id=tenant.id)
    return CategorySummaryResponse(**out)


@router.get("/position", response_model=TenantPositionResponse)
@limiter.limit("30/minute")
def market_position(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> TenantPositionResponse:
    """Percentile position of this tenant vs peers."""
    out = mi.tenant_position(db, tenant)
    return TenantPositionResponse(**out)


@router.get("/region", response_model=RegionSummaryResponse)
@limiter.limit("30/minute")
def market_region(
    request: Request,
    region: str = Query(min_length=1, max_length=100),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> RegionSummaryResponse:
    """Aggregate info about a specific region (from peers' locations)."""
    out = mi.region_summary(db, region=region, exclude_tenant_id=tenant.id)
    return RegionSummaryResponse(**out)


@router.get("/insights", response_model=InsightResponse)
@limiter.limit("30/minute")
def market_insights_combined(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> InsightResponse:
    """Full market insights: metrics + strengths/weaknesses + fallback text."""
    cat = mi._tenant_category(tenant)
    region = mi._tenant_region(tenant)

    metrics: dict[str, Any] = {
        "tenant_category": cat,
        "tenant_region": region,
        "category_summary": mi.category_summary(db, category=cat, exclude_tenant_id=tenant.id),
        "tenant_position": mi.tenant_position(db, tenant),
    }
    if region:
        metrics["region_summary"] = mi.region_summary(db, region=region, exclude_tenant_id=tenant.id)
    else:
        metrics["region_summary"] = None

    sw = market_analyst.highlight_strengths_and_weaknesses(metrics.get("tenant_position"))
    summary = market_analyst._fallback_summary(metrics)
    advice = market_analyst._fallback_advice(sw)

    return InsightResponse(
        metrics=metrics,
        strengths=sw["strengths"],
        weaknesses=sw["weaknesses"],
        summary=summary,
        advice=advice,
        provider="fallback",
    )


@router.get("/insights/ai", response_model=AIOnlyResponse)
@limiter.limit("10/minute")
def market_insights_ai(
    request: Request,
    language: str = Query(default="en", pattern="^(en|ar|fil|hi)$"),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> AIOnlyResponse:
    """AI-powered interpretation of the tenant's market position."""
    try:
        out = market_analyst.interpret_market(db, tenant, language=language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AIOnlyResponse(summary=out["summary"], advice=out["advice"], provider=out["provider"])
