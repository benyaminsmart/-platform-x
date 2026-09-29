"""Scoring Engine — deterministic monthly score per tenant.

Computes 5 criteria (each 0-100) from real DB data, then a weighted overall.

Weights (platform policy, fixed):
  Customer Satisfaction   30%
  Service Quality         25%
  Pricing Competitiveness 20%
  Engagement              15%
  Loyalty                 10%

Design:
- Pure functions; no DB writes here.
- All numbers come from real data via SQLAlchemy queries.
- If data is missing, use a fair baseline (never zero just because of gaps).
- Every criterion returns (score, breakdown dict) for transparency.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.ai_chat import AIChatMessage
from app.models.booking import Booking
from app.models.service import Service
from app.models.subscription import Subscription
from app.models.tenant import Tenant
from app.services.ai.business_context import build_business_context


WEIGHTS = {
    "customer_satisfaction": 0.30,
    "service_quality": 0.25,
    "pricing_competitiveness": 0.20,
    "engagement": 0.15,
    "loyalty": 0.10,
}

# Catalog of tenant categories (derived from tenant.config.type)
CATEGORY_FROM_TYPE = {
    "hotel": "hotels",
    "restaurant": "restaurants",
    "travel_agency": "travel",
    "entertainment": "entertainment",
}


# ---------- Helpers ----------


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _round2(v: float) -> float:
    return round(float(v), 2)


def _tenant_category(tenant: Tenant) -> str:
    """Map tenant.config.type to a leaderboard category."""
    t = (tenant.config or {}).get("type") or ""
    return CATEGORY_FROM_TYPE.get(t, "other")


# ---------- Criterion 1: Customer Satisfaction (30%) ----------


def compute_customer_satisfaction(
    tenant: Tenant,
) -> tuple[float, dict[str, Any]]:
    """Base on rating + confidence from review count.

    rating 5.0 with 500+ reviews -> ~100
    rating 4.8 with 340 reviews  -> ~90
    no rating -> 50 (neutral baseline)
    """
    cfg = tenant.config or {}
    rating = cfg.get("rating")
    reviews = cfg.get("reviews_count") or 0

    if rating is None:
        return 50.0, {"note": "no rating configured", "baseline": 50.0}

    rating = float(rating)
    reviews = int(reviews)

    base = rating * 20.0  # 5.0 -> 100
    confidence = 1.0 if reviews <= 0 else min(1.0, math.log10(max(reviews, 1) + 1) / math.log10(501))
    # reviews=500 -> confidence ~0.99, reviews=100 -> ~0.74, reviews=10 -> ~0.40

    score = _clamp(base * confidence)
    return _round2(score), {
        "rating": rating,
        "reviews_count": reviews,
        "base_score": _round2(base),
        "confidence": _round2(confidence),
    }


# ---------- Criterion 2: Service Quality (25%) ----------


def compute_service_quality(db: DBSession, tenant: Tenant) -> tuple[float, dict[str, Any]]:
    """Activity (30) + diversity (30) + profile completeness (40)."""
    total = (
        db.query(func.count(Service.id))
        .filter(Service.tenant_id == tenant.id)
        .scalar()
        or 0
    )
    active = (
        db.query(func.count(Service.id))
        .filter(Service.tenant_id == tenant.id, Service.status == "active")
        .scalar()
        or 0
    )

    # activity: 0..30 based on active ratio, minimum 5 if at least 1 active
    if active == 0:
        activity = 0.0
    elif total == 0:
        activity = 0.0
    else:
        activity = 30.0 * (active / total)
        if activity < 5.0:
            activity = 5.0

    # diversity: number of distinct service types, capped at 6 -> 5 pts each
    distinct_types = (
        db.query(func.count(func.distinct(Service.type)))
        .filter(Service.tenant_id == tenant.id, Service.status == "active")
        .scalar()
        or 0
    )
    diversity = min(distinct_types, 6) * 5.0

    # profile completeness: 6 fields -> ~6.67 each
    cfg = tenant.config or {}
    fields = [
        bool(cfg.get("type")),
        bool(cfg.get("tagline")),
        bool(cfg.get("location")),
        bool(cfg.get("cover_image")),
        bool(cfg.get("gallery")),
        bool(cfg.get("amenities") or cfg.get("services_list")),
    ]
    profile = (sum(fields) / len(fields)) * 40.0

    score = _clamp(activity + diversity + profile)
    return _round2(score), {
        "total_services": total,
        "active_services": active,
        "distinct_types": distinct_types,
        "activity_points": _round2(activity),
        "diversity_points": _round2(diversity),
        "profile_points": _round2(profile),
        "profile_fields_present": sum(fields),
    }


# ---------- Criterion 3: Pricing Competitiveness (20%) ----------


def compute_pricing_competitiveness(
    db: DBSession, tenant: Tenant
) -> tuple[float, dict[str, Any]]:
    """Based on position vs anonymized peer cohort (from Context Builder).

    delta = 0% -> 100
    |delta| >= 40% -> 0
    Otherwise: 100 - |delta| * 2.5

    If no cohort data: baseline 60.
    """
    ctx = build_business_context(db, tenant)
    bench = ctx.get("benchmark") or {}
    delta = bench.get("tenant_price_vs_cohort_pct")

    if delta is None or not bench.get("cohort_size"):
        return 60.0, {"note": "insufficient cohort data", "baseline": 60.0}

    delta = abs(float(delta))
    score = _clamp(100.0 - delta * 2.5)
    return _round2(score), {
        "cohort_size": bench.get("cohort_size"),
        "tenant_price_vs_cohort_pct": delta,
        "cohort_type": bench.get("cohort_type"),
    }


# ---------- Criterion 4: Engagement (15%) ----------


def compute_engagement(
    db: DBSession, tenant: Tenant, *, today: date | None = None
) -> tuple[float, dict[str, Any]]:
    """Bookings (last 30d) relative to platform median + AI usage.

    Bookings: 0..80
      If tenant bookings >= platform median (of active tenants with bookings):
        80 (or scaled 80..100 if well above)
      If below: ratio * 80
    AI messages (last 30d): 0..20 (1 point per message, capped at 20)
    """
    today = today or date.today()
    d30 = today - timedelta(days=30)
    d30_dt = datetime.combine(d30, datetime.min.time(), tzinfo=timezone.utc)

    my_bookings_30 = (
        db.query(func.count(Booking.id))
        .filter(Booking.tenant_id == tenant.id, Booking.check_in >= d30)
        .scalar()
        or 0
    )

    # platform median across active tenants (only counting tenants with >=1 booking)
    peer_rows = (
        db.query(Booking.tenant_id, func.count(Booking.id).label("c"))
        .filter(Booking.check_in >= d30)
        .group_by(Booking.tenant_id)
        .all()
    )
    peer_counts = sorted([r[1] for r in peer_rows]) or [0]
    n = len(peer_counts)
    median = peer_counts[n // 2] if n % 2 == 1 else (peer_counts[n // 2 - 1] + peer_counts[n // 2]) / 2.0

    if median <= 0:
        booking_score = 40.0 if my_bookings_30 == 0 else 80.0
    elif my_bookings_30 >= median:
        # scale 80..100 for well above
        excess = (my_bookings_30 - median) / max(median, 1)
        booking_score = _clamp(80.0 + min(excess, 1.0) * 20.0)
    else:
        booking_score = _clamp((my_bookings_30 / median) * 80.0)

    # AI usage (messages by business users of this tenant in last 30 days)
    ai_msgs = (
        db.query(func.count(AIChatMessage.id))
        .filter(
            AIChatMessage.tenant_id == tenant.id,
            AIChatMessage.created_at >= d30_dt,
        )
        .scalar()
        or 0
    )
    ai_score = min(ai_msgs, 20)

    score = _clamp(booking_score + ai_score)
    return _round2(score), {
        "bookings_last_30d": my_bookings_30,
        "platform_median_last_30d": _round2(median),
        "booking_points": _round2(booking_score),
        "ai_messages_last_30d": ai_msgs,
        "ai_points": _round2(ai_score),
    }


# ---------- Criterion 5: Loyalty (10%) ----------


def compute_loyalty(db: DBSession, tenant: Tenant, *, today: date | None = None) -> tuple[float, dict[str, Any]]:
    """Tenure (0-72) + active subscription (0-20) + paid bookings (0-8)."""
    today = today or date.today()
    created = tenant.created_at.date() if tenant.created_at else today
    days = max((today - created).days, 0)
    months = days / 30.0

    age_points = min(months, 24.0) * 3.0  # 0..72

    sub = (
        db.query(Subscription)
        .filter(Subscription.tenant_id == tenant.id, Subscription.status == "active")
        .first()
    )
    sub_points = 20.0 if sub else 0.0

    paid_count = (
        db.query(func.count(Booking.id))
        .filter(Booking.tenant_id == tenant.id, Booking.payment_status == "paid")
        .scalar()
        or 0
    )
    paid_points = min(paid_count, 8) * 1.0  # 0..8

    score = _clamp(age_points + sub_points + paid_points)
    return _round2(score), {
        "days_since_created": days,
        "months_since_created": _round2(months),
        "age_points": _round2(age_points),
        "has_active_subscription": bool(sub),
        "subscription_points": sub_points,
        "paid_bookings": paid_count,
        "paid_points": _round2(paid_points),
    }


# ---------- Overall ----------


def compute_score(db: DBSession, tenant: Tenant, *, today: date | None = None) -> dict[str, Any]:
    """Compute the full score for one tenant. No DB writes."""
    today = today or date.today()

    cs, cs_bd = compute_customer_satisfaction(tenant)
    sq, sq_bd = compute_service_quality(db, tenant)
    pc, pc_bd = compute_pricing_competitiveness(db, tenant)
    en, en_bd = compute_engagement(db, tenant, today=today)
    lo, lo_bd = compute_loyalty(db, tenant, today=today)

    overall = _clamp(
        cs * WEIGHTS["customer_satisfaction"]
        + sq * WEIGHTS["service_quality"]
        + pc * WEIGHTS["pricing_competitiveness"]
        + en * WEIGHTS["engagement"]
        + lo * WEIGHTS["loyalty"]
    )

    return {
        "tenant_id": tenant.id,
        "category": _tenant_category(tenant),
        "overall_score": _round2(overall),
        "customer_satisfaction": cs,
        "service_quality": sq,
        "pricing_competitiveness": pc,
        "engagement": en,
        "loyalty": lo,
        "criteria_breakdown": {
            "customer_satisfaction": cs_bd,
            "service_quality": sq_bd,
            "pricing_competitiveness": pc_bd,
            "engagement": en_bd,
            "loyalty": lo_bd,
            "weights": WEIGHTS,
        },
    }


# ---------- Period helpers ----------


def current_period(today: date | None = None) -> tuple[date, date]:
    """Return (period_start, period_end) for the current month.

    period_start = first day of month
    period_end   = first day of next month (exclusive end convention)
    """
    today = today or date.today()
    start = today.replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def previous_period(today: date | None = None) -> tuple[date, date]:
    """Return the previous month's (period_start, period_end)."""
    this_start, _ = current_period(today)
    prev_end = this_start
    prev_start = (this_start - timedelta(days=1)).replace(day=1)
    return prev_start, prev_end
