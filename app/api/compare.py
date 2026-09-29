"""Compare services API (Phase 33, Step 5).

Public endpoint:
  GET /api/compare?ids=id1,id2,id3

Returns details for 2-4 services side by side.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.service import Service
from app.models.tenant import Tenant


router = APIRouter(prefix="/api", tags=["compare"])

MAX_COMPARE = 4


class CompareItem(BaseModel):
    service_id: str
    service_name: str
    service_type: str
    price: float
    currency: str
    capacity: int | None
    description: str | None
    images: list[str]
    attributes: dict
    tenant_id: str
    tenant_slug: str
    tenant_name: str
    category: str
    location: str | None
    rating: float | None
    reviews_count: int
    cover_image: str | None


class CompareResponse(BaseModel):
    items: list[CompareItem]


def _cat(t: Tenant) -> str:
    m = {"hotel": "hotels", "restaurant": "restaurants",
         "travel_agency": "travel", "entertainment": "entertainment"}
    return m.get(((t.config or {}).get("type") or "").lower(), "other")


@router.get("/compare", response_model=CompareResponse)
@limiter.limit("30/minute")
def compare(
    request: Request,
    ids: str = Query(min_length=3, max_length=400),
    db: DBSession = Depends(get_db),
) -> CompareResponse:
    """Compare 2-4 services side by side (public)."""
    parts = [x.strip() for x in ids.split(",") if x.strip()]
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 service IDs")
    if len(parts) > MAX_COMPARE:
        parts = parts[:MAX_COMPARE]

    rows = (
        db.query(Service, Tenant)
        .join(Tenant, Tenant.id == Service.tenant_id)
        .filter(
            Service.id.in_(parts),
            Service.status == "active",
            Tenant.status == "active",
        )
        .all()
    )
    # preserve user order
    by_id = {s.id: (s, t) for s, t in rows}
    ordered = [by_id[i] for i in parts if i in by_id]

    items = []
    for s, t in ordered:
        cfg = t.config or {}
        items.append(CompareItem(
            service_id=s.id,
            service_name=s.name,
            service_type=s.type,
            price=float(s.price),
            currency=s.currency,
            capacity=s.capacity,
            description=s.description,
            images=list(s.image_urls or []),
            attributes=dict(s.attributes or {}),
            tenant_id=t.id,
            tenant_slug=t.slug,
            tenant_name=t.name,
            category=_cat(t),
            location=cfg.get("location"),
            rating=cfg.get("rating"),
            reviews_count=cfg.get("reviews_count") or 0,
            cover_image=cfg.get("cover_image"),
        ))
    return CompareResponse(items=items)
