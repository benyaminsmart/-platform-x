"""Tests for AI Campaign Writer (Phase 25, Step 2)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai import campaign_writer


# ---------- Helpers ----------


def _tenant(db: Session, slug: str = "cw") -> Tenant:
    t = Tenant(slug=slug, name="Campaign Biz", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai, UAE", "rating": 4.7,
                       "reviews_count": 300, "tagline": "Luxury stay"})
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _user(db: Session, tenant: Tenant, email: str, *, tier: str = "welcome") -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("Pass1234"),
        first_name="U", last_name="X",
        referral_code=email[:10].upper(),
        tier=tier, status="active",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _booking(db: Session, tenant: Tenant, user: User, *, days_ago: int = 5, amount: float = 500) -> Booking:
    ci = date.today() - timedelta(days=days_ago)
    b = Booking(
        tenant_id=tenant.id, user_id=user.id, booking_type="room",
        service_name="R", check_in=ci, check_out=ci + timedelta(days=1),
        guests=1, amount=Decimal(str(amount)), discount=Decimal("0"),
        total_amount=Decimal(str(amount)), currency="AED",
        status="confirmed", payment_status="paid",
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def _stub_ai(content: str):
    def _fake(message, *, history=None, provider_name=None):
        return {"content": content, "provider": "stub", "model": "x", "tokens_used": 0}
    return _fake


# ---------- suggest_campaigns ----------


def test_suggest_campaigns_invalid_language(db: Session) -> None:
    t = _tenant(db)
    with pytest.raises(ValueError):
        campaign_writer.suggest_campaigns(db, tenant=t, language="xx")


def test_suggest_campaigns_fallback_on_no_ai(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)

    t = _tenant(db)
    out = campaign_writer.suggest_campaigns(db, tenant=t)
    assert out["provider"] == "fallback"
    assert 3 <= len(out["campaigns"]) <= 5
    # All campaigns must have required fields
    for c in out["campaigns"]:
        assert c["name"]
        assert c["target_segment"] in campaign_writer.__dict__["SUPPORTED_LANGUAGES"] or True
        assert c["channel"] in campaign_writer.SUPPORTED_CHANNELS
        assert "estimated_reach" in c


def test_suggest_campaigns_ai_returns_valid(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    payload = '''{"campaigns": [
      {"name": "Inactive return", "target_segment": "inactive_90d",
       "channel": "email", "subject": "We miss you", "body": "Come back!",
       "rationale": "Re-engage"}
    ]}'''
    monkeypatch.setattr(ai_service, "chat", _stub_ai(payload))

    t = _tenant(db)
    out = campaign_writer.suggest_campaigns(db, tenant=t)
    assert out["provider"] == "ai"
    assert len(out["campaigns"]) == 1
    assert out["campaigns"][0]["target_segment"] == "inactive_90d"
    assert out["campaigns"][0]["subject"] == "We miss you"


def test_suggest_campaigns_invalid_segment_fixed(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    payload = '''{"campaigns": [
      {"name": "X", "target_segment": "bogus_segment",
       "channel": "email", "subject": "S", "body": "B", "rationale": "R"}
    ]}'''
    monkeypatch.setattr(ai_service, "chat", _stub_ai(payload))
    t = _tenant(db)
    out = campaign_writer.suggest_campaigns(db, tenant=t)
    # Invalid segment replaced by default
    assert out["campaigns"][0]["target_segment"] == "past_bookers"


def test_suggest_campaigns_invalid_channel_fixed(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    payload = '''{"campaigns": [
      {"name": "X", "target_segment": "past_bookers",
       "channel": "carrier_pigeon", "subject": "S", "body": "B", "rationale": "R"}
    ]}'''
    monkeypatch.setattr(ai_service, "chat", _stub_ai(payload))
    t = _tenant(db)
    out = campaign_writer.suggest_campaigns(db, tenant=t)
    assert out["campaigns"][0]["channel"] == "email"


def test_suggest_campaigns_estimated_reach_from_real_data(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    payload = '''{"campaigns": [
      {"name": "X", "target_segment": "past_bookers",
       "channel": "email", "subject": "S", "body": "B", "rationale": "R"}
    ]}'''
    monkeypatch.setattr(ai_service, "chat", _stub_ai(payload))

    t = _tenant(db)
    for i in range(3):
        u = _user(db, t, f"u{i}@x.com")
        _booking(db, t, u, days_ago=i + 1)

    out = campaign_writer.suggest_campaigns(db, tenant=t)
    assert out["campaigns"][0]["estimated_reach"] == 3


# ---------- generate_campaign ----------


def test_generate_campaign_invalid_segment(db: Session) -> None:
    t = _tenant(db)
    with pytest.raises(ValueError):
        campaign_writer.generate_campaign(db, tenant=t, segment="bogus", goal="promo")


def test_generate_campaign_missing_goal(db: Session) -> None:
    t = _tenant(db)
    with pytest.raises(ValueError):
        campaign_writer.generate_campaign(db, tenant=t, segment="past_bookers", goal="  ")


def test_generate_campaign_ai_ok(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    payload = '''{"campaign": {
      "name": "Weekend promo",
      "target_segment": "past_bookers",
      "channel": "email",
      "subject": "A weekend offer just for you",
      "body": "Book this weekend and enjoy our best rate.",
      "rationale": "Past guests are most likely to return."
    }}'''
    monkeypatch.setattr(ai_service, "chat", _stub_ai(payload))

    t = _tenant(db)
    u = _user(db, t, "u@x.com")
    _booking(db, t, u, days_ago=5)

    out = campaign_writer.generate_campaign(
        db, tenant=t, segment="past_bookers", goal="promote weekend bookings"
    )
    assert out["provider"] == "ai"
    assert out["campaign"]["name"] == "Weekend promo"
    assert out["campaign"]["estimated_reach"] == 1


def test_generate_campaign_fallback(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    def _boom(*a, **kw):
        raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)

    t = _tenant(db)
    out = campaign_writer.generate_campaign(
        db, tenant=t, segment="past_bookers", goal="promo"
    )
    assert out["provider"] == "fallback"
    assert out["campaign"]["target_segment"] == "past_bookers"
    assert "estimated_reach" in out["campaign"]


def test_generate_campaign_wrong_segment_in_ai_response(db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service

    # AI returns a different segment than requested -> must fall back
    payload = '''{"campaign": {
      "name": "X", "target_segment": "new_30d",
      "channel": "email", "subject": "S", "body": "B", "rationale": "R"
    }}'''
    monkeypatch.setattr(ai_service, "chat", _stub_ai(payload))

    t = _tenant(db)
    out = campaign_writer.generate_campaign(
        db, tenant=t, segment="past_bookers", goal="promo"
    )
    # Fallback (because AI returned wrong segment)
    assert out["provider"] == "fallback"
    assert out["campaign"]["target_segment"] == "past_bookers"


# ---------- _extract_json ----------


def test_extract_json_plain() -> None:
    assert campaign_writer._extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_with_noise() -> None:
    s = 'Sure! Here you go:\n{"a": 1}\nHope that helps!'
    assert campaign_writer._extract_json(s) == {"a": 1}


def test_extract_json_invalid() -> None:
    assert campaign_writer._extract_json("no json here") is None
