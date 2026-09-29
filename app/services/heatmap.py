"""Heatmap service — distribution of bookings by time dimensions.

Data source: Booking (real). Excludes cancelled.

Three views:
- day_of_week: which weekdays get the most bookings (Mon..Sun)
- hour_of_day: which hours of day new bookings are created
  (proxy: Booking.created_at hour — Booking model has no explicit time)
- calendar: daily booking counts over the recent window
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.tenant import Tenant


_EXCLUDED_STATUSES = ("cancelled",)
_WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _round2(v: float) -> float:
    return round(float(v), 2)


def _bookings_in_window(
    db: DBSession,
    tenant: Tenant,
    *,
    from_date: date,
    to_date: date,
) -> list[Booking]:
    """Return bookings whose check_in is inside [from_date, to_date)."""
    return (
        db.query(Booking)
        .filter(
            Booking.tenant_id == tenant.id,
            Booking.status.notin_(_EXCLUDED_STATUSES),
            Booking.check_in >= from_date,
            Booking.check_in < to_date,
        )
        .all()
    )


# ---------- Day of week ----------


def day_of_week_heatmap(
    db: DBSession,
    tenant: Tenant,
    *,
    today: date | None = None,
    days: int = 90,
) -> dict[str, Any]:
    """Return bookings + revenue per weekday over the recent window."""
    today = today or date.today()
    days = max(7, min(int(days), 365))
    to_date = today + timedelta(days=1)
    from_date = to_date - timedelta(days=days)

    buckets: dict[int, dict[str, float]] = {
        i: {"bookings": 0, "revenue": 0.0} for i in range(7)
    }

    for b in _bookings_in_window(db, tenant, from_date=from_date, to_date=to_date):
        wd = b.check_in.weekday()  # 0=Mon .. 6=Sun
        buckets[wd]["bookings"] += 1
        buckets[wd]["revenue"] += float(b.total_amount or 0)

    items = [
        {
            "weekday": i,
            "label": _WEEKDAY_NAMES[i],
            "bookings": int(buckets[i]["bookings"]),
            "revenue_aed": _round2(buckets[i]["revenue"]),
        }
        for i in range(7)
    ]
    total = sum(x["bookings"] for x in items)
    # Percentage share
    for x in items:
        x["share_pct"] = _round2((x["bookings"] / total) * 100) if total else 0.0

    return {
        "days": days,
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "total_bookings": total,
        "items": items,
    }


# ---------- Hour of day ----------


def hour_of_day_heatmap(
    db: DBSession,
    tenant: Tenant,
    *,
    today: date | None = None,
    days: int = 90,
) -> dict[str, Any]:
    """Return when bookings are *created*, bucketed by hour (0-23).

    Note: Booking has no explicit time field, so we use created_at as a
    proxy for when guests make their booking.
    """
    today = today or date.today()
    days = max(7, min(int(days), 365))
    to_date = today + timedelta(days=1)
    from_date = to_date - timedelta(days=days)

    buckets: dict[int, dict[str, float]] = {
        i: {"bookings": 0, "revenue": 0.0} for i in range(24)
    }

    # SQLite stores datetimes as naive UTC; compare with naive datetimes.
    created_from = datetime.combine(from_date, datetime.min.time())
    created_to = datetime.combine(to_date, datetime.min.time())

    rows = (
        db.query(Booking)
        .filter(
            Booking.tenant_id == tenant.id,
            Booking.status.notin_(_EXCLUDED_STATUSES),
            Booking.created_at >= created_from,
            Booking.created_at < created_to,
        )
        .all()
    )

    for b in rows:
        if b.created_at is None:
            continue
        dt = b.created_at
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)
        h = dt.hour
        buckets[h]["bookings"] += 1
        buckets[h]["revenue"] += float(b.total_amount or 0)

    items = [
        {
            "hour": i,
            "label": f"{i:02d}:00",
            "bookings": int(buckets[i]["bookings"]),
            "revenue_aed": _round2(buckets[i]["revenue"]),
        }
        for i in range(24)
    ]
    total = sum(x["bookings"] for x in items)
    for x in items:
        x["share_pct"] = _round2((x["bookings"] / total) * 100) if total else 0.0

    return {
        "days": days,
        "total_bookings": total,
        "items": items,
        "note": "Hour is derived from booking creation time.",
    }


# ---------- Calendar ----------


def calendar_heatmap(
    db: DBSession,
    tenant: Tenant,
    *,
    today: date | None = None,
    days: int = 90,
) -> dict[str, Any]:
    """Return a per-day series of bookings (check_in basis) for the last N days."""
    today = today or date.today()
    days = max(7, min(int(days), 365))
    to_date = today + timedelta(days=1)
    from_date = to_date - timedelta(days=days)

    daily: dict[str, dict[str, float]] = defaultdict(lambda: {"bookings": 0, "revenue": 0.0})

    for b in _bookings_in_window(db, tenant, from_date=from_date, to_date=to_date):
        k = b.check_in.isoformat()
        daily[k]["bookings"] += 1
        daily[k]["revenue"] += float(b.total_amount or 0)

    # Emit every day in the range (including zeros) for a clean calendar
    items: list[dict[str, Any]] = []
    d = from_date
    while d < to_date:
        k = d.isoformat()
        v = daily.get(k, {"bookings": 0, "revenue": 0.0})
        items.append({
            "date": k,
            "weekday": d.weekday(),
            "bookings": int(v["bookings"]),
            "revenue_aed": _round2(v["revenue"]),
        })
        d += timedelta(days=1)

    # Compute peak day
    peak = max(items, key=lambda x: x["bookings"]) if items else None
    return {
        "days": days,
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "peak": peak,
        "items": items,
    }
