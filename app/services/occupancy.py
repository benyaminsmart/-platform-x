"""Occupancy service — compute real-time occupancy metrics.

Data sources (real):
- Booking.check_in / check_out / status / guests
- Service.capacity (for room-type services)

Definitions:
- Occupancy rate = booked_nights / capacity_nights * 100
- "Booked" = status != cancelled (we count pending + confirmed + checked_in + checked_out)
- A night counts if check_in <= night < check_out
- Services without capacity are excluded from occupancy rate (counted separately)
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant


_EXCLUDED_STATUSES = ("cancelled",)


# ---------- Helpers ----------


def _iter_nights(from_date: date, to_date: date):
    """Yield each date from from_date to to_date (exclusive end)."""
    d = from_date
    while d < to_date:
        yield d
        d += timedelta(days=1)


def _round2(v: float) -> float:
    return round(float(v), 2)


def _pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return _round2((numerator / denominator) * 100)


# ---------- Summary ----------


def occupancy_summary(
    db: DBSession,
    tenant: Tenant,
    *,
    from_date: date,
    to_date: date,
) -> dict[str, Any]:
    """Return overall occupancy summary for the tenant between two dates.

    Counts only bookings that overlap the window.
    """
    if to_date <= from_date:
        return {
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "days": 0,
            "total_bookings": 0,
            "total_guests": 0,
            "booked_nights": 0,
            "capacity_nights": 0,
            "occupancy_pct": 0.0,
            "note": "empty range",
        }

    # All bookings overlapping the window, excluding cancelled
    bookings = (
        db.query(Booking)
        .filter(
            Booking.tenant_id == tenant.id,
            Booking.status.notin_(_EXCLUDED_STATUSES),
            Booking.check_in < to_date,
        )
        .all()
    )
    # Filter to those with check_out > from_date (i.e., overlap in the window)
    overlapping = []
    for b in bookings:
        end = b.check_out or (b.check_in + timedelta(days=1))
        if end > from_date:
            overlapping.append(b)

    total_bookings = len(overlapping)
    total_guests = sum(int(b.guests or 0) for b in overlapping)

    # Booked nights (clamped to window)
    booked_nights = 0
    for b in overlapping:
        start = max(b.check_in, from_date)
        end = min(b.check_out or (b.check_in + timedelta(days=1)), to_date)
        if end > start:
            booked_nights += (end - start).days

    # Capacity nights: sum of capacities of active room-type services × days
    active_services = (
        db.query(Service)
        .filter(
            Service.tenant_id == tenant.id,
            Service.status == "active",
            Service.capacity.isnot(None),
        )
        .all()
    )
    capacity_per_night = sum(int(s.capacity or 0) for s in active_services)
    days = (to_date - from_date).days
    capacity_nights = capacity_per_night * days

    return {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "days": days,
        "total_bookings": total_bookings,
        "total_guests": total_guests,
        "booked_nights": booked_nights,
        "capacity_nights": capacity_nights,
        "occupancy_pct": _pct(booked_nights, capacity_nights),
        "note": None if capacity_nights > 0 else "no capacity-bearing services",
    }


# ---------- Per-service breakdown ----------


def occupancy_by_service(
    db: DBSession,
    tenant: Tenant,
    *,
    from_date: date,
    to_date: date,
) -> list[dict[str, Any]]:
    """Return occupancy per active service (only services with capacity)."""
    if to_date <= from_date:
        return []

    days = (to_date - from_date).days

    services = (
        db.query(Service)
        .filter(
            Service.tenant_id == tenant.id,
            Service.status == "active",
            Service.capacity.isnot(None),
        )
        .all()
    )
    if not services:
        return []

    # Fetch overlapping bookings
    bookings = (
        db.query(Booking)
        .filter(
            Booking.tenant_id == tenant.id,
            Booking.status.notin_(_EXCLUDED_STATUSES),
            Booking.check_in < to_date,
        )
        .all()
    )

    out: list[dict[str, Any]] = []
    for s in services:
        capacity = int(s.capacity or 0)
        capacity_nights = capacity * days
        booked_nights = 0
        bookings_count = 0

        for b in bookings:
            if b.service_id != s.id:
                continue
            end = b.check_out or (b.check_in + timedelta(days=1))
            if end <= from_date:
                continue
            start = max(b.check_in, from_date)
            stop = min(end, to_date)
            if stop > start:
                booked_nights += (stop - start).days
                bookings_count += 1

        out.append({
            "service_id": s.id,
            "service_name": s.name,
            "service_type": s.type,
            "capacity": capacity,
            "capacity_nights": capacity_nights,
            "booked_nights": booked_nights,
            "bookings_count": bookings_count,
            "occupancy_pct": _pct(booked_nights, capacity_nights),
        })

    out.sort(key=lambda r: -r["occupancy_pct"])
    return out


# ---------- Trend ----------


def occupancy_trend(
    db: DBSession,
    tenant: Tenant,
    *,
    today: date | None = None,
    days: int = 30,
) -> dict[str, Any]:
    """Return trend for the last `days` vs the previous `days` window.

    Provides:
      - current window summary
      - previous window summary
      - occupancy_pct change
    """
    today = today or date.today()
    days = max(7, min(int(days), 365))

    cur_end = today + timedelta(days=1)  # include today
    cur_start = cur_end - timedelta(days=days)
    prev_end = cur_start
    prev_start = prev_end - timedelta(days=days)

    current = occupancy_summary(db, tenant, from_date=cur_start, to_date=cur_end)
    previous = occupancy_summary(db, tenant, from_date=prev_start, to_date=prev_end)

    delta_pct = None
    if previous["occupancy_pct"] > 0:
        delta_pct = _round2(
            ((current["occupancy_pct"] - previous["occupancy_pct"]) / previous["occupancy_pct"]) * 100
        )

    return {
        "days": days,
        "current": current,
        "previous": previous,
        "occupancy_delta_pct": delta_pct,
    }
