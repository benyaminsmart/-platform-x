"""Availability API (Phase 30, Step 4 — Wave 0 part A).

Public endpoint:
  GET /api/availability/{tenant_slug}?days=30

Returns per-service, per-day availability for the given tenant over the
next N days. Days with no capacity for a service are marked "full".

NOTE: no 'from __future__ import annotations'.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant


router = APIRouter(prefix="/api", tags=["availability"])

_EXCLUDED_STATUSES = ("cancelled",)


class ServiceAvailability(BaseModel):
    service_id: str
    service_name: str
    service_type: str
    capacity: int | None
    days: list[dict]


class AvailabilityResponse(BaseModel):
    tenant_id: str
    tenant_slug: str
    from_date: str
    to_date: str
    services: list[ServiceAvailability]


@router.get("/availability/{tenant_slug}", response_model=AvailabilityResponse)
@limiter.limit("60/minute")
def get_availability(
    request: Request,
    tenant_slug: str,
    days: int = Query(default=30, ge=1, le=90),
    db: DBSession = Depends(get_db),
) -> AvailabilityResponse:
    """Return per-service availability for the next N days."""
    tenant = (
        db.query(Tenant)
        .filter(Tenant.slug == tenant_slug, Tenant.status == "active", Tenant.deleted_at.is_(None))
        .one_or_none()
    )
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    today = date.today()
    to_date = today + timedelta(days=days)

    services = (
        db.query(Service)
        .filter(Service.tenant_id == tenant.id, Service.status == "active")
        .order_by(Service.display_order, Service.name)
        .all()
    )

    bookings = (
        db.query(Booking)
        .filter(
            Booking.tenant_id == tenant.id,
            Booking.status.notin_(_EXCLUDED_STATUSES),
            Booking.check_in < to_date,
        )
        .all()
    )
    overlapping = [
        b for b in bookings
        if (b.check_out or (b.check_in + timedelta(days=1))) > today
    ]

    out_services: list[ServiceAvailability] = []
    for s in services:
        cap = s.capacity
        day_list: list[dict] = []
        d = today
        while d < to_date:
            if cap is None:
                booked = 0
                free = None  # unlimited
            else:
                booked = 0
                for b in overlapping:
                    if b.service_id != s.id:
                        continue
                    end = b.check_out or (b.check_in + timedelta(days=1))
                    if b.check_in <= d < end:
                        booked += 1
                free = max(0, int(cap) - booked)
            day_list.append({
                "date": d.isoformat(),
                "booked": booked,
                "free": free,
                "full": (free == 0) if free is not None else False,
            })
            d += timedelta(days=1)
        out_services.append(ServiceAvailability(
            service_id=s.id,
            service_name=s.name,
            service_type=s.type,
            capacity=cap,
            days=day_list,
        ))

    return AvailabilityResponse(
        tenant_id=tenant.id,
        tenant_slug=tenant.slug,
        from_date=today.isoformat(),
        to_date=to_date.isoformat(),
        services=out_services,
    )
