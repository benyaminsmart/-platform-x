"""Public Search API (Phase 30, Step 2 — Wave 0 part A).

Prefix: /api/search

Public, no auth. Returns cross-tenant search results with availability
filtering, price range, category, and sort options.

NOTE: no 'from __future__ import annotations' (pydantic + FastAPI route
body pitfall — see HANDOFF).
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.services import search_service


router = APIRouter(prefix="/api", tags=["search"])


# ---------- Schemas ----------


class SearchItem(BaseModel):
    service_id: str
    service_name: str
    service_type: str
    price: float
    currency: str
    capacity: int | None
    description: str | None
    tenant_id: str
    tenant_slug: str
    tenant_name: str
    category: str
    location: str | None
    rating: float | None
    reviews_count: int
    cover_image: str | None


class SearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    check_in: str | None
    check_out: str | None
    guests: int
    sort: str
    items: list[SearchItem]


# ---------- Endpoint ----------


@router.get("/search", response_model=SearchResponse)
@limiter.limit("60/minute")
def search(
    request: Request,
    check_in: date | None = Query(default=None),
    check_out: date | None = Query(default=None),
    guests: int = Query(default=1, ge=1, le=50),
    category: str | None = Query(default=None, max_length=50),
    tenant: str | None = Query(default=None, max_length=100),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    sort: str = Query(default="popular", pattern="^(popular|price_asc|price_desc|rating)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: DBSession = Depends(get_db),
) -> SearchResponse:
    """Search services across all active tenants."""
    out = search_service.search_services(
        db,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        category=category,
        tenant_slug=tenant,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return SearchResponse(**out)
