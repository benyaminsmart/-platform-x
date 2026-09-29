"""Tests for the Leaderboard service (Phase 29, Step 3)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.business_score import BusinessScore
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import leaderboard, scoring_engine


# ---------- Helpers ----------


def _tenant(db: Session, slug: str, cfg: dict, *, status: str = "active") -> Tenant:
    t = Tenant(slug=slug, name=slug, tier="starter", status=status, config=cfg)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _svc(db: Session, tenant: Tenant, *, name: str = "R", price: float = 500) -> Service:
    s = Service(
        tenant_id=tenant.id, type="room", name=name,
        price=Decimal(str(price)), currency="AED", capacity=2,
        attributes={}, image_urls=[], status="active", display_order=0,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# ---------- Rewards mapping ----------


def test_rewards_for_rank_mapping() -> None:
    r1 = leaderboard.rewards_for_rank(1)
    assert r1["badge"] == "gold"
    assert r1["commission_discount_pct"] == 100
    assert r1["hero_featured"] is True

    r2 = leaderboard.rewards_for_rank(2)
    assert r2["badge"] == "silver"
    assert r2["commission_discount_pct"] == 50

    r3 = leaderboard.rewards_for_rank(3)
    assert r3["badge"] == "bronze"

    assert leaderboard.rewards_for_rank(4) is None
    assert leaderboard.rewards_for_rank(None) is None


# ---------- Recompute ----------


def test_recompute_empty_db(db: Session) -> None:
    ps, pe = date(2026, 9, 1), date(2026, 10, 1)
    out = leaderboard.recompute_scores(db, period_start=ps, period_end=pe)
    assert out["tenants_total"] == 0
    assert out["created"] == 0
    assert out["updated"] == 0
    assert out["ranks_assigned"] == 0


def test_recompute_creates_scores_for_all_active_tenants(db: Session) -> None:
    _tenant(db, "a", {"type": "hotel", "rating": 4.8, "reviews_count": 200})
    _tenant(db, "b", {"type": "hotel", "rating": 4.5, "reviews_count": 100})
    _tenant(db, "inactive", {"type": "hotel"}, status="suspended")

    ps, pe = date(2026, 9, 1), date(2026, 10, 1)
    out = leaderboard.recompute_scores(db, period_start=ps, period_end=pe)
    assert out["tenants_total"] == 2
    assert out["created"] == 2
    assert out["ranks_assigned"] == 2

    rows = db.query(BusinessScore).all()
    assert len(rows) == 2


def test_recompute_idempotent(db: Session) -> None:
    _tenant(db, "a", {"type": "hotel", "rating": 4.8, "reviews_count": 200})
    ps, pe = date(2026, 9, 1), date(2026, 10, 1)

    out1 = leaderboard.recompute_scores(db, period_start=ps, period_end=pe)
    assert out1["created"] == 1
    assert out1["updated"] == 0

    out2 = leaderboard.recompute_scores(db, period_start=ps, period_end=pe)
    assert out2["created"] == 0
    assert out2["updated"] == 1
    assert db.query(BusinessScore).count() == 1


# ---------- Ranks ----------


def test_ranks_ordered_by_overall_desc(db: Session) -> None:
    # Build 3 tenants with different scores via ratings
    _tenant(db, "high", {"type": "hotel", "rating": 5.0, "reviews_count": 1000})
    _tenant(db, "mid", {"type": "hotel", "rating": 4.0, "reviews_count": 500})
    _tenant(db, "low", {"type": "hotel", "rating": 2.0, "reviews_count": 100})

    ps, pe = date(2026, 9, 1), date(2026, 10, 1)
    leaderboard.recompute_scores(db, period_start=ps, period_end=pe)

    rows = (
        db.query(BusinessScore)
        .filter(BusinessScore.period_start == ps, BusinessScore.period_end == pe)
        .all()
    )
    by_rank = {r.rank_overall: r for r in rows}

    assert by_rank[1].tenant_id
    # Highest overall is rank 1
    assert by_rank[1].overall_score >= by_rank[2].overall_score >= by_rank[3].overall_score


def test_ranks_in_category_are_independent(db: Session) -> None:
    _tenant(db, "h1", {"type": "hotel", "rating": 5.0, "reviews_count": 500})
    _tenant(db, "h2", {"type": "hotel", "rating": 3.0, "reviews_count": 500})
    _tenant(db, "r1", {"type": "restaurant", "rating": 4.5, "reviews_count": 500})
    _tenant(db, "r2", {"type": "restaurant", "rating": 4.0, "reviews_count": 500})

    ps, pe = date(2026, 9, 1), date(2026, 10, 1)
    leaderboard.recompute_scores(db, period_start=ps, period_end=pe)

    rows = (
        db.query(BusinessScore)
        .filter(BusinessScore.period_start == ps, BusinessScore.period_end == pe)
        .all()
    )
    hotels = sorted([r for r in rows if r.category == "hotels"], key=lambda r: r.rank_in_category)
    restaurants = sorted([r for r in rows if r.category == "restaurants"], key=lambda r: r.rank_in_category)

    assert [r.rank_in_category for r in hotels] == [1, 2]
    assert [r.rank_in_category for r in restaurants] == [1, 2]
    # Overall ranks are unique
    overall = sorted([r.rank_overall for r in rows])
    assert overall == [1, 2, 3, 4]


# ---------- Leaderboard queries ----------


def test_get_leaderboard_all_categories(db: Session) -> None:
    _tenant(db, "h1", {"type": "hotel", "rating": 5.0, "reviews_count": 500})
    _tenant(db, "r1", {"type": "restaurant", "rating": 4.5, "reviews_count": 500})

    ps, pe = date(2026, 9, 1), date(2026, 10, 1)
    leaderboard.recompute_scores(db, period_start=ps, period_end=pe)

    rows = leaderboard.get_leaderboard(db, period_start=ps, period_end=pe)
    assert len(rows) == 2
    # Order by overall desc (rank_overall asc)
    assert rows[0]["rank_overall"] == 1
    assert rows[1]["rank_overall"] == 2
    # Includes rewards for rank 1
    assert rows[0]["rewards"]["badge"] in ("gold", "silver")


def test_get_leaderboard_by_category(db: Session) -> None:
    _tenant(db, "h1", {"type": "hotel", "rating": 5.0, "reviews_count": 500})
    _tenant(db, "h2", {"type": "hotel", "rating": 3.0, "reviews_count": 500})
    _tenant(db, "r1", {"type": "restaurant", "rating": 4.5, "reviews_count": 500})

    ps, pe = date(2026, 9, 1), date(2026, 10, 1)
    leaderboard.recompute_scores(db, period_start=ps, period_end=pe)

    rows = leaderboard.get_leaderboard(db, category="hotels", period_start=ps, period_end=pe)
    assert len(rows) == 2
    for r in rows:
        assert r["category"] == "hotels"
    # Rank is rank_in_category
    assert rows[0]["rank"] == 1
    assert rows[1]["rank"] == 2


def test_get_leaderboard_empty(db: Session) -> None:
    rows = leaderboard.get_leaderboard(db, period_start=date(2026, 9, 1), period_end=date(2026, 10, 1))
    assert rows == []


# ---------- Tenant score ----------


def test_get_tenant_score_dict(db: Session) -> None:
    t = _tenant(db, "t1", {"type": "hotel", "rating": 4.8, "reviews_count": 300})
    ps, pe = date(2026, 9, 1), date(2026, 10, 1)
    leaderboard.recompute_scores(db, period_start=ps, period_end=pe)

    row = leaderboard.get_tenant_score(db, tenant_id=t.id, period_start=ps, period_end=pe)
    assert row is not None
    assert row.overall_score > 0
    assert row.customer_satisfaction > 0


def test_get_tenant_score_dict_returns_none_for_missing_period(db: Session) -> None:
    """For a tenant with no score in the current period, returns None."""
    t = _tenant(db, "no-score", {"type": "hotel", "rating": 4.0})
    # Do NOT call recompute — no score exists for current period
    d = leaderboard.get_tenant_score_dict(db, tenant_id=t.id)
    assert d is None


def test_get_tenant_score_dict_for_current_period(db: Session) -> None:
    t = _tenant(db, "t2", {"type": "hotel", "rating": 4.5, "reviews_count": 200})
    ps, pe = scoring_engine.current_period()
    leaderboard.recompute_scores(db, period_start=ps, period_end=pe)

    d = leaderboard.get_tenant_score_dict(db, tenant_id=t.id)
    assert d is not None
    assert d["tenant_id"] == t.id
    assert d["category"] == "hotels"
    assert 0.0 <= d["overall_score"] <= 100.0
    assert d["rank_overall"] == 1
    assert d["rewards"]["badge"] == "gold"
    assert "criteria_breakdown" in d
