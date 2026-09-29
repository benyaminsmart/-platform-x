"""Predictive capacity — how full is the business going forward.

Data sources:
- Booking (status != cancelled, check_in <= day < check_out)
- Service (status=active, capacity set)

Only services that carry `capacity` participate. Services without capacity
(such as menu items) are ignored.
"""

from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant


_EXCLUDED_STATUSES = ("cancelled",)


def _round2(v: float) -> float:
    return round(float(v), 2)


def _active_capacity_services(db: DBSession, tenant: Tenant) -> list[Service]:
    return (
        db.query(Service)
        .filter(
            Service.tenant_id == tenant.id,
            Service.status == "active",
            Service.capacity.isnot(None),
        )
        .all()
    )


def _overlapping_bookings(
    db: DBSession,
    tenant: Tenant,
    *,
    from_date: date,
    to_date: date,
) -> list[Booking]:
    return (
        db.query(Booking)
        .filter(
            Booking.tenant_id == tenant.id,
            Booking.status.notin_(_EXCLUDED_STATUSES),
            Booking.check_in < to_date,
        )
        .all()
    )


# ---------- Available capacity ----------


def available_capacity(
    db: DBSession,
    tenant: Tenant,
    *,
    from_date: date,
    to_date: date,
) -> dict[str, Any]:
    """Return a per-day series of available capacity across the tenant.

    For each day:
      - total_capacity = sum of active capacity-service.capacity
      - booked = number of overlapping bookings on that day
      - available = max(0, total_capacity - booked)
      - occupancy_pct = booked / total_capacity * 100 (if > 0)
    """
    if to_date <= from_date:
        return {
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "days": 0,
            "total_capacity_per_day": 0,
            "items": [],
            "summary": {"min_available": 0, "max_available": 0, "avg_available": 0.0},
            "note": "empty range",
        }

    services = _active_capacity_services(db, tenant)
    total_capacity = sum(int(s.capacity or 0) for s in services)
    bookings = _overlapping_bookings(db, tenant, from_date=from_date, to_date=to_date)

    items: list[dict[str, Any]] = []
    d = from_date
    while d < to_date:
        day = d
        next_day = day + timedelta(days=1)
        booked = 0
        for b in bookings:
            end = b.check_out or (b.check_in + timedelta(days=1))
            if b.check_in <= day < end:
                booked += 1
        available = max(0, total_capacity - booked)
        occupancy_pct = _round2((booked / total_capacity) * 100) if total_capacity else 0.0
        items.append({
            "date": day.isoformat(),
            "booked": booked,
            "available": available,
            "total_capacity": total_capacity,
            "occupancy_pct": occupancy_pct,
        })
        d = next_day

    availabilities = [x["available"] for x in items]
    return {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "days": (to_date - from_date).days,
        "total_capacity_per_day": total_capacity,
        "items": items,
        "summary": {
            "min_available": min(availabilities) if availabilities else 0,
            "max_available": max(availabilities) if availabilities else 0,
            "avg_available": _round2(sum(availabilities) / len(availabilities)) if availabilities else 0.0,
        },
        "note": None if total_capacity > 0 else "no active capacity-bearing services",
    }


# ---------- Near fully booked ----------


def near_fully_booked(
    db: DBSession,
    tenant: Tenant,
    *,
    from_date: date,
    to_date: date,
    threshold_pct: float = 90.0,
) -> dict[str, Any]:
    """Return days where occupancy_pct >= threshold."""
    summary = available_capacity(db, tenant, from_date=from_date, to_date=to_date)
    hot = [x for x in summary["items"] if x["occupancy_pct"] >= threshold_pct]
    return {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "threshold_pct": threshold_pct,
        "total_capacity_per_day": summary["total_capacity_per_day"],
        "count": len(hot),
        "items": hot,
    }


# ---------- Next available date ----------


def next_available_date(
    db: DBSession,
    tenant: Tenant,
    *,
    service_id: str,
    guests: int = 1,
    from_date: date | None = None,
    max_search_days: int = 365,
) -> dict[str, Any]:
    """Find the first date with enough free capacity for one service.

    free = service.capacity - overlapping_bookings_on_that_day
    """
    from_date = from_date or date.today()
    guests = max(1, int(guests))
    max_search_days = max(1, min(int(max_search_days), 730))

    s = (
        db.query(Service)
        .filter(Service.id == service_id, Service.tenant_id == tenant.id)
        .one_or_none()
    )
    if s is None:
        raise ValueError("service not found")
    if s.capacity is None:
        return {
            "service_id": s.id,
            "service_name": s.name,
            "guests": guests,
            "capacity": None,
            "next_date": None,
            "note": "service has no capacity; always available",
        }

    capacity = int(s.capacity)
    if guests > capacity:
        return {
            "service_id": s.id,
            "service_name": s.name,
            "guests": guests,
            "capacity": capacity,
            "next_date": None,
            "note": "requested guests exceed capacity",
        }

    # Fetch bookings for this service in the search window
    search_end = from_date + timedelta(days=max_search_days)
    bookings = (
        db.query(Booking)
        .filter(
            Booking.tenant_id == tenant.id,
            Booking.service_id == s.id,
            Booking.status.notin_(_EXCLUDED_STATUSES),
            Booking.check_in < search_end,
        )
        .all()
    )

    d = from_date
    while d < search_end:
        day = d
        next_day = day + timedelta(days=1)
        booked = 0
        for b in bookings:
            end = b.check_out or (b.check_in + timedelta(days=1))
            if b.check_in <= day < end:
                booked += 1
        if capacity - booked >= guests:
            return {
                "service_id": s.id,
                "service_name": s.name,
                "guests": guests,
                "capacity": capacity,
                "next_date": day.isoformat(),
                "available_on_date": capacity - booked,
                "note": None,
            }
        d = next_day

    return {
        "service_id": s.id,
        "service_name": s.name,
        "guests": guests,
        "capacity": capacity,
        "next_date": None,
        "note": f"no availability within {max_search_days} days",
    }
