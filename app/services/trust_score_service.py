"""Trust Score service — deterministic composite trust score per tenant.

Phase 49 (Wave 3, Blue-Ocean B11 — Trust Score per Business).

Composite 0..100 score from four components:
  - Rating         40%   (avg review rating, normalized 0..100)
  - Volume         20%   (30-day paid bookings, log-scaled)
  - Verification   20%   (verified / total published reviews)
  - Responsiveness 20%   (responded / total published reviews)

No AI. No new table. All data is derived from existing rows:
tenants, services, bookings, reviews.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.review import Review
from app.models.tenant import Tenant


# Weights (fixed platform policy)
W_RATING = 0.40
W_VOLUME = 0.20
W_VERIFICATION = 0.20
W_RESPONSIVENESS = 0.20

# Volume saturation: ~30 bookings/month → ~100
VOLUME_SATURATION = 30.0

_PAID_STATUSES = {"confirmed", "paid"}
_PUBLISHED = "published"


def _clip01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _rating_component(db: DBSession, tenant_id: str) -> tuple[float, dict[str, Any]]:
    row = (
        db.query(func.avg(Review.rating), func.count(Review.id))
        .filter(Review.tenant_id == tenant_id, Review.status == _PUBLISHED)
        .one()
    )
    avg = float(row[0]) if row and row[0] is not None else None
    count = int(row[1]) if row and row[1] is not None else 0
    if avg is None or count == 0:
        # Neutral baseline if no reviews yet
        return 50.0, {"avg_rating": None, "reviews_count": 0}
    # 1..5 → 0..100
    normalized = ((avg - 1.0) / 4.0) * 100.0
    return _clip01(normalized / 100.0) * 100.0, {
        "avg_rating": round(avg, 2),
        "reviews_count": count,
    }


def _volume_component(db: DBSession, tenant_id: str) -> tuple[float, dict[str, Any]]:
    since = datetime.now(timezone.utc) - timedelta(days=30)
    count = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.tenant_id == tenant_id,
            Booking.status.in_(list(_PAID_STATUSES)),
            Booking.created_at >= since,
        )
        .scalar()
    ) or 0
    # log-scaled saturation
    denom = math.log1p(VOLUME_SATURATION)
    norm = math.log1p(float(count)) / denom if denom > 0 else 0.0
    return _clip01(norm) * 100.0, {"bookings_30d": int(count)}


def _verification_component(db: DBSession, tenant_id: str) -> tuple[float, dict[str, Any]]:
    total = (
        db.query(func.count(Review.id))
        .filter(Review.tenant_id == tenant_id, Review.status == _PUBLISHED)
        .scalar()
    ) or 0
    if total == 0:
        return 50.0, {"verified": 0, "total": 0}
    verified = (
        db.query(func.count(Review.id))
        .filter(
            Review.tenant_id == tenant_id,
            Review.status == _PUBLISHED,
            Review.verified == True,  # noqa: E712
        )
        .scalar()
    ) or 0
    return _clip01(verified / total) * 100.0, {"verified": int(verified), "total": int(total)}


def _responsiveness_component(db: DBSession, tenant_id: str) -> tuple[float, dict[str, Any]]:
    total = (
        db.query(func.count(Review.id))
        .filter(Review.tenant_id == tenant_id, Review.status == _PUBLISHED)
        .scalar()
    ) or 0
    if total == 0:
        return 50.0, {"responded": 0, "total": 0}
    responded = (
        db.query(func.count(Review.id))
        .filter(
            Review.tenant_id == tenant_id,
            Review.status == _PUBLISHED,
            Review.response_text.isnot(None),
        )
        .scalar()
    ) or 0
    return _clip01(responded / total) * 100.0, {"responded": int(responded), "total": int(total)}


def compute(db: DBSession, *, tenant_id: str) -> dict[str, Any]:
    """Compute the trust score for one tenant."""
    rating, r_meta = _rating_component(db, tenant_id)
    volume, v_meta = _volume_component(db, tenant_id)
    verification, ve_meta = _verification_component(db, tenant_id)
    responsiveness, re_meta = _responsiveness_component(db, tenant_id)

    overall = (
        rating * W_RATING
        + volume * W_VOLUME
        + verification * W_VERIFICATION
        + responsiveness * W_RESPONSIVENESS
    )
    overall = max(0.0, min(100.0, overall))

    return {
        "tenant_id": tenant_id,
        "score": round(overall, 1),
        "components": {
            "rating": round(rating, 1),
            "volume": round(volume, 1),
            "verification": round(verification, 1),
            "responsiveness": round(responsiveness, 1),
        },
        "meta": {
            "rating": r_meta,
            "volume": v_meta,
            "verification": ve_meta,
            "responsiveness": re_meta,
        },
        "weights": {
            "rating": W_RATING,
            "volume": W_VOLUME,
            "verification": W_VERIFICATION,
            "responsiveness": W_RESPONSIVENESS,
        },
    }


def get_by_slug(db: DBSession, *, slug: str) -> dict[str, Any] | None:
    t = db.query(Tenant).filter(Tenant.slug == slug).one_or_none()
    if t is None:
        return None
    out = compute(db, tenant_id=t.id)
    out["tenant_slug"] = t.slug
    out["tenant_name"] = t.name
    return out


def compute_many(db: DBSession, *, tenant_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Compute trust scores for multiple tenants in one call."""
    return {tid: compute(db, tenant_id=tid) for tid in tenant_ids}


def tier_label(score: float) -> str:
    """Human-readable tier for a trust score."""
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "very_good"
    if score >= 55:
        return "good"
    if score >= 40:
        return "fair"
    return "new"
