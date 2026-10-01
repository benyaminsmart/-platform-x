"""Public Local Experiences API (Phase 65, Step 2).

  GET  /api/local-events                    list events (city + date filters)
  GET  /api/local-events/nearby             nearby events (Haversine)
  POST /api/local-events/recommend          AI recommendation for a location

No auth required. Rate-limited.

NOTE: no 'from __future__ import annotations' in this file.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.services import local_experiences as lx


router = APIRouter(prefix="/api/local-events", tags=["local-experiences"])


class EventItem(BaseModel):
    id: str
    name: str
    category: str
    description: str | None = None
    city: str | None = None
    venue: str | None = None
    lat: float
    lng: float
    start_at: str | None = None
    end_at: str | None = None
    cover_image: str | None = None
    ticket_url: str | None = None


class NearbyItem(EventItem):
    distance_km: float


class RecommendRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    radius_km: float = Field(default=15.0, ge=0.1, le=200)
    on_date: date | None = None
    language: str = Field(default="en", pattern="^(en|ar|fil|hi)$")


class RecommendResponse(BaseModel):
    events: list[NearbyItem]
    advice: str
    provider: str


@router.get("", response_model=list[EventItem])
@limiter.limit("60/minute")
def list_local_events(
    request: Request,
    city: str | None = Query(default=None, max_length=100),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: DBSession = Depends(get_db),
) -> list[EventItem]:
    rows = lx.list_events(db, city=city, date_from=date_from, date_to=date_to, limit=limit)
    return [EventItem(**r) for r in rows]


@router.get("/nearby", response_model=list[NearbyItem])
@limiter.limit("60/minute")
def nearby_local_events(
    request: Request,
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    radius_km: float = Query(default=15.0, ge=0.1, le=200),
    on_date: date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: DBSession = Depends(get_db),
) -> list[NearbyItem]:
    rows = lx.nearby(db, lat=lat, lng=lng, radius_km=radius_km,
                     on_date=on_date, limit=limit)
    return [NearbyItem(**r) for r in rows]


@router.post("/recommend", response_model=RecommendResponse)
@limiter.limit("15/minute")
def recommend_local_events(
    request: Request,
    payload: RecommendRequest,
    db: DBSession = Depends(get_db),
) -> RecommendResponse:
    from app.core.config import settings
    if not settings.AI_ENABLED:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="AI disabled")
    try:
        out = lx.recommend(
            db, lat=payload.lat, lng=payload.lng,
            radius_km=payload.radius_km, on_date=payload.on_date,
            language=payload.language,
        )
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RecommendResponse(**out)
