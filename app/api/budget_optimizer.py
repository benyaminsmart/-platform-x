"""Budget Optimizer API (Phase 50, Step 2).

  POST /api/budget-optimize        public, no auth

Returns an optimal package + AI rationale for a given budget.

NOTE: no 'from __future__ import annotations' in this file.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.services.ai import budget_optimizer as bo


router = APIRouter(prefix="/api", tags=["budget-optimizer"])


class OptimizeRequest(BaseModel):
    budget: float = Field(gt=0, le=1_000_000)
    city: str | None = Field(default=None, max_length=120)
    days: int = Field(default=3, ge=1, le=30)
    guests: int = Field(default=2, ge=1, le=50)
    currency: str = Field(default="AED", max_length=5)
    language: str = Field(default="en", pattern="^(en|ar|fil|hi)$")


class PackageItem(BaseModel):
    category: str
    service_id: str | None = None
    service_name: str | None = None
    tenant_slug: str | None = None
    tenant_name: str | None = None
    price: float
    currency: str
    rating: float | None = None
    estimated_total: float
    location: str | None = None


class OptimizeResponse(BaseModel):
    package: list[PackageItem]
    total_estimated: float
    budget: float
    currency: str
    remaining: float
    advice: str
    provider: str


@router.post("/budget-optimize", response_model=OptimizeResponse)
@limiter.limit("15/minute")
def optimize_budget(
    request: Request,
    payload: OptimizeRequest,
    db: DBSession = Depends(get_db),
) -> OptimizeResponse:
    try:
        out = bo.optimize(
            db, city=payload.city, days=payload.days, guests=payload.guests,
            budget=payload.budget, currency=payload.currency,
            language=payload.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return OptimizeResponse(**out)
