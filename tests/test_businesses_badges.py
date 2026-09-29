"""Tests: businesses page shows leaderboard badges (Phase 29, Step 8)."""

from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.tenant import Tenant
from app.services import leaderboard as lb_service
from app.services import scoring_engine


def _tenant(db: Session, slug: str, cfg: dict) -> Tenant:
    t = Tenant(slug=slug, name=slug, tier="starter", status="active", config=cfg)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def test_businesses_page_has_badge_css(client: TestClient) -> None:
    r = client.get("/businesses")
    assert r.status_code == 200
    assert "px-lb-card-badge" in r.text


def test_businesses_page_no_badges_when_no_scores(client: TestClient, db: Session) -> None:
    _tenant(db, "h1", {"type": "hotel", "rating": 4.5})
    r = client.get("/businesses")
    assert r.status_code == 200
    # CSS is present (marker), but no badge element rendered
    assert "px-lb-card-badge-gold" in r.text  # css rule present
    # No actual badge element with gold class in a thumbnail
    assert '<span class="px-lb-card-badge px-lb-card-badge-gold">' not in r.text


def test_businesses_page_renders_gold_badge_for_rank_1(client: TestClient, db: Session) -> None:
    t1 = _tenant(db, "champ", {"type": "hotel", "rating": 5.0, "reviews_count": 500})
    _tenant(db, "second", {"type": "hotel", "rating": 3.0, "reviews_count": 100})

    ps, pe = scoring_engine.current_period()
    lb_service.recompute_scores(db, period_start=ps, period_end=pe)

    r = client.get("/businesses")
    assert r.status_code == 200
    # The gold badge span must be present for the rank-1 tenant
    assert 'px-lb-card-badge px-lb-card-badge-gold' in r.text


def test_businesses_page_renders_silver_badge_for_rank_2(client: TestClient, db: Session) -> None:
    _tenant(db, "first", {"type": "hotel", "rating": 5.0, "reviews_count": 500})
    _tenant(db, "second", {"type": "hotel", "rating": 3.0, "reviews_count": 100})

    ps, pe = scoring_engine.current_period()
    lb_service.recompute_scores(db, period_start=ps, period_end=pe)

    r = client.get("/businesses")
    assert r.status_code == 200
    assert "px-lb-card-badge-silver" in r.text
