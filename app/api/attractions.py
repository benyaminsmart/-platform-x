"""Public Attractions API (Phase 41, Step 2).

  GET /api/attractions
  GET /api/attractions/nearby?lat=&lng=&radius_km=&limit=
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.services import attraction_service


router = APIRouter(prefix="/api/attractions", tags=["attractions"])


class AttractionItem(BaseModel):
    id: str
    name: str
    category: str
    description: str | None
    lat: float
    lng: float
    city: str | None
    cover_image: str | None


class NearbyItem(AttractionItem):
    distance_km: float


@router.get("", response_model=list[AttractionItem])
@limiter.limit("60/minute")
def list_attractions(
    request: Request,
    db: DBSession = Depends(get_db),
) -> list[AttractionItem]:
    rows = attraction_service.list_all(db)
    return [
        AttractionItem(
            id=a.id, name=a.name, category=a.category, description=a.description,
            lat=a.lat, lng=a.lng, city=a.city, cover_image=a.cover_image,
        )
        for a in rows
    ]


@router.get("/nearby", response_model=list[NearbyItem])
@limiter.limit("60/minute")
def nearby(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=10.0, ge=0.1, le=200),
    limit: int = Query(default=20, ge=1, le=100),
    db: DBSession = Depends(get_db),
) -> list[NearbyItem]:
    rows = attraction_service.nearby(db, lat=lat, lng=lng, radius_km=radius_km, limit=limit)
    return [NearbyItem(**r) for r in rows]
