"""Leaderboard service — recompute, rank, and query business scores.

All operations are deterministic and DB-backed. No AI here.
Rewards logic maps rank -> badges + platform benefits (as documented
in Phase 29 roadmap).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session as DBSession

from app.models.business_score import BusinessScore
from app.models.tenant import Tenant
from app.services import scoring_engine


# ---------- Reward mapping ----------


REWARDS_BY_RANK: dict[int, dict[str, Any]] = {
    1: {
        "badge": "gold",
        "label": "Gold",
        "hero_featured": True,
        "sponsored_promotion": True,
        "commission_discount_pct": 100,  # 0% commission next month
        "search_boost": "top",
    },
    2: {
        "badge": "silver",
        "label": "Silver",
        "category_featured": True,
        "commission_discount_pct": 50,
        "search_boost": "high",
    },
    3: {
        "badge": "bronze",
        "label": "Bronze",
        "search_boost": "medium",
    },
}


def rewards_for_rank(rank: int | None) -> dict[str, Any] | None:
    """Return the reward bundle for a rank, or None if outside top 3."""
    if rank is None:
        return None
    return REWARDS_BY_RANK.get(rank)


# ---------- Recompute ----------


def recompute_scores(
    db: DBSession,
    *,
    period_start: date,
    period_end: date,
) -> dict[str, Any]:
    """Compute and persist scores for all active tenants in a period.

    Upserts BusinessScore rows, then assigns ranks.
    Returns summary: counts + period info.
    """
    tenants = (
        db.query(Tenant)
        .filter(Tenant.status == "active", Tenant.deleted_at.is_(None))
        .all()
    )

    created = 0
    updated = 0
    now = datetime.now(timezone.utc)

    for t in tenants:
        result = scoring_engine.compute_score(db, t)

        existing = (
            db.query(BusinessScore)
            .filter(
                BusinessScore.tenant_id == t.id,
                BusinessScore.period_start == period_start,
                BusinessScore.period_end == period_end,
            )
            .one_or_none()
        )

        if existing is None:
            row = BusinessScore(
                tenant_id=t.id,
                category=result["category"],
                period_start=period_start,
                period_end=period_end,
                overall_score=result["overall_score"],
                customer_satisfaction=result["customer_satisfaction"],
                service_quality=result["service_quality"],
                pricing_competitiveness=result["pricing_competitiveness"],
                engagement=result["engagement"],
                loyalty=result["loyalty"],
                criteria_breakdown=result["criteria_breakdown"],
                computed_at=now,
            )
            db.add(row)
            created += 1
        else:
            existing.category = result["category"]
            existing.overall_score = result["overall_score"]
            existing.customer_satisfaction = result["customer_satisfaction"]
            existing.service_quality = result["service_quality"]
            existing.pricing_competitiveness = result["pricing_competitiveness"]
            existing.engagement = result["engagement"]
            existing.loyalty = result["loyalty"]
            existing.criteria_breakdown = result["criteria_breakdown"]
            existing.computed_at = now
            updated += 1

    db.commit()

    ranks = compute_and_assign_ranks(
        db, period_start=period_start, period_end=period_end
    )

    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "tenants_total": len(tenants),
        "created": created,
        "updated": updated,
        "ranks_assigned": ranks,
    }


# ---------- Ranks ----------


def _rank_sort_key(row: BusinessScore) -> tuple:
    """Tie-breakers: overall desc, then engagement desc, then created_at asc."""
    return (
        -float(row.overall_score or 0),
        -float(row.engagement or 0),
        row.created_at.timestamp() if row.created_at else 0,
    )


def compute_and_assign_ranks(
    db: DBSession,
    *,
    period_start: date,
    period_end: date,
) -> int:
    """Assign rank_overall and rank_in_category. Returns count of ranked rows."""
    rows = (
        db.query(BusinessScore)
        .filter(
            BusinessScore.period_start == period_start,
            BusinessScore.period_end == period_end,
        )
        .all()
    )

    if not rows:
        return 0

    # Overall ranking
    overall_sorted = sorted(rows, key=_rank_sort_key)
    for i, r in enumerate(overall_sorted, start=1):
        r.rank_overall = i

    # Per-category ranking
    by_cat: dict[str, list[BusinessScore]] = {}
    for r in rows:
        by_cat.setdefault(r.category, []).append(r)
    for cat, cat_rows in by_cat.items():
        cat_sorted = sorted(cat_rows, key=_rank_sort_key)
        for i, r in enumerate(cat_sorted, start=1):
            r.rank_in_category = i

    db.commit()
    return len(rows)


# ---------- Queries ----------


def get_leaderboard(
    db: DBSession,
    *,
    category: str | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return the leaderboard for a period, optionally filtered by category."""
    if period_start is None or period_end is None:
        ps, pe = scoring_engine.current_period()
        period_start = period_start or ps
        period_end = period_end or pe

    q = db.query(BusinessScore, Tenant).join(
        Tenant, Tenant.id == BusinessScore.tenant_id
    ).filter(
        BusinessScore.period_start == period_start,
        BusinessScore.period_end == period_end,
    )
    if category:
        q = q.filter(BusinessScore.category == category)

    # Order: rank_in_category asc when category given, otherwise rank_overall
    order_col = BusinessScore.rank_in_category if category else BusinessScore.rank_overall
    q = q.order_by(asc(order_col), desc(BusinessScore.overall_score))

    rows = q.limit(limit).all()

    out: list[dict[str, Any]] = []
    for score, tenant in rows:
        rank = score.rank_in_category if category else score.rank_overall
        out.append(
            {
                "rank": rank,
                "rank_overall": score.rank_overall,
                "rank_in_category": score.rank_in_category,
                "tenant_id": tenant.id,
                "tenant_slug": tenant.slug,
                "tenant_name": tenant.name,
                "category": score.category,
                "overall_score": round(float(score.overall_score), 2),
                "customer_satisfaction": round(float(score.customer_satisfaction), 2),
                "service_quality": round(float(score.service_quality), 2),
                "pricing_competitiveness": round(float(score.pricing_competitiveness), 2),
                "engagement": round(float(score.engagement), 2),
                "loyalty": round(float(score.loyalty), 2),
                "rewards": rewards_for_rank(rank),
                "location": (tenant.config or {}).get("location"),
                "rating": (tenant.config or {}).get("rating"),
                "cover_image": (tenant.config or {}).get("cover_image"),
            }
        )
    return out


