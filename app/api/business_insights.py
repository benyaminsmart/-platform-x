"""Business Insights API (Phase 26, Step 5).

Prefix: /business/api/insights

Covers occupancy, heatmaps, revenue forecast, and predictive capacity.
All endpoints require business auth and are tenant-scoped.

NOTE: No 'from __future__ import annotations' in this file (pydantic +
FastAPI route body pitfall — see HANDOFF).
"""

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services import capacity_forecast, heatmap, occupancy, revenue_forecast


router = APIRouter(prefix="/business/api/insights", tags=["business-insights"])


# ---------- Schemas ----------


class OccupancySummaryResponse(BaseModel):
    from_date: str
    to_date: str
    days: int
    total_bookings: int
    total_guests: int
    booked_nights: int
    capacity_nights: int
    occupancy_pct: float
    note: str | None = None


class OccupancyTrendResponse(BaseModel):
    days: int
    current: dict[str, Any]
    previous: dict[str, Any]
    occupancy_delta_pct: float | None


class ByServiceItem(BaseModel):
    service_id: str
    service_name: str
    service_type: str
    capacity: int
    capacity_nights: int
    booked_nights: int
    bookings_count: int
    occupancy_pct: float


class DayOfWeekResponse(BaseModel):
    days: int
    from_date: str
    to_date: str
    total_bookings: int
    items: list[dict[str, Any]]


class HourOfDayResponse(BaseModel):
    days: int
    total_bookings: int
    items: list[dict[str, Any]]
    note: str | None = None


class CalendarResponse(BaseModel):
    days: int
    from_date: str
    to_date: str
    peak: dict[str, Any] | None = None
    items: list[dict[str, Any]]


class ForecastResponse(BaseModel):
    metrics: dict[str, Any]
    advice: str | None = None


class AvailableCapacityResponse(BaseModel):
    from_date: str
    to_date: str
    days: int
    total_capacity_per_day: int
    items: list[dict[str, Any]]
    summary: dict[str, Any]
    note: str | None = None


class NextAvailableResponse(BaseModel):
    service_id: str
    service_name: str
    guests: int
    capacity: int | None
    next_date: str | None
    available_on_date: int | None = None
    note: str | None = None


# ---------- Occupancy ----------


@router.get("/occupancy", response_model=OccupancySummaryResponse)
@limiter.limit("60/minute")
def occupancy_summary(
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> OccupancySummaryResponse:
    today = date.today()
    to_date = today + timedelta(days=1)
    from_date = to_date - timedelta(days=days)
    return OccupancySummaryResponse(**occupancy.occupancy_summary(db, tenant, from_date=from_date, to_date=to_date))


@router.get("/occupancy/trend", response_model=OccupancyTrendResponse)
@limiter.limit("60/minute")
def occupancy_trend(
    request: Request,
    days: int = Query(default=30, ge=7, le=365),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> OccupancyTrendResponse:
    return OccupancyTrendResponse(**occupancy.occupancy_trend(db, tenant, days=days))


@router.get("/occupancy/by-service", response_model=list[ByServiceItem])
@limiter.limit("60/minute")
def occupancy_by_service(
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> list[ByServiceItem]:
    today = date.today()
    to_date = today + timedelta(days=1)
    from_date = to_date - timedelta(days=days)
    rows = occupancy.occupancy_by_service(db, tenant, from_date=from_date, to_date=to_date)
    return [ByServiceItem(**r) for r in rows]


# ---------- Heatmaps ----------


@router.get("/heatmap/day-of-week", response_model=DayOfWeekResponse)
@limiter.limit("60/minute")
def heatmap_day_of_week(
    request: Request,
    days: int = Query(default=90, ge=7, le=365),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> DayOfWeekResponse:
    return DayOfWeekResponse(**heatmap.day_of_week_heatmap(db, tenant, days=days))


@router.get("/heatmap/hour-of-day", response_model=HourOfDayResponse)
@limiter.limit("60/minute")
def heatmap_hour_of_day(
    request: Request,
    days: int = Query(default=90, ge=7, le=365),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> HourOfDayResponse:
    return HourOfDayResponse(**heatmap.hour_of_day_heatmap(db, tenant, days=days))


@router.get("/heatmap/calendar", response_model=CalendarResponse)
@limiter.limit("60/minute")
def heatmap_calendar(
    request: Request,
    days: int = Query(default=90, ge=7, le=365),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> CalendarResponse:
    return CalendarResponse(**heatmap.calendar_heatmap(db, tenant, days=days))


# ---------- Revenue forecast ----------


@router.get("/revenue/forecast", response_model=ForecastResponse)
@limiter.limit("15/minute")
def revenue_forecast_endpoint(
    request: Request,
    days: int = Query(default=30, ge=7, le=180),
    with_advice: bool = Query(default=False),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> ForecastResponse:
    if with_advice:
        out = revenue_forecast.forecast_with_advice(db, tenant, days=days)
        return ForecastResponse(metrics=out["metrics"], advice=out["advice"])
    m = revenue_forecast.forecast_revenue(db, tenant, days=days)
    return ForecastResponse(metrics=m, advice=None)


# ---------- Capacity ----------


@router.get("/capacity/available", response_model=AvailableCapacityResponse)
@limiter.limit("60/minute")
def capacity_available(
    request: Request,
    days: int = Query(default=30, ge=1, le=180),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> AvailableCapacityResponse:
    today = date.today()
    to_date = today + timedelta(days=days)
    return AvailableCapacityResponse(
        **capacity_forecast.available_capacity(db, tenant, from_date=today, to_date=to_date)
    )


@router.get("/capacity/near-full", response_model=dict)
@limiter.limit("60/minute")
def capacity_near_full(
    request: Request,
    days: int = Query(default=30, ge=1, le=180),
    threshold: float = Query(default=90.0, ge=10.0, le=100.0),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict:
    today = date.today()
    to_date = today + timedelta(days=days)
    return capacity_forecast.near_fully_booked(
        db, tenant, from_date=today, to_date=to_date, threshold_pct=threshold
    )


@router.get("/capacity/next-available/{service_id}", response_model=NextAvailableResponse)
@limiter.limit("60/minute")
def capacity_next_available(
    request: Request,
    service_id: str,
    guests: int = Query(default=1, ge=1, le=50),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> NextAvailableResponse:
    try:
        out = capacity_forecast.next_available_date(
            db, tenant, service_id=service_id, guests=guests
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return NextAvailableResponse(**out)
