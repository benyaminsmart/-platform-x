"""Tests for AI Content Writer (Phase 23, Step 1)."""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.tenant import Tenant
from app.services.ai import content_writer


# ---------- Helpers ----------


def _tenant(db: Session, slug: str = "cw-biz", cfg: dict | None = None) -> Tenant:
    t = Tenant(
        slug=slug, name="Test Hotel", tier="starter", status="active",
        config=cfg or {
            "type": "hotel",
            "location": "Dubai, UAE",
            "rating": 4.7,
            "reviews_count": 300,
            "tagline": "Luxury stay",
            "amenities": ["wifi", "pool", "spa"],
        },
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _svc(db: Session, tenant: Tenant, *, name: str = "Deluxe Suite", attrs: dict | None = None) -> Service:
    s = Service(
        tenant_id=tenant.id, type="room", name=name,
        price=Decimal("850"), currency="AED", capacity=2,
        attributes=attrs or {"view": "sea", "bed": "king"},
        image_urls=[], status="active", display_order=0,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# ---------- write_service_description ----------


def test_write_service_description_invalid_language(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t)
    with pytest.raises(ValueError):
        content_writer.write_service_description(db, tenant=t, service=s, language="fr")


def test_write_service_description_invalid_tone(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t)
    with pytest.raises(ValueError):
        content_writer.write_service_description(db, tenant=t, service=s, tone="rude")


def test_write_service_description_all_languages(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t)
    for lang in ["en", "ar", "fil", "hi"]:
        out = content_writer.write_service_description(db, tenant=t, service=s, language=lang)
        assert out["language"] == lang
        assert out["tone"] == "professional"
        assert isinstance(out["description"], str)
        assert out["description"]


def test_write_service_description_all_tones(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t)
    for tone in ["professional", "friendly", "luxury", "playful"]:
        out = content_writer.write_service_description(db, tenant=t, service=s, tone=tone)
        assert out["tone"] == tone
        assert out["description"]


def test_write_service_description_fallback_on_ai_failure(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("simulated")

    monkeypatch.setattr(ai_service, "chat", _boom)

    t = _tenant(db)
    s = _svc(db, t, name="Standard Room")
    out = content_writer.write_service_description(db, tenant=t, service=s)
    # Fallback description contains the service name
    assert "Standard Room" in out["description"]
    assert out["provider"] == "fallback"


def test_write_service_description_strips_surrounding_quotes(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _fake_chat(message, *, history=None, provider_name=None):
        return {"content": '"A lovely sea-view suite in Dubai."', "provider": "stub", "model": "x", "tokens_used": 0}

    monkeypatch.setattr(ai_service, "chat", _fake_chat)

    t = _tenant(db)
    s = _svc(db, t)
    out = content_writer.write_service_description(db, tenant=t, service=s)
    # Quotes stripped
    assert not out["description"].startswith('"')
    assert not out["description"].endswith('"')
    assert out["provider"] == "ai"


def test_prompt_contains_rating_only_when_strong(db: Session) -> None:
    # Strong rating
    t1 = _tenant(db, "strong", {"type": "hotel", "rating": 4.8, "reviews_count": 500})
    s1 = _svc(db, t1)
    p1 = content_writer._build_service_prompt(t1, s1, language="en", tone="professional")
    assert "safe to mention" in p1

    # Weak rating
    t2 = _tenant(db, "weak", {"type": "hotel", "rating": 3.2, "reviews_count": 50})
    s2 = _svc(db, t2)
    p2 = content_writer._build_service_prompt(t2, s2, language="en", tone="professional")
    assert "Do NOT mention a rating" in p2


# ---------- write_business_tagline ----------


def test_write_business_tagline_all_languages(db: Session) -> None:
    t = _tenant(db)
    for lang in ["en", "ar", "fil", "hi"]:
        out = content_writer.write_business_tagline(db, tenant=t, language=lang)
        assert out["language"] == lang
        assert out["tagline"]


def test_write_business_tagline_invalid_language(db: Session) -> None:
    t = _tenant(db)
    with pytest.raises(ValueError):
        content_writer.write_business_tagline(db, tenant=t, language="xx")


def test_write_business_tagline_fallback(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("simulated")

    monkeypatch.setattr(ai_service, "chat", _boom)

    t = _tenant(db, cfg={"type": "restaurant", "location": "Abu Dhabi, UAE"})
    out = content_writer.write_business_tagline(db, tenant=t)
    assert t.name in out["tagline"]


# ---------- suggest_image_keywords ----------


def test_suggest_image_keywords_basic(db: Session) -> None:
    t = _tenant(db, cfg={"type": "hotel", "location": "Dubai, UAE"})
    s = _svc(db, t, name="Deluxe Sea View Suite")
    out = content_writer.suggest_image_keywords(t, s)
    assert "keywords" in out
    assert "room" in [k.lower() for k in out["keywords"]]
    assert "hotel" in [k.lower() for k in out["keywords"]]
    # Location last segment (UAE) should be present
    assert any("uae" in k.lower() for k in out["keywords"])
    assert out["query"]
    assert "unsplash.com" in out["unsplash_search_url"]
    assert "source.unsplash.com" in out["unsplash_source_url"]


def test_suggest_image_keywords_dedupe(db: Session) -> None:
    t = _tenant(db, cfg={"type": "hotel", "location": "Dubai, UAE"})
    # name also contains "hotel"
    s = _svc(db, t, name="Hotel Suite")
    out = content_writer.suggest_image_keywords(t, s)
    # No duplicate keywords (case-insensitive)
    lc = [k.lower() for k in out["keywords"]]
    assert len(lc) == len(set(lc))


def test_suggest_image_keywords_empty_tenant(db: Session) -> None:
    t = _tenant(db, cfg={})
    s = _svc(db, t, name="X", attrs={})
    out = content_writer.suggest_image_keywords(t, s)
    # At least the service type should be present
    assert "room" in [k.lower() for k in out["keywords"]]
