"""Market Insights service — anonymized peer benchmarks for a tenant.

Design principles:
- NEVER exposes another tenant's identity.
- Only aggregated values (median, quartiles, counts) are returned.
- All numbers computed from real DB data (Tenant + Service + Booking).
- Cohort = tenants in the same category (config.type), active, excluding self.
- Region = last segment of config.location (e.g., 'UAE', 'Dubai').
"""

from datetime import date, timedelta
from statistics import median
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant


_EXCLUDED_STATUSES = ("cancelled",)
CATEGORY_FROM_TYPE = {
    "hotel": "hotels",
    "restaurant": "restaurants",
    "travel_agency": "travel",
    "entertainment": "entertainment",
}


def _round2(v: float) -> float:
    return round(float(v), 2)


def _pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return _round2((numerator / denominator) * 100)


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    k = max(0, min(len(sorted_values) - 1, int(round((len(sorted_values) - 1) * pct))))
    return float(sorted_values[k])


def _tenant_category(t: Tenant) -> str:
    cfg = t.config or {}
    return CATEGORY_FROM_TYPE.get((cfg.get("type") or "").lower(), "other")


def _tenant_region(t: Tenant) -> str | None:
    cfg = t.config or {}
    loc = cfg.get("location")
    if not isinstance(loc, str) or not loc.strip():
        return None
    parts = [p.strip() for p in loc.split(",") if p.strip()]
    return parts[-1] if parts else None


def _services_count(db: DBSession, tenant_id: str) -> int:
    return (
        db.query(func.count(Service.id))
        .filter(Service.tenant_id == tenant_id, Service.status == "active")
        .scalar()
        or 0
    )


def _bookings_30d(db: DBSession, tenant_id: str, *, today: date) -> int:
    from_d = today - timedelta(days=30)
    return (
        db.query(func.count(Booking.id))
        .filter(
            Booking.tenant_id == tenant_id,
            Booking.status.notin_(_EXCLUDED_STATUSES),
            Booking.check_in >= from_d,
        )
        .scalar()
        or 0
    )


def _avg_price(db: DBSession, tenant_id: str) -> float:
    v = (
        db.query(func.avg(Service.price))
        .filter(Service.tenant_id == tenant_id, Service.status == "active")
        .scalar()
    )
    return float(v) if v is not None else 0.0


# ---------- Category summary ----------


