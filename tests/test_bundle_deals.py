"""Tests for AI Multi-Business Bundle Deals (Phase 51, Step 1)."""
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.tenant import Tenant
from app.services.ai import bundle_deals as bd


def _tenant(db, slug, typ="hotel", location="Dubai", rating=4.5):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": typ, "rating": rating, "location": location})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, price=500, typ="room"):
    s = Service(tenant_id=t.id, type=typ, name=f"{typ}-{t.slug}",
                price=Decimal(str(price)), currency="AED", capacity=4,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_invalid_language(db):
    with pytest.raises(ValueError):
        bd.build(db, language="xx")


def test_invalid_days(db):
    with pytest.raises(ValueError):
        bd.build(db, days=0)


def test_invalid_guests(db):
    with pytest.raises(ValueError):
        bd.build(db, guests=0)


def test_empty_returns_fallback(db):
    out = bd.build(db, city="Atlantis")
    assert out["items"] == []
    assert out["total"] == 0.0
    assert out["provider"] == "fallback"


def test_basic_bundle_with_ai(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI_PITCH", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    th = _tenant(db, "bd-h", typ="hotel", rating=4.9)
    tr1 = _tenant(db, "bd-r1", typ="restaurant", rating=4.8)
    tr2 = _tenant(db, "bd-r2", typ="restaurant", rating=4.7)
    _svc(db, th, price=400, typ="room")
    _svc(db, tr1, price=80, typ="table")
    _svc(db, tr2, price=100, typ="table")

    out = bd.build(db, city="Dubai", days=3, guests=2)
    assert out["provider"] == "ai"
    assert out["advice"] == "AI_PITCH"
    assert len(out["items"]) == 3
    cats = [it["category"] for it in out["items"]]
    assert "hotels" in cats
    assert "restaurants" in cats
    assert out["discount_percent"] == 10
    assert out["discount_amount"] > 0
    assert out["total"] < out["subtotal"]


def test_bundle_with_5_items_gets_20pct(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "x", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    th = _tenant(db, "bd5-h", typ="hotel")
    tr1 = _tenant(db, "bd5-r1", typ="restaurant")
    tr2 = _tenant(db, "bd5-r2", typ="restaurant")
    te = _tenant(db, "bd5-e", typ="entertainment")
    tt = _tenant(db, "bd5-t", typ="travel_agency")
    _svc(db, th, price=300, typ="room")
    _svc(db, tr1, price=50, typ="table")
    _svc(db, tr2, price=60, typ="table")
    _svc(db, te, price=100, typ="ticket")
    _svc(db, tt, price=200, typ="package")

    out = bd.build(db, city="Dubai", days=2, guests=2)
    assert len(out["items"]) == 5
    assert out["discount_percent"] == 20


def test_fallback_when_ai_fails(db, monkeypatch):
    from app.services.ai import service as ai_service
    def _boom(*a, **kw): raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)
    th = _tenant(db, "bd-fb-h", typ="hotel")
    _svc(db, th, price=300, typ="room")
    out = bd.build(db, city="Dubai")
    assert out["provider"] == "fallback"
    assert "Bundle of" in out["advice"]


def test_rounding_consistency(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "x", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    th = _tenant(db, "bd-round-h", typ="hotel")
    _svc(db, th, price=333.33, typ="room")
    out = bd.build(db, city="Dubai", days=3, guests=2)
    assert out["subtotal"] == round(out["subtotal"], 2)
    assert out["total"] == round(out["total"], 2)
