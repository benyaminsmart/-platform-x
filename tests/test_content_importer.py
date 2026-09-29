"""Tests for AI Content Importer (Phase 23, Step 3)."""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.tenant import Tenant
from app.services.ai import content_importer


# ---------- Helpers ----------


def _tenant(db: Session, slug: str = "imp-biz") -> Tenant:
    t = Tenant(slug=slug, name="Importer Biz", tier="starter", status="active", config={})
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _stub_ai(content: str):
    def _fake(message, *, history=None, provider_name=None):
        return {"content": content, "provider": "stub", "model": "x", "tokens_used": 0}
    return _fake


# ---------- _parse_price ----------


def test_parse_price_variants() -> None:
    assert content_importer._parse_price(100) == Decimal("100")
    assert content_importer._parse_price("150.50") == Decimal("150.50")
    assert content_importer._parse_price("AED 200") == Decimal("200")
    assert content_importer._parse_price("1,200") == Decimal("1200")
    assert content_importer._parse_price("no number") is None
    assert content_importer._parse_price(None) is None


# ---------- Fallback parser ----------


def test_fallback_parse_basic_lines() -> None:
    text = """Deluxe Room - 850
Standard Room - 500
Sea View Suite - 1200
"""
    out = content_importer._fallback_parse(text, default_type="room")
    assert len(out) == 3
    assert out[0]["name"] == "Deluxe Room"
    assert out[0]["price"] == "850"
    assert out[1]["name"] == "Standard Room"
    assert out[1]["price"] == "500"


def test_fallback_parse_colon_separator() -> None:
    text = "Espresso: 15\nLatte: 22"
    out = content_importer._fallback_parse(text, default_type="menu_item")
    assert len(out) == 2
    assert out[0]["name"] == "Espresso"
    assert out[0]["price"] == "15"


def test_fallback_parse_trailing_number() -> None:
    text = "Deluxe Suite 1200\nBasic Room 500"
    out = content_importer._fallback_parse(text, default_type="room")
    assert out[0]["name"] == "Deluxe Suite"
    assert out[0]["price"] == "1200"


def test_fallback_parse_skips_empty_lines() -> None:
    text = "\n\nFirst Room - 100\n\n\nSecond Room - 200\n\n"
    out = content_importer._fallback_parse(text, default_type="room")
    assert len(out) == 2


def test_fallback_parse_no_price() -> None:
    text = "Deluxe Suite"
    out = content_importer._fallback_parse(text, default_type="room")
    assert len(out) == 1
    assert out[0]["name"] == "Deluxe Suite"
    assert out[0]["price"] is None


# ---------- parse_services_from_text ----------


def test_parse_empty_text_raises(db: Session) -> None:
    t = _tenant(db)
    with pytest.raises(ValueError):
        content_importer.parse_services_from_text(db, tenant=t, text="   ")