def category_summary(
    db: DBSession,
    *,
    category: str,
    exclude_tenant_id: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Return anonymized aggregate metrics for a category."""
    today = today or date.today()

    tenants = (
        db.query(Tenant)
        .filter(Tenant.status == "active", Tenant.deleted_at.is_(None))
        .all()
    )
    peers = [
        t for t in tenants
        if _tenant_category(t) == category and t.id != (exclude_tenant_id or "")
    ]

    if not peers:
        return {
            "category": category,
            "cohort_size": 0,
            "note": "no peers in this category yet",
        }

    prices: list[float] = []
    ratings: list[float] = []
    service_counts: list[int] = []
    bookings_30: list[int] = []

    for t in peers:
        p = _avg_price(db, t.id)
        if p > 0:
            prices.append(p)
        cfg = t.config or {}
        r = cfg.get("rating")
        if isinstance(r, (int, float)) and r > 0:
            ratings.append(float(r))
        service_counts.append(_services_count(db, t.id))
        bookings_30.append(_bookings_30d(db, t.id, today=today))

    def _quartiles(values: list[float]) -> dict[str, float] | None:
        if not values:
            return None
        s = sorted(values)
        return {
            "min": _round2(s[0]),
            "p25": _round2(_percentile(s, 0.25)),
            "median": _round2(median(s)),
            "p75": _round2(_percentile(s, 0.75)),
            "max": _round2(s[-1]),
            "avg": _round2(sum(s) / len(s)),
        }

    return {
        "category": category,
        "cohort_size": len(peers),
        "metrics": {
            "avg_price": _quartiles(prices),
            "rating": _quartiles(ratings),
            "service_count": _quartiles([float(x) for x in service_counts]),
            "bookings_last_30d": _quartiles([float(x) for x in bookings_30]),
        },
    }


# ---------- Tenant position ----------


def _percentile_of(value: float, sorted_values: list[float]) -> float:
    """Return the % of values below `value` (0..100)."""
    if not sorted_values:
        return 0.0
    below = sum(1 for v in sorted_values if v < value)
    return _round2((below / len(sorted_values)) * 100)


def tenant_position(
    db: DBSession,
    tenant: Tenant,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Return this tenant's percentile within its category for key metrics."""
    today = today or date.today()
    cat = _tenant_category(tenant)

    tenants = (
        db.query(Tenant)
        .filter(Tenant.status == "active", Tenant.deleted_at.is_(None))
        .all()
    )
    peers = [t for t in tenants if _tenant_category(t) == cat and t.id != tenant.id]
    if not peers:
        return {"category": cat, "cohort_size": 0, "positions": None}

    prices = [_avg_price(db, t.id) for t in peers]
    prices = [p for p in prices if p > 0]
    ratings = [
        float(t.config.get("rating"))
        for t in peers
        if isinstance((t.config or {}).get("rating"), (int, float))
    ]
    services = [float(_services_count(db, t.id)) for t in peers]
    b30 = [float(_bookings_30d(db, t.id, today=today)) for t in peers]

    my_price = _avg_price(db, tenant.id)
    my_rating = (tenant.config or {}).get("rating")
    my_services = float(_services_count(db, tenant.id))
    my_b30 = float(_bookings_30d(db, tenant.id, today=today))

    def _pos(my_val: float, arr: list[float]) -> dict[str, Any] | None:
        if not arr or my_val <= 0:
            return None
        return {
            "value": _round2(my_val),
            "percentile": _percentile_of(my_val, sorted(arr)),
        }

    return {
        "category": cat,
        "cohort_size": len(peers),
        "positions": {
            "avg_price": _pos(my_price, prices),
            "rating": _pos(float(my_rating), ratings) if my_rating else None,
            "service_count": _pos(my_services, services),
            "bookings_last_30d": _pos(my_b30, b30),
        },
    }


# ---------- Region summary ----------


def region_summary(
    db: DBSession,
    *,
    region: str,
    exclude_tenant_id: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Aggregate per region (last segment of config.location)."""
    today = today or date.today()
    tenants = (
        db.query(Tenant)
        .filter(Tenant.status == "active", Tenant.deleted_at.is_(None))
        .all()
    )
    peers = [
        t for t in tenants
        if _tenant_region(t) and _tenant_region(t).lower() == region.lower()
        and t.id != (exclude_tenant_id or "")
    ]
    if not peers:
        return {"region": region, "cohort_size": 0}

    prices = [_avg_price(db, t.id) for t in peers]
    prices = [p for p in prices if p > 0]
    cats: dict[str, int] = {}
    for t in peers:
        c = _tenant_category(t)
        cats[c] = cats.get(c, 0) + 1

    return {
        "region": region,
        "cohort_size": len(peers),
        "categories": cats,
        "avg_price": _round2(sum(prices) / len(prices)) if prices else None,
        "median_price": _round2(median(prices)) if prices else None,
    }


# ---------- Combined ----------


def market_insights(db: DBSession, tenant: Tenant) -> dict[str, Any]:
    """Return category + position + region insights for the tenant."""
    cat = _tenant_category(tenant)
    region = _tenant_region(tenant)

    out: dict[str, Any] = {
        "tenant_category": cat,
        "tenant_region": region,
        "category_summary": category_summary(db, category=cat, exclude_tenant_id=tenant.id),
        "tenant_position": tenant_position(db, tenant),
    }
    if region:
        out["region_summary"] = region_summary(db, region=region, exclude_tenant_id=tenant.id)
    else:
        out["region_summary"] = None
    return out
