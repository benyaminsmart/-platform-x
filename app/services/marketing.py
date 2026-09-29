"""Marketing service — customer segmentation for campaigns.

Design:
- Read-only. No emails sent here.
- Segments are computed from real booking + user data.
- Cross-tenant isolation: only bookings of the given tenant are considered.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User


SEGMENTS = {
    "all",
    "past_bookers",
    "inactive_90d",
    "high_value",
    "new_30d",
    "loyalty_gold_plus",
}


# ---------- Helpers ----------


def _user_rows(db: DBSession, tenant: Tenant) -> list[dict[str, Any]]:
    """Return aggregated per-user stats for the tenant.

    Each row:
      user_id, email, first_name, last_name, tier, language,
      bookings_count, total_paid, last_check_in, first_check_in
    """
    # Bookings grouped by user
    rows = (
        db.query(
            Booking.user_id,
            func.count(Booking.id).label("bookings_count"),
            func.coalesce(func.sum(Booking.total_amount), 0).label("total_amount"),
            func.max(Booking.check_in).label("last_check_in"),
            func.min(Booking.check_in).label("first_check_in"),
        )
        .filter(Booking.tenant_id == tenant.id)
        .group_by(Booking.user_id)
        .all()
    )
    if not rows:
        return []

    user_ids = [r[0] for r in rows]
    users = {
        u.id: u
        for u in db.query(User).filter(User.id.in_(user_ids)).all()
    }

    out: list[dict[str, Any]] = []
    for r in rows:
        u = users.get(r[0])
        if u is None or u.status != "active":
            continue
        out.append({
            "user_id": u.id,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "tier": u.tier,
            "language": u.language,
            "points": u.points,
            "bookings_count": int(r[1] or 0),
            "total_paid": float(r[2] or 0),
            "last_check_in": r[3],
            "first_check_in": r[4],
        })
    return out


def _percentile(values: list[float], pct: float) -> float:
    """Return the pct-th percentile (0..1). Empty -> 0."""
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round((len(s) - 1) * pct))))
    return s[k]


# ---------- Main segmentation ----------


def segment_customers(
    db: DBSession,
    tenant: Tenant,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Return a summary of all segments for the tenant."""
    today = today or date.today()
    rows = _user_rows(db, tenant)

    if not rows:
        return {
            "segments": {s: {"count": 0, "sample_emails": []} for s in sorted(SEGMENTS)},
            "totals": {"customers": 0, "all_time_revenue": 0.0},
        }

    total_paid_values = [r["total_paid"] for r in rows]
    top20_threshold = _percentile(total_paid_values, 0.8)

    cutoff_90d = today - timedelta(days=90)
    cutoff_30d = today - timedelta(days=30)

    buckets: dict[str, list[dict[str, Any]]] = {s: [] for s in SEGMENTS}

    for r in rows:
        buckets["all"].append(r)
        if r["bookings_count"] > 0:
            buckets["past_bookers"].append(r)
        last = r["last_check_in"]
        if last is not None and last < cutoff_90d:
            buckets["inactive_90d"].append(r)
        if r["total_paid"] >= top20_threshold and r["total_paid"] > 0:
            buckets["high_value"].append(r)
        first = r["first_check_in"]
        if first is not None and first >= cutoff_30d:
            buckets["new_30d"].append(r)
        if r["tier"] in ("gold", "platinum", "royal"):
            buckets["loyalty_gold_plus"].append(r)

    segments: dict[str, Any] = {}
    for name, items in buckets.items():
        segments[name] = {
            "count": len(items),
            "sample_emails": [i["email"] for i in items[:5]],
            "top20_threshold_aed": round(top20_threshold, 2) if name == "high_value" else None,
        }

    all_revenue = sum(r["total_paid"] for r in rows)
    return {
        "segments": segments,
        "totals": {
            "customers": len(rows),
            "all_time_revenue": round(all_revenue, 2),
        },
    }


def get_segment_customers(
    db: DBSession,
    tenant: Tenant,
    segment: str,
    *,
    today: date | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Return full list of users in a segment (up to limit)."""
    if segment not in SEGMENTS:
        raise ValueError(f"unknown segment: {segment}")

    today = today or date.today()
    rows = _user_rows(db, tenant)

    if not rows:
        return []

    if segment == "all":
        selected = rows
    elif segment == "past_bookers":
        selected = [r for r in rows if r["bookings_count"] > 0]
    elif segment == "inactive_90d":
        cutoff_90d = today - timedelta(days=90)
        selected = [r for r in rows if r["last_check_in"] and r["last_check_in"] < cutoff_90d]
    elif segment == "high_value":
        vals = [r["total_paid"] for r in rows]
        thr = _percentile(vals, 0.8)
        selected = [r for r in rows if r["total_paid"] >= thr and r["total_paid"] > 0]
    elif segment == "new_30d":
        cutoff_30d = today - timedelta(days=30)
        selected = [r for r in rows if r["first_check_in"] and r["first_check_in"] >= cutoff_30d]
    elif segment == "loyalty_gold_plus":
        selected = [r for r in rows if r["tier"] in ("gold", "platinum", "royal")]
    else:
        selected = []

    return selected[:limit]


def estimate_audience_size(
    db: DBSession,
    tenant: Tenant,
    segment: str,
    *,
    today: date | None = None,
) -> int:
    """Return just the count for a segment (fast path)."""
    if segment not in SEGMENTS:
        raise ValueError(f"unknown segment: {segment}")
    summary = segment_customers(db, tenant, today=today)
    return int(summary["segments"][segment]["count"])
