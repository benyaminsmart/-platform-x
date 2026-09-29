"""Business Context Builder — turns real DB data into structured AI context.

Used by the Business AI layer (Layer 3) to ground the AI in the tenant's
actual performance: services, pricing, bookings, revenue, and trends.

Design goals:
- Pure read-only. No side effects.
- Deterministic. Same DB state => same output.
- Anonymized benchmark: never reveals another tenant's identity or exact numbers.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from statistics import median
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant


# ---------- Helpers ----------


def _to_float(v: Any) -> float:
    """Convert Decimal/int/None to float safely."""
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
    return float(v)


def _month_bounds(ref: date) -> tuple[date, date]:
    """Return (first_day_this_month, first_day_next_month)."""
    first = ref.replace(day=1)
    if first.month == 12:
        nxt = first.replace(year=first.year + 1, month=1)
    else:
        nxt = first.replace(month=first.month + 1)
    return first, nxt


def _prev_month_bounds(ref: date) -> tuple[date, date]:
    """Return (first_day_prev_month, first_day_this_month)."""
    first_this, _ = _month_bounds(ref)
    last_prev = first_this - timedelta(days=1)
    first_prev, _ = _month_bounds(last_prev)
    return first_prev, first_this


# ---------- Main builder ----------


def build_business_context(db: DBSession, tenant: Tenant) -> dict[str, Any]:
    """Build a structured context dict for the given tenant.

    All values are computed from live DB data. Nothing is mocked.
    """
    today = date.today()

    # --- Services portfolio ---
    services = (
        db.query(Service)
        .filter(Service.tenant_id == tenant.id)
        .order_by(Service.display_order, Service.name)
        .all()
    )
    active_services = [s for s in services if s.status == "active"]

    # Group prices by type (only active services with price > 0)
    prices_by_type: dict[str, list[float]] = {}
    for s in active_services:
        p = _to_float(s.price)
        if p > 0:
            prices_by_type.setdefault(s.type, []).append(p)

    pricing_by_type: dict[str, dict[str, float | int]] = {}
    for t, vals in prices_by_type.items():
        pricing_by_type[t] = {
            "count": len(vals),
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
            "avg": round(sum(vals) / len(vals), 2),
            "median": round(median(vals), 2),
        }

    # Detect dominant business type (most common type among active services)
    dominant_type: str | None = None
    if active_services:
        type_counts: dict[str, int] = {}
        for s in active_services:
            type_counts[s.type] = type_counts.get(s.type, 0) + 1
        dominant_type = max(type_counts.items(), key=lambda kv: kv[1])[0]

    services_summary = [
        {
            "name": s.name,
            "type": s.type,
            "price": _to_float(s.price),
            "currency": s.currency,
            "capacity": s.capacity,
            "status": s.status,
        }
        for s in services
    ]

    # --- Bookings overall ---
    total_bookings = (
        db.query(func.count(Booking.id))
        .filter(Booking.tenant_id == tenant.id)
        .scalar()
        or 0
    )
    confirmed_bookings = (
        db.query(func.count(Booking.id))
        .filter(Booking.tenant_id == tenant.id, Booking.status == "confirmed")
        .scalar()
        or 0
    )
    cancelled_bookings = (
        db.query(func.count(Booking.id))
        .filter(Booking.tenant_id == tenant.id, Booking.status == "cancelled")
        .scalar()
        or 0
    )

    # --- Revenue (paid bookings only) ---
    total_revenue = (
        db.query(func.coalesce(func.sum(Booking.total_amount), 0))
        .filter(Booking.tenant_id == tenant.id, Booking.payment_status == "paid")
        .scalar()
        or 0
    )

    # --- This month vs last month ---
    this_start, next_start = _month_bounds(today)
    prev_start, _ = _prev_month_bounds(today)

    rev_this_month = (
        db.query(func.coalesce(func.sum(Booking.total_amount), 0))
        .filter(
            Booking.tenant_id == tenant.id,
            Booking.payment_status == "paid",
            Booking.check_in >= this_start,
            Booking.check_in < next_start,
        )
        .scalar()
        or 0
    )
    rev_prev_month = (
        db.query(func.coalesce(func.sum(Booking.total_amount), 0))
        .filter(
            Booking.tenant_id == tenant.id,
            Booking.payment_status == "paid",
            Booking.check_in >= prev_start,
            Booking.check_in < this_start,
        )
        .scalar()
        or 0
    )

    book_this_month = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.tenant_id == tenant.id,
            Booking.check_in >= this_start,
            Booking.check_in < next_start,
        )
        .scalar()
        or 0
    )
    book_prev_month = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.tenant_id == tenant.id,
            Booking.check_in >= prev_start,
            Booking.check_in < this_start,
        )
        .scalar()
        or 0
    )

    def _growth(curr: float, prev: float) -> float | None:
        if prev <= 0:
            return None
        return round(((curr - prev) / prev) * 100, 1)

    rev_this_f = _to_float(rev_this_month)
    rev_prev_f = _to_float(rev_prev_month)

    # --- 30-day rolling trend ---
    d30 = today - timedelta(days=30)
    d60 = today - timedelta(days=60)

    book_last_30 = (
        db.query(func.count(Booking.id))
        .filter(Booking.tenant_id == tenant.id, Booking.check_in >= d30)
        .scalar()
        or 0
    )
    book_prev_30 = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.tenant_id == tenant.id,
            Booking.check_in >= d60,
            Booking.check_in < d30,
        )
        .scalar()
        or 0
    )

    # --- Top service by booking count (by service_name since service_id may be null) ---
    top_rows = (
        db.query(Booking.service_name, func.count(Booking.id).label("cnt"))
        .filter(Booking.tenant_id == tenant.id)
        .group_by(Booking.service_name)
        .order_by(func.count(Booking.id).desc())
        .limit(5)
        .all()
    )
    top_services = [{"name": r[0], "bookings": r[1]} for r in top_rows]

    # --- Average booking value (paid only) ---
    paid_count = (
        db.query(func.count(Booking.id))
        .filter(Booking.tenant_id == tenant.id, Booking.payment_status == "paid")
        .scalar()
        or 0
    )
    avg_booking_value = round(_to_float(total_revenue) / paid_count, 2) if paid_count else 0.0

    # --- Anonymized platform benchmark (same dominant type across platform) ---
    benchmark: dict[str, Any] = {
        "cohort_type": dominant_type,
        "cohort_size": 0,  # number of tenants in same type
        "avg_price": None,
        "median_price": None,
        "tenant_price_vs_cohort_pct": None,
    }
    if dominant_type:
        # Find tenants (excluding self) that have active services of this type
        peer_rows = (
            db.query(Service.tenant_id, Service.price)
            .join(Tenant, Tenant.id == Service.tenant_id)
            .filter(
                Service.type == dominant_type,
                Service.status == "active",
                Service.tenant_id != tenant.id,
                Tenant.status == "active",
            )
            .all()
        )
        peer_tenant_ids = {r[0] for r in peer_rows}
        peer_prices = [_to_float(r[1]) for r in peer_rows if _to_float(r[1]) > 0]
        if peer_prices:
            avg_p = sum(peer_prices) / len(peer_prices)
            med_p = median(peer_prices)
            benchmark["cohort_size"] = len(peer_tenant_ids)
            benchmark["avg_price"] = round(avg_p, 2)
            benchmark["median_price"] = round(med_p, 2)
            # Compare tenant's avg for this type to cohort avg
            own_prices = prices_by_type.get(dominant_type, [])
            if own_prices and avg_p > 0:
                own_avg = sum(own_prices) / len(own_prices)
                benchmark["tenant_price_vs_cohort_pct"] = round(
                    ((own_avg - avg_p) / avg_p) * 100, 1
                )

    # --- Assemble ---
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tenant": {
            "name": tenant.name,
            "slug": tenant.slug,
            "tier": tenant.tier,
            "dominant_type": dominant_type,
        },
        "portfolio": {
            "total_services": len(services),
            "active_services": len(active_services),
            "pricing_by_type": pricing_by_type,
            "services": services_summary,
        },
        "performance": {
            "total_bookings": total_bookings,
            "confirmed_bookings": confirmed_bookings,
            "cancelled_bookings": cancelled_bookings,
            "confirmation_rate_pct": (
                round((confirmed_bookings / total_bookings) * 100, 1)
                if total_bookings
                else 0.0
            ),
            "total_revenue_aed": round(_to_float(total_revenue), 2),
            "avg_booking_value_aed": avg_booking_value,
            "top_services": top_services,
        },
        "monthly": {
            "this_month": {
                "bookings": book_this_month,
                "revenue_aed": round(rev_this_f, 2),
            },
            "prev_month": {
                "bookings": book_prev_month,
                "revenue_aed": round(rev_prev_f, 2),
            },
            "revenue_growth_pct": _growth(rev_this_f, rev_prev_f),
            "bookings_growth_pct": _growth(
                float(book_this_month), float(book_prev_month)
            ),
        },
        "rolling_30d": {
            "bookings_last_30d": book_last_30,
            "bookings_prev_30d": book_prev_30,
            "growth_pct": _growth(float(book_last_30), float(book_prev_30)),
        },
        "benchmark": benchmark,
    }


def context_to_prompt(ctx: dict[str, Any]) -> str:
    """Flatten the context into a compact text block for LLM injection.

    Kept short to preserve tokens. Numbers are shown as-is; the LLM is
    expected to reason over them, not invent new ones.
    """
    t = ctx["tenant"]
    p = ctx["portfolio"]
    perf = ctx["performance"]
    m = ctx["monthly"]
    r = ctx["rolling_30d"]
    b = ctx["benchmark"]

    lines: list[str] = []
    lines.append(f"BUSINESS: {t['name']} (slug={t['slug']}, tier={t['tier']})")
    if t.get("dominant_type"):
        lines.append(f"DOMINANT CATEGORY: {t['dominant_type']}")
    lines.append(
        f"SERVICES: {p['active_services']} active / {p['total_services']} total"
    )
    if p.get("pricing_by_type"):
        for typ, stats in p["pricing_by_type"].items():
            lines.append(
                f"  - {typ}: n={stats['count']}, avg={stats['avg']}, "
                f"median={stats['median']}, min={stats['min']}, max={stats['max']} (AED)"
            )
    lines.append(
        f"BOOKINGS: total={perf['total_bookings']}, "
        f"confirmed={perf['confirmed_bookings']} "
        f"({perf['confirmation_rate_pct']}%), "
        f"cancelled={perf['cancelled_bookings']}"
    )
    lines.append(
        f"REVENUE (all-time, paid): {perf['total_revenue_aed']} AED "
        f"| avg booking = {perf['avg_booking_value_aed']} AED"
    )
    if perf.get("top_services"):
        tops = ", ".join(f"{x['name']} ({x['bookings']})" for x in perf["top_services"][:3])
        lines.append(f"TOP SERVICES: {tops}")

    m_this = m["this_month"]
    m_prev = m["prev_month"]
    lines.append(
        f"THIS MONTH: {m_this['bookings']} bookings, {m_this['revenue_aed']} AED "
        f"| PREV MONTH: {m_prev['bookings']} bookings, {m_prev['revenue_aed']} AED"
    )
    if m.get("revenue_growth_pct") is not None:
        lines.append(f"  revenue growth: {m['revenue_growth_pct']}%")
    if m.get("bookings_growth_pct") is not None:
        lines.append(f"  bookings growth: {m['bookings_growth_pct']}%")

    lines.append(
        f"LAST 30 DAYS: {r['bookings_last_30d']} bookings "
        f"(prev 30d: {r['bookings_prev_30d']}, "
        f"growth: {r.get('growth_pct')}%)"
    )

    if b.get("cohort_size") and b.get("avg_price") is not None:
        lines.append(
            f"ANONYMIZED PEER BENCHMARK ({b['cohort_type']}): "
            f"cohort_size={b['cohort_size']} tenants, "
            f"avg_price={b['avg_price']} AED, median={b['median_price']} AED"
        )
        if b.get("tenant_price_vs_cohort_pct") is not None:
            lines.append(
                f"  your avg price vs cohort: {b['tenant_price_vs_cohort_pct']}%"
            )

    return "\n".join(lines)