def test_parse_ai_returns_candidates(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    payload = (
        '{"candidates": ['
        '{"name": "Deluxe Room", "type": "room", "description": null, '
        '"price": 850, "currency": "AED", "capacity": 2, '
        '"attributes": {"view": "sea"}},'
        '{"name": "Standard Room", "type": "room", "description": null, '
        '"price": 500, "currency": "AED", "capacity": null, "attributes": {}}'
        ']}'
    )
    monkeypatch.setattr(ai_service, "chat", _stub_ai(payload))

    t = _tenant(db)
    out = content_importer.parse_services_from_text(db, tenant=t, text="some text")
    assert out["provider"] == "ai"
    assert out["count"] == 2
    assert out["candidates"][0]["name"] == "Deluxe Room"
    assert out["candidates"][0]["price"] == "850"
    assert out["candidates"][0]["capacity"] == 2
    assert out["candidates"][0]["attributes"] == {"view": "sea"}


def test_parse_ai_with_surrounding_noise(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    payload = (
        "Here you go:\n"
        '{"candidates": [{"name": "X", "type": "room", "price": 100}]}\n'
        "Hope this helps!"
    )
    monkeypatch.setattr(ai_service, "chat", _stub_ai(payload))
    t = _tenant(db)
    out = content_importer.parse_services_from_text(db, tenant=t, text="x")
    assert out["provider"] == "ai"
    assert out["candidates"][0]["name"] == "X"


def test_parse_ai_never_invents_price(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    payload = '{"candidates": [{"name": "Mystery Room", "type": "room", "price": null}]}'
    monkeypatch.setattr(ai_service, "chat", _stub_ai(payload))
    t = _tenant(db)
    out = content_importer.parse_services_from_text(db, tenant=t, text="x")
    assert out["candidates"][0]["price"] is None


def test_parse_invalid_type_falls_back_to_default(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    payload = '{"candidates": [{"name": "X", "type": "bogus_type", "price": 100}]}'
    monkeypatch.setattr(ai_service, "chat", _stub_ai(payload))
    t = _tenant(db)
    out = content_importer.parse_services_from_text(db, tenant=t, text="x", default_type="room")
    assert out["candidates"][0]["type"] == "room"


def test_parse_falls_back_on_invalid_json(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    monkeypatch.setattr(ai_service, "chat", _stub_ai("this is not json"))
    t = _tenant(db)
    out = content_importer.parse_services_from_text(
        db, tenant=t, text="Room A - 100\nRoom B - 200"
    )
    assert out["provider"] == "fallback"
    assert out["count"] == 2


def test_parse_falls_back_on_ai_exception(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("fail")

    monkeypatch.setattr(ai_service, "chat", _boom)
    t = _tenant(db)
    out = content_importer.parse_services_from_text(
        db, tenant=t, text="A - 10\nB - 20"
    )
    assert out["provider"] == "fallback"
    assert out["count"] == 2


def test_parse_truncates_long_text(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    monkeypatch.setattr(ai_service, "chat", _stub_ai('{"candidates": []}'))
    t = _tenant(db)
    long_text = "A - 10\n" * 2000  # ~ 12k chars
    out = content_importer.parse_services_from_text(db, tenant=t, text=long_text)
    # Should not raise, falls back to fallback parser
    assert out["provider"] == "fallback"
    assert out["count"] >= 1


# ---------- bulk_create_services ----------


def test_bulk_create_happy_path(db: Session) -> None:
    t = _tenant(db, "bulk-happy")
    candidates = [
        {"name": "A", "type": "room", "price": "100", "currency": "AED", "capacity": 2, "attributes": {}},
        {"name": "B", "type": "room", "price": "200", "currency": "AED", "capacity": None, "attributes": {}},
    ]
    out = content_importer.bulk_create_services(db, tenant=t, candidates=candidates)
    assert out["created"] == 2
    assert out["skipped"] == []
    assert len(out["service_ids"]) == 2

    # Verify in DB
    count = db.query(Service).filter(Service.tenant_id == t.id).count()
    assert count == 2


def test_bulk_create_skips_missing_name(db: Session) -> None:
    t = _tenant(db, "bulk-noname")
    candidates = [
        {"name": "", "type": "room", "price": "100"},
        {"name": "Good", "type": "room", "price": "200"},
    ]
    out = content_importer.bulk_create_services(db, tenant=t, candidates=candidates)
    assert out["created"] == 1
    assert len(out["skipped"]) == 1
    assert "missing name" in out["skipped"][0]["reason"]


def test_bulk_create_skips_negative_price(db: Session) -> None:
    t = _tenant(db, "bulk-neg")
    candidates = [
        {"name": "Bad", "type": "room", "price": "-50"},
        {"name": "Good", "type": "room", "price": "200"},
    ]
    out = content_importer.bulk_create_services(db, tenant=t, candidates=candidates)
    assert out["created"] == 1
    assert len(out["skipped"]) == 1
    assert "negative price" in out["skipped"][0]["reason"]


def test_bulk_create_price_none_becomes_zero(db: Session) -> None:
    t = _tenant(db, "bulk-none")
    candidates = [{"name": "Free Trial", "type": "activity", "price": None}]
    out = content_importer.bulk_create_services(db, tenant=t, candidates=candidates)
    assert out["created"] == 1
    svc = db.query(Service).filter(Service.id == out["service_ids"][0]).one()
    assert svc.price == Decimal("0")
