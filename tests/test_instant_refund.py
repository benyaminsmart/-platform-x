"""Tests for Instant Refund AI (Phase 54, Step 1)."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai import instant_refund as ir


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="g@x.com", tier="welcome"):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper() + tier[:2].upper(),
             status="active", tier=tier)
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db, t, u, *, days_from_now=10, amount=1000, status="confirmed"):
    ci = date.today() + timedelta(days=days_from_now)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_name="R", check_in=ci,
                check_out=ci + timedelta(days=1), guests=1,
                amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency="AED",
                status=status, payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def _confirm_booking(db, t, u, *, days_ago=30):
    ci = date.today() - timedelta(days=days_ago)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_name="R", check_in=ci,
                check_out=ci + timedelta(days=1), guests=1,
                amount=Decimal("100"), discount=Decimal("0"),
                total_amount=Decimal("100"), currency="AED",
                status="confirmed", payment_status="paid")
    db.add(b); db.commit()
    return b


def _cancelled_booking(db, t, u, *, days_ago=10):
    ci = date.today() - timedelta(days=days_ago)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_name="R", check_in=ci,
                check_out=ci + timedelta(days=1), guests=1,
                amount=Decimal("100"), discount=Decimal("0"),
                total_amount=Decimal("100"), currency="AED",
                status="cancelled", payment_status="paid",
                cancelled_at=datetime.now(timezone.utc) - timedelta(days=days_ago))
    db.add(b); db.commit()
    return b


def test_invalid_language(db):
    t = _tenant(db, "ir-lang")
    u = _user(db, t)
    b = _booking(db, t, u)
    with pytest.raises(ValueError):
        ir.evaluate(db, booking=b, user=u, language="xx")


def test_welcome_user_no_adjustment(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "ir-base")
    u = _user(db, t, "base@x.com", tier="welcome")
    b = _booking(db, t, u, days_from_now=10, amount=1000)
    out = ir.evaluate(db, booking=b, user=u)
    assert out["base_pct"] == 100
    assert out["suggested_pct"] == 100
    assert out["delta_pp"] == 0
    assert out["policy_label"] == "full"


def test_loyalty_user_positive_delta_bounded(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "ir-royal")
    u = _user(db, t, "royal@x.com", tier="royal")
    for i in range(12):
        _confirm_booking(db, t, u, days_ago=30 + i)
    b = _booking(db, t, u, days_from_now=2, amount=1000)
    out = ir.evaluate(db, booking=b, user=u)
    assert out["base_pct"] == 0
    assert out["suggested_pct"] == 20
    assert out["delta_pp"] == 20


def test_positive_delta_never_exceeds_platform_cap(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "ir-cap")
    u = _user(db, t, "cap@x.com", tier="royal")
    for i in range(20):
        _confirm_booking(db, t, u, days_ago=30 + i)
    b = _booking(db, t, u, days_from_now=2)
    out = ir.evaluate(db, booking=b, user=u)
    assert out["delta_pp"] <= 25


def test_negative_delta_due_to_recent_cancellations(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "ir-fraud")
    u = _user(db, t, "cancel-heavy@x.com", tier="welcome")
    for i in range(4):
        _cancelled_booking(db, t, u, days_ago=5 + i)
    b = _booking(db, t, u, days_from_now=1)
    out = ir.evaluate(db, booking=b, user=u)
    assert out["base_pct"] == 0
    assert out["suggested_pct"] == 0
    assert out["delta_pp"] == 0


def test_suggested_pct_stays_within_0_100(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "ir-bound")
    u = _user(db, t, "bound@x.com", tier="royal")
    for i in range(20):
        _confirm_booking(db, t, u, days_ago=30 + i)
    b = _booking(db, t, u, days_from_now=10)
    out = ir.evaluate(db, booking=b, user=u)
    assert 0 <= out["suggested_pct"] <= 100


def test_fallback_when_ai_fails(db, monkeypatch):
    from app.services.ai import service as ai_service
    def _boom(*a, **kw): raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)
    t = _tenant(db, "ir-fb")
    u = _user(db, t, "fb@x.com", tier="royal")
    b = _booking(db, t, u, days_from_now=10)
    out = ir.evaluate(db, booking=b, user=u)
    assert out["provider"] == "fallback"
    assert out["rationale"]


def test_ai_rationale_received(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI_RATIONALE_TEXT", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "ir-ai")
    u = _user(db, t, "ai@x.com", tier="gold")
    b = _booking(db, t, u, days_from_now=2)
    out = ir.evaluate(db, booking=b, user=u)
    assert out["provider"] == "ai"
    assert out["rationale"] == "AI_RATIONALE_TEXT"
