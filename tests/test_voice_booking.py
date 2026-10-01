"""Tests for AI Voice Booking (Phase 64, Step 1)."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.tenant import Tenant
from app.services.ai import voice_booking as vb


def _tenant(db, slug, typ="hotel", location="Dubai", rating=4.5):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": typ, "rating": rating, "location": location})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, name="Room", price=500):
    s = Service(tenant_id=t.id, type="room", name=name,
                price=Decimal(str(price)), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_invalid_language(db):
    with pytest.raises(ValueError):
        vb.voice_request(db, transcript="hello", language="xx")


def test_empty_transcript(db):
    out = vb.voice_request(db, transcript="")
    assert out["status"] == "empty"
    assert out["reply"] == ""


def test_unrecognized_transcript(db):
    out = vb.voice_request(db, transcript="blah blah nothing meaningful")
    assert out["status"] == "unrecognized"
    assert "couldn't catch" in out["reply"]


def test_parse_intent_basic():
    intent = vb.parse_intent("Book a hotel in Dubai next weekend for 2")
    assert intent["category"] == "hotels"
    assert intent["city"] == "Dubai"
    assert intent["guests"] == 2
    assert intent["check_in"] is not None


def test_parse_intent_restaurant():
    intent = vb.parse_intent("I want a table at a restaurant tomorrow for 4")
    assert intent["category"] == "restaurants"
    assert intent["guests"] == 4
    assert intent["check_in"] == (date.today() + timedelta(days=1)).isoformat()


def test_parse_intent_explicit_month():
    intent = vb.parse_intent("Book a room on March 15 for 2")
    assert intent["category"] == "hotels"
    assert intent["check_in"] is not None
    ci = date.fromisoformat(intent["check_in"])
    assert ci.month == 3 and ci.day == 15


def test_parse_intent_iso_date():
    intent = vb.parse_intent("I need a hotel 2030-05-10 to 2030-05-12 for 3")
    assert intent["check_in"] == "2030-05-10"
    assert intent["check_out"] == "2030-05-12"
    assert intent["guests"] == 3


def test_voice_request_with_ai(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI_REPLY", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "vb-full", typ="hotel", location="Dubai")
    _svc(db, t, "Deluxe Room", 500)
    out = vb.voice_request(db, transcript="Book a hotel in Dubai tomorrow for 2")
    assert out["status"] == "ok"
    assert out["provider"] == "ai"
    assert out["reply"] == "AI_REPLY"
    assert len(out["matches"]) >= 1


def test_voice_request_fallback(db, monkeypatch):
    from app.services.ai import service as ai_service
    def _boom(*a, **kw): raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)
    t = _tenant(db, "vb-fb", typ="restaurant", location="Dubai")
    _svc(db, t, "Table", 100)
    out = vb.voice_request(db, transcript="dinner in Dubai tonight for 2")
    assert out["status"] == "ok"
    assert out["provider"] == "fallback"
    assert "Understood" in out["reply"]
    assert "restaurants" in out["reply"]