def get_tenant_score(
    db: DBSession,
    *,
    tenant_id: str,
    period_start: date | None = None,
    period_end: date | None = None,
) -> BusinessScore | None:
    """Return the stored BusinessScore row for a tenant in a period."""
    if period_start is None or period_end is None:
        ps, pe = scoring_engine.current_period()
        period_start = period_start or ps
        period_end = period_end or pe

    return (
        db.query(BusinessScore)
        .filter(
            BusinessScore.tenant_id == tenant_id,
            BusinessScore.period_start == period_start,
            BusinessScore.period_end == period_end,
        )
        .one_or_none()
    )


def get_tenant_score_dict(db: DBSession, *, tenant_id: str) -> dict[str, Any] | None:
    """Return the current-period tenant score as a dict (or None)."""
    row = get_tenant_score(db, tenant_id=tenant_id)
    if row is None:
        return None
    return {
        "tenant_id": row.tenant_id,
        "category": row.category,
        "period_start": row.period_start.isoformat(),
        "period_end": row.period_end.isoformat(),
        "overall_score": round(float(row.overall_score), 2),
        "customer_satisfaction": round(float(row.customer_satisfaction), 2),
        "service_quality": round(float(row.service_quality), 2),
        "pricing_competitiveness": round(float(row.pricing_competitiveness), 2),
        "engagement": round(float(row.engagement), 2),
        "loyalty": round(float(row.loyalty), 2),
        "rank_overall": row.rank_overall,
        "rank_in_category": row.rank_in_category,
        "rewards": rewards_for_rank(row.rank_in_category or row.rank_overall),
        "criteria_breakdown": row.criteria_breakdown,
        "computed_at": row.computed_at.isoformat() if row.computed_at else None,
    }
