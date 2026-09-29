"""Tests for Leaderboard AI Tips (Phase 29, Step 5)."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.business_score import BusinessScore
from app.models.service import Service
from app.models.tenant import Tenant
from app.services import leaderboard as lb_service
from app.services import leaderboard_tips, scoring_engine


# ---------- Helpers ----------


def _tenant(db: Session, slug: str, cfg: dict) -> Tenant:
    t = Tenant(slug=slug, name=slug, tier="starter", status="active", config=cfg)
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


def _score_row(db: Session, tenant: Tenant) -> BusinessScore:
    ps, pe = scoring_engine.current_period()
    lb_service.recompute_scores(db, period_start=ps, period_end=pe)
    return (
        db.query(BusinessScore)
        .filter(BusinessScore.tenant_id == tenant.id,
                BusinessScore.period_start == ps,
                BusinessScore.period_end == pe)
        .one()
    )


# ---------- _weakest_criteria ----------


def test_weakest_criteria_ordering(db: Session) -> None:
    t = _tenant(db, "t", {"type": "hotel"})
    row = _score_row(db, t)

    # Manually set criteria to known values for the ordering test
    row.customer_satisfaction = 80.0
    row.service_quality = 30.0
    row.pricing_competitiveness = 90.0
    row.engagement = 50.0
    row.loyalty = 10.0
    db.commit()

    weakest = leaderboard_tips._weakest_criteria(row, n=3)
    assert [w["key"] for w in weakest] == ["loyalty", "service_quality", "engagement"]
    assert weakest[0]["score"] == 10.0
    assert weakest[0]["gap_to_100"] == 90.0


# ---------- _next_rank_gap ----------


def test_next_rank_gap_when_rank_1(db: Session) -> None:
    t = _tenant(db, "only", {"type": "hotel", "rating": 5.0, "reviews_count": 500})
    row = _score_row(db, t)
    assert row.rank_in_category == 1
    gap = leaderboard_tips._next_rank_gap(row, db)
    assert gap is None


def test_next_rank_gap_between_two(db: Session) -> None:
    _tenant(db, "top", {"type": "hotel", "rating": 5.0, "reviews_count": 1000})
    _tenant(db, "second", {"type": "hotel", "rating": 3.0, "reviews_count": 100})
    ps, pe = scoring_engine.current_period()
    lb_service.recompute_scores(db, period_start=ps, period_end=pe)

    second_row = (
        db.query(BusinessScore)
        .filter(BusinessScore.rank_in_category == 2)
        .one()
    )
    gap = leaderboard_tips._next_rank_gap(second_row, db)
    assert gap is not None
    assert gap["target_rank"] == 1
    assert gap["target_overall_score"] >= second_row.overall_score
    assert gap["gap"] >= 0


# ---------- generate_tips ----------


def test_generate_tips_empty_tenant(db: Session) -> None:
    t = _tenant(db, "empty", {"type": "hotel"})
    row = _score_row(db, t)
    out = leaderboard_tips.generate_tips(db, tenant=t, row=row)
    assert "weakest" in out
    assert len(out["weakest"]) == 3
    assert isinstance(out["advice"], str)
    assert out["advice"]  # non-empty (content depends on the active AI provider/stub)


def test_generate_tips_strong_tenant(db: Session) -> None:
    t = _tenant(db, "strong", {
        "type": "hotel",
        "rating": 5.0,
        "reviews_count": 2000,
        "tagline": "Best",
        "location": "Dubai",
        "cover_image": "x",
        "gallery": ["a"],
        "amenities": ["wifi"],
    })
    _svc(db, t, name="R1")
    _svc(db, t, name="R2", price=600)
    row = _score_row(db, t)
    out = leaderboard_tips.generate_tips(db, tenant=t, row=row)
    # Strong tenant has higher scores; weakest should still be well-defined
    assert len(out["weakest"]) == 3
    assert out["advice"]


def test_generate_tips_fallback_when_ai_fails(db: Session, monkeypatch) -> None:
    from app.services import leaderboard_tips as lt
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("simulated AI failure")

    monkeypatch.setattr(ai_service, "chat", _boom)

    t = _tenant(db, "fallback", {"type": "hotel", "rating": 3.0, "reviews_count": 10})
    row = _score_row(db, t)
    out = lt.generate_tips(db, tenant=t, row=row)
    # Should still return a non-empty fallback advice
    assert out["advice"]
    assert "Focus on these areas" in out["advice"] or "score" in out["advice"].lower()


def test_generate_tips_uses_ai_when_available(db: Session, monkeypatch) -> None:
    from app.services import leaderboard_tips as lt
    from app.services.ai import service as ai_service

    called = {"n": 0}

    def _fake_chat(message, *, history=None, provider_name=None):
        called["n"] += 1
        return {"content": "AI_GENERATED_ADVICE", "provider": "stub", "model": "x", "tokens_used": 0}

    monkeypatch.setattr(ai_service, "chat", _fake_chat)

    t = _tenant(db, "with-ai", {"type": "hotel", "rating": 4.0, "reviews_count": 100})
    row = _score_row(db, t)
    out = lt.generate_tips(db, tenant=t, row=row)
    assert called["n"] == 1
    assert out["advice"] == "AI_GENERATED_ADVICE"


def test_generate_tips_next_rank_present(db: Session) -> None:
    _tenant(db, "first", {"type": "hotel", "rating": 5.0, "reviews_count": 1000})
    _tenant(db, "second", {"type": "hotel", "rating": 3.0, "reviews_count": 100})
    ps, pe = scoring_engine.current_period()
    lb_service.recompute_scores(db, period_start=ps, period_end=pe)

    second_t = (
        db.query(Tenant).filter(Tenant.slug == "second").one()
    )
    second_row = (
        db.query(BusinessScore)
        .filter(BusinessScore.tenant_id == second_t.id)
        .one()
    )
    out = leaderboard_tips.generate_tips(db, tenant=second_t, row=second_row)
    assert out["next_rank_gap"] is not None
    assert out["next_rank_gap"]["target_rank"] == 1
