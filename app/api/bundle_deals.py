"""Bundle Deals API (Phase 51, Step 2).

  POST /api/bundle-deals         public, no auth

Returns a cross-category bundle + AI pitch.

NOTE: no 'from __future__ import annotations' in this file.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.services.ai import bundle_deals as bd


router = APIRouter(prefix="/api", tags=["bundle-deals"])


class BundleRequest(BaseModel):
    city: str | None = Field(default=None, max_length=120)
    days: int = Field(default=3, ge=1, le=30)
    guests: int = Field(default=2, ge=1, le=50)
    language: str = Field(default="en", pattern="^(en|ar|fil|hi)$")


class BundleItem(BaseModel):
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


class BundleResponse(BaseModel):
    items: list[BundleItem]
    subtotal: float
    discount_percent: int
    discount_amount: float
    total: float
    currency: str
    advice: str
    provider: str


@router.post("/bundle-deals", response_model=BundleResponse)
@limiter.limit("15/minute")
def bundle_deals(
    request: Request,
    payload: BundleRequest,
    db: DBSession = Depends(get_db),
) -> BundleResponse:
    try:
        out = bd.build(
            db, city=payload.city, days=payload.days, guests=payload.guests,
            language=payload.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return BundleResponse(**out)
