"""Tests for AI Budget Optimizer (Phase 50, Step 1)."""
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.tenant import Tenant
from app.services.ai import budget_optimizer as bo


def _tenant(db, slug, typ="hotel", location="Dubai", rating=4.5):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": typ, "rating": rating, "location": location})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, price=500, typ="room"):
    s = Service(tenant_id=t.id, type=typ, name=f"{typ.capitalize()}-{t.slug}",
                price=Decimal(str(price)), currency="AED", capacity=4,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_invalid_language(db):
    with pytest.raises(ValueError):
        bo.optimize(db, budget=1000, language="xx")


def test_invalid_days(db):
    with pytest.raises(ValueError):
        bo.optimize(db, budget=1000, days=0)


def test_invalid_guests(db):
    with pytest.raises(ValueError):
        bo.optimize(db, budget=1000, guests=0)


def test_invalid_budget(db):
    with pytest.raises(ValueError):
        bo.optimize(db, budget=0)


def test_empty_city_returns_fallback(db):
    out = bo.optimize(db, city="Atlantis", budget=2000)
    assert out["package"] == []
    assert out["total_estimated"] == 0.0
    assert out["provider"] == "fallback"
    assert "No matching" in out["advice"]


def test_basic_package(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI_ADVICE", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    th = _tenant(db, "bo-h", typ="hotel", rating=4.8)
    tr = _tenant(db, "bo-r", typ="restaurant", rating=4.6)
    _svc(db, th, price=400, typ="room")
    _svc(db, tr, price=80, typ="table")

    out = bo.optimize(db, city="Dubai", days=3, guests=2, budget=5000)
    assert out["provider"] == "ai"
    assert out["advice"] == "AI_ADVICE"
    cats = {it["category"] for it in out["package"]}
    assert "hotels" in cats
    assert "restaurants" in cats
    assert out["total_estimated"] > 0
    assert out["remaining"] >= 0


def test_fallback_when_ai_fails(db, monkeypatch):
    from app.services.ai import service as ai_service
    def _boom(*a, **kw): raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)
    th = _tenant(db, "bo-fb-h", typ="hotel")
    _svc(db, th, price=300, typ="room")
    out = bo.optimize(db, city="Dubai", days=2, guests=2, budget=3000)
    assert out["provider"] == "fallback"
    assert "Recommended mix" in out["advice"]


def test_budget_redistribution_with_missing_category(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "ok", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    th = _tenant(db, "bo-red-h", typ="hotel")
    _svc(db, th, price=200, typ="room")
    out = bo.optimize(db, city="Dubai", days=2, guests=1, budget=2000)
    assert out["package"], "should still produce a package"
    assert out["package"][0]["category"] == "hotels"
