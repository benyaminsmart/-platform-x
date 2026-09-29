"""Search service — cross-tenant search with date + guests + filters.

Design:
- Cross-tenant: search across all active tenants (like Booking.com).
- Date filter: only returns services with enough free capacity in the
  requested window (based on overlapping bookings).
- Guests: service.capacity >= guests (if capacity is set).
- Category: derived from tenant.config.type.
- Price range: service.price filters.
- Sort: popular (by recent bookings), price_asc, price_desc, rating.
- Paginated.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.services import currency


import math


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points in km."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))



_EXCLUDED_STATUSES = ("cancelled",)
CATEGORY_FROM_TYPE = {
    "hotel": "hotels",
    "restaurant": "restaurants",
    "travel_agency": "travel",
    "entertainment": "entertainment",
}
ALLOWED_SORTS = {"popular", "price_asc", "price_desc", "rating"}


def _tenant_category(t: Tenant) -> str:
    cfg = t.config or {}
    return CATEGORY_FROM_TYPE.get((cfg.get("type") or "").lower(), "other")


def _free_capacity_on_day(
    db: DBSession,
    service: Service,
    day: date,
    overlapping_bookings: list[Booking],
) -> int:
    """Return free capacity for this service on `day`."""
    cap = service.capacity
    if cap is None:
        return 10**9  # unlimited
    booked = 0
    for b in overlapping_bookings:
        if b.service_id != service.id:
            continue
        end = b.check_out or (b.check_in + timedelta(days=1))
        if b.check_in <= day < end:
            booked += 1
    return max(0, int(cap) - booked)


def search_services(
    db: DBSession,
    *,
    check_in: date | None = None,
    check_out: date | None = None,
    guests: int = 1,
    category: str | None = None,
    tenant_slug: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort: str = "popular",
    page: int = 1,
    page_size: int = 20,
    display_currency: str | None = None,
    min_rating: float | None = None,
    service_type: str | None = None,
    location_search: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float | None = None,
) -> dict[str, Any]:
    """Return paginated search results.

    If check_in/check_out are provided, only services with enough free
    capacity in the whole window are returned (for capacity-bearing
    services). Services without capacity are always included.
    """
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 100))
    guests = max(1, int(guests))
    if sort not in ALLOWED_SORTS:
        sort = "popular"

    # 1. Base query: active services on active tenants
    q = (
        db.query(Service, Tenant)
        .join(Tenant, Tenant.id == Service.tenant_id)
        .filter(
            Service.status == "active",
            Tenant.status == "active",
            Tenant.deleted_at.is_(None),
        )
    )
    if tenant_slug:
        q = q.filter(Tenant.slug == tenant_slug)
    if category:
        type_map_reverse = {v: k for k, v in CATEGORY_FROM_TYPE.items()}
        wanted_type = type_map_reverse.get(category)
        if not wanted_type:
            return {"total": 0, "page": page, "page_size": page_size, "items": []}
        # match config.type (JSON) — SQLite JSON path via cast is complex;
        # use Python filter after fetching (bounded by page_size after filtering)
        # Simpler: fetch and filter in Python; we paginate after filtering.
        rows = q.all()
        rows = [(s, t) for (s, t) in rows if _tenant_category(t) == category]
    else:
        rows = q.all()

    if min_price is not None:
        rows = [(s, t) for (s, t) in rows if float(s.price) >= float(min_price)]
    if max_price is not None:
        rows = [(s, t) for (s, t) in rows if float(s.price) <= float(max_price)]

    if min_rating is not None:
        rows = [
            (s, t) for (s, t) in rows
            if float(((t.config or {}).get("rating") or 0)) >= float(min_rating)
        ]

    if service_type:
        rows = [(s, t) for (s, t) in rows if s.type == service_type]

    if location_search:
        needle = location_search.strip().lower()
        if needle:
            def _has_loc(t):
                loc = ((t.config or {}).get("location") or "").lower()
                return needle in loc
            rows = [(s, t) for (s, t) in rows if _has_loc(t)]

    # Geographic filter
    if lat is not None and lng is not None and radius_km is not None and radius_km > 0:
        filtered = []
        for s, t in rows:
            coords = ((t.config or {}).get("coordinates") or {})
            t_lat = coords.get("lat")
            t_lng = coords.get("lng")
            if t_lat is None or t_lng is None:
                continue
            d = _haversine_km(float(lat), float(lng), float(t_lat), float(t_lng))
            if d <= float(radius_km):
                # attach distance to service object for later use
                setattr(s, "_px_distance_km", round(d, 2))
                filtered.append((s, t))
        rows = filtered

    # 2. Guests filter (only for capacity-bearing services)
    if guests > 1:
        rows = [
            (s, t) for (s, t) in rows
            if (s.capacity is None) or (int(s.capacity) >= guests)
        ]

    # 3. Date filter
    if check_in and check_out and check_out > check_in:
        window_days = (check_out - check_in).days
        # Fetch overlapping bookings for all relevant tenants once
        tenant_ids = list({t.id for _, t in rows})
        service_ids = list({s.id for s, _ in rows})
        if not service_ids:
            return {"total": 0, "page": page, "page_size": page_size, "items": []}

        overlapping = (
            db.query(Booking)
            .filter(
                Booking.service_id.in_(service_ids),
                Booking.status.notin_(_EXCLUDED_STATUSES),
                Booking.check_in < check_out,
            )
            .all()
        )
        overlapping = [
            b for b in overlapping
            if (b.check_out or (b.check_in + timedelta(days=1))) > check_in
        ]

        filtered: list[tuple[Service, Tenant]] = []
        for s, t in rows:
            if s.capacity is None:
                filtered.append((s, t))
                continue
            ok = True
            d = check_in
            while d < check_out:
                if _free_capacity_on_day(db, s, d, overlapping) < 1:
                    ok = False
                    break
                d += timedelta(days=1)
            if ok:
                filtered.append((s, t))
        rows = filtered

    # 4. Sort
    if sort == "price_asc":
        rows.sort(key=lambda x: float(x[0].price))
    elif sort == "price_desc":
        rows.sort(key=lambda x: -float(x[0].price))
    elif sort == "rating":
        rows.sort(key=lambda x: -(float((x[1].config or {}).get("rating") or 0)))
    else:  # popular
        # by tenant rating, then by service display_order
        rows.sort(key=lambda x: (
            -(float((x[1].config or {}).get("rating") or 0)),
            x[0].display_order,
            x[0].name,
        ))

    # 5. Paginate
    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]

    items: list[dict[str, Any]] = []
    currency_note = None
    if display_currency and currency.is_supported(display_currency):
        display_currency = display_currency.upper()
        if display_currency != currency.BASE_CURRENCY:
            currency_note = f"Converted from AED to {display_currency} at an approximate rate."

    for s, t in page_rows:
        cfg = t.config or {}
        price_value = float(s.price)
        currency_code = s.currency
        if display_currency and currency.is_supported(display_currency):
            display_currency_u = display_currency.upper()
            if display_currency_u != currency.BASE_CURRENCY:
                price_value = float(currency.convert_from_aed(price_value, display_currency_u))
                currency_code = display_currency_u
        items.append({
            "service_id": s.id,
            "service_name": s.name,
            "service_type": s.type,
            "price": price_value,
            "currency": currency_code,
            "capacity": s.capacity,
            "description": s.description,
            "tenant_id": t.id,
            "tenant_slug": t.slug,
            "tenant_name": t.name,
            "category": _tenant_category(t),
            "location": cfg.get("location"),
            "rating": cfg.get("rating"),
            "reviews_count": cfg.get("reviews_count") or 0,
            "cover_image": cfg.get("cover_image"),
            "coordinates": (cfg.get("coordinates") or None),
            "distance_km": getattr(s, "_px_distance_km", None),
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "check_in": check_in.isoformat() if check_in else None,
        "check_out": check_out.isoformat() if check_out else None,
        "guests": guests,
        "sort": sort,
        "currency_note": currency_note,
        "items": items,
    }
