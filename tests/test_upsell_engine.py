"""Tests for AI Upsell Engine (Phase 56, Step 1)."""
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.tenant import Tenant
from app.services.ai import upsell_engine as ue


def _tenant(db, slug, typ="hotel"):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": typ, "rating": 4.5, "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, name, price, typ="room", description=None, status="active"):
    s = Service(tenant_id=t.id, type=typ, name=name,
                description=description,
                price=Decimal(str(price)), currency="AED", capacity=2,
                attributes={}, image_urls=[], status=status, display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_invalid_language(db):
    t = _tenant(db, "ue-lang")
    s = _svc(db, t, "Room", 100)
    with pytest.raises(ValueError):
        ue.suggest(db, tenant=t, base_service_id=s.id, language="xx")


def test_no_base(db):
    t = _tenant(db, "ue-nobase")
    out = ue.suggest(db, tenant=t, base_service_id="does-not-exist")
    assert out["status"] == "no_base"
    assert out["suggestions"] == []


def test_empty_no_candidates(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "x", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "ue-empty")
    s = _svc(db, t, "Only Room", 100)
    out = ue.suggest(db, tenant=t, base_service_id=s.id)
    assert out["status"] == "empty"
    assert out["suggestions"] == []


def test_upgrade_and_ancillary_suggested(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI_PITCH", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "ue-full")
    base = _svc(db, t, "Standard", 100)
    _svc(db, t, "Deluxe", 200)
    _svc(db, t, "Breakfast Package", 80, typ="addon",
         description="Breakfast add-on for guests")

    out = ue.suggest(db, tenant=t, base_service_id=base.id)
    assert out["status"] == "ok"
    assert out["provider"] == "ai"
    assert out["rationale"] == "AI_PITCH"
    kinds = {s["kind"] for s in out["suggestions"]}
    assert "upgrade" in kinds or "ancillary" in kinds
    names = [s["service_name"] for s in out["suggestions"]]
    assert "Breakfast Package" in names
    assert "Deluxe" in names


def test_upgrade_not_included_if_too_expensive(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "x", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "ue-cap")
    base = _svc(db, t, "Standard", 100)
    _svc(db, t, "Royal Suite", 10000)
    out = ue.suggest(db, tenant=t, base_service_id=base.id)
    assert out["status"] == "empty"


def test_max_three_suggestions(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "x", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "ue-max")
    base = _svc(db, t, "Standard", 100)
    _svc(db, t, "Upgrade A", 150)
    _svc(db, t, "Breakfast", 30, typ="addon")
    _svc(db, t, "Spa", 200, typ="addon")
    _svc(db, t, "Tour", 250, typ="addon")
    out = ue.suggest(db, tenant=t, base_service_id=base.id)
    assert len(out["suggestions"]) <= 3


def test_fallback_when_ai_fails(db, monkeypatch):
    from app.services.ai import service as ai_service
    def _boom(*a, **kw): raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)
    t = _tenant(db, "ue-fb")
    base = _svc(db, t, "Standard", 100)
    _svc(db, t, "Breakfast", 30, typ="addon")
    out = ue.suggest(db, tenant=t, base_service_id=base.id)
    assert out["provider"] == "fallback"
    assert out["rationale"]
