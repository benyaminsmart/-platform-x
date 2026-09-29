"""Tests for the leaderboard badges helper (Phase 29, Step 8)."""

from datetime import date
from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.services import leaderboard as lb_service
from app.services import scoring_engine
from app.web.pages import _badges_by_tenant


def _tenant(db: Session, slug: str, cfg: dict) -> Tenant:
    t = Tenant(slug=slug, name=slug, tier="starter", status="active", config=cfg)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def test_badges_empty_when_no_scores(db: Session) -> None:
    _tenant(db, "h1", {"type": "hotel", "rating": 4.5})
    assert _badges_by_tenant(db) == {}


def test_badges_for_top_3_per_category(db: Session) -> None:
    t1 = _tenant(db, "h1", {"type": "hotel", "rating": 5.0, "reviews_count": 500})
    t2 = _tenant(db, "h2", {"type": "hotel", "rating": 4.0, "reviews_count": 300})
    t3 = _tenant(db, "h3", {"type": "hotel", "rating": 3.0, "reviews_count": 100})
    t4 = _tenant(db, "h4", {"type": "hotel", "rating": 2.0, "reviews_count": 50})

    ps, pe = scoring_engine.current_period()
    lb_service.recompute_scores(db, period_start=ps, period_end=pe)

    badges = _badges_by_tenant(db)
    assert badges.get(t1.id) == "gold"
    assert badges.get(t2.id) == "silver"
    assert badges.get(t3.id) == "bronze"
    assert t4.id not in badges
