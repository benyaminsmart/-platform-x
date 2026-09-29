"""Tests for AI Market Analyst (Phase 27, Step 2)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.service import Service
from app.models.tenant import Tenant
from app.services.ai import market_analyst


# ---------- Helpers ----------


def _tenant(db: Session, slug: str, *, cfg: dict | None = None) -> Tenant:
    t = Tenant(slug=slug, name=slug, tier="starter", status="active", config=cfg or {"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db: Session, tenant: Tenant, *, price: float = 500) -> Service:
    s = Service(
        tenant_id=tenant.id, type="room", name="R",
        price=Decimal(str(price)), currency="AED", capacity=2,
        attributes={}, image_urls=[], status="active", display_order=0,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s


def _stub_ai(content: str):
    def _fake(message, *, history=None, provider_name=None):
        return {"content": content, "provider": "stub", "model": "x", "tokens_used": 0}
    return _fake


# ---------- highlight_strengths_and_weaknesses ----------


def test_highlights_none_when_no_position() -> None:
    out = market_analyst.highlight_strengths_and_weaknesses(None)
    assert out == {"strengths": [], "weaknesses": []}


def test_highlights_strengths_over_70() -> None:
    position = {
        "positions": {
            "avg_price": {"value": 800, "percentile": 85},
            "rating": {"value": 4.8, "percentile": 90},
            "service_count": {"value": 3, "percentile": 40},
            "bookings_last_30d": {"value": 2, "percentile": 20},
        }
    }
    out = market_analyst.highlight_strengths_and_weaknesses(position)
    strengths_keys = [s["key"] for s in out["strengths"]]
    weaknesses_keys = [w["key"] for w in out["weaknesses"]]
    assert "rating" in strengths_keys
    assert "avg_price" in strengths_keys
    assert "bookings_last_30d" in weaknesses_keys
    # sorted desc for strengths
    assert out["strengths"][0]["percentile"] >= out["strengths"][1]["percentile"]
    # sorted asc for weaknesses
    assert out["weaknesses"][0]["percentile"] <= out["weaknesses"][-1]["percentile"]


def test_highlights_skips_middle_band() -> None:
    position = {
        "positions": {
            "avg_price": {"value": 500, "percentile": 50},
            "rating": {"value": 4.0, "percentile": 50},
        }
    }
    out = market_analyst.highlight_strengths_and_weaknesses(position)
    assert out["strengths"] == []
    assert out["weaknesses"] == []


# ---------- interpret_market ----------


def test_interpret_invalid_language(db: Session) -> None:
    t = _tenant(db, "invalid-lang")
    with pytest.raises(ValueError):
        market_analyst.interpret_market(db, t, language="xx")


def test_interpret_empty_cohort(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)

    t = _tenant(db, "solo", cfg={"type": "hotel"})
    out = market_analyst.interpret_market(db, t)
    assert out["provider"] == "fallback"
    assert "no other active businesses" in out["summary"].lower() or "cohort" in out["summary"].lower()
    assert out["advice"]


def test_interpret_with_ai(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    payload = '{"summary": "You are doing great.", "advice": "Keep it up."}'
    monkeypatch.setattr(ai_service, "chat", _stub_ai(payload))

    t = _tenant(db, "self", cfg={"type": "hotel", "location": "Downtown, Dubai, UAE", "rating": 4.5})
    _svc(db, t, price=500)
    _tenant(db, "p1", cfg={"type": "hotel", "location": "Marina, Dubai, UAE", "rating": 4.0})
    _svc(db, "p1" and _tenant(db, "p1", cfg={"type": "hotel"}) if False else t, price=500)  # no-op safety

    out = market_analyst.interpret_market(db, t)
    assert out["provider"] == "ai"
    assert out["summary"] == "You are doing great."
    assert out["advice"] == "Keep it up."


def test_interpret_ai_with_noise(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    payload = 'Sure!\n{"summary": "Nice.", "advice": "Do more."}\nDone.'
    monkeypatch.setattr(ai_service, "chat", _stub_ai(payload))
    t = _tenant(db, "self2", cfg={"type": "hotel"})
    out = market_analyst.interpret_market(db, t)
    assert out["summary"] == "Nice."
    assert out["advice"] == "Do more."


def test_interpret_fallback_on_invalid_json(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    monkeypatch.setattr(ai_service, "chat", _stub_ai("not json at all"))
    t = _tenant(db, "self3", cfg={"type": "hotel"})
    out = market_analyst.interpret_market(db, t)
    assert out["provider"] == "fallback"
    assert out["summary"]


def test_interpret_includes_strengths_weaknesses(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)

    # self has expensive price + high rating -> both strengths
    t_self = _tenant(db, "self4", cfg={"type": "hotel", "rating": 4.9})
    _svc(db, t_self, price=900)
    for i, (price, rating) in enumerate([(300, 3.5), (400, 4.0), (500, 4.2)], start=1):
        p = _tenant(db, f"p{i}x", cfg={"type": "hotel", "rating": rating})
        _svc(db, p, price=price)

    out = market_analyst.interpret_market(db, t_self)
    keys = [s["key"] for s in out["strengths"]]
    assert "avg_price" in keys
    assert "rating" in keys


def test_interpret_languages(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _fake(message, *, history=None, provider_name=None):
        # respond with a valid JSON regardless of language
        return {"content": '{"summary": "ok", "advice": "go"}', "provider": "stub", "model": "x", "tokens_used": 0}
    monkeypatch.setattr(ai_service, "chat", _fake)

    t = _tenant(db, "self5", cfg={"type": "hotel"})
    for lang in ["en", "ar", "fil", "hi"]:
        out = market_analyst.interpret_market(db, t, language=lang)
        assert out["summary"] == "ok"

def test_interpret_ai_returns_list_advice(db: Session, monkeypatch) -> None:
    """Regression: AI may return advice as a list of strings."""
    from app.services.ai import service as ai_service

    payload = (
        '{"summary": "Great position.", '
        '"advice": ["Improve pricing", "Add services", "Boost marketing"]}'
    )
    monkeypatch.setattr(ai_service, "chat", _stub_ai(payload))

    t = _tenant(db, "ai-list", cfg={"type": "hotel"})
    out = market_analyst.interpret_market(db, t)
    assert out["provider"] == "ai"
    assert "Improve pricing" in out["advice"]
    assert "Add services" in out["advice"]


def test_interpret_ai_returns_dict_summary(db: Session, monkeypatch) -> None:
    """Regression: AI may return summary as a dict."""
    from app.services.ai import service as ai_service

    payload = (
        '{"summary": {"title": "Position", "body": "Top quartile."}, '
        '"advice": "Keep going."}'
    )
    monkeypatch.setattr(ai_service, "chat", _stub_ai(payload))

    t = _tenant(db, "ai-dict", cfg={"type": "hotel"})
    out = market_analyst.interpret_market(db, t)
    assert out["provider"] == "ai"
    assert "Position" in out["summary"]
    assert "Top quartile" in out["summary"]

