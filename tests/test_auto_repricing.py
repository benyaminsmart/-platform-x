"""Tests for AI Auto-Repricing (Phase 60, Step 1)."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai import auto_repricing as ar


def _tenant(db, slug, typ="hotel", enabled=True):
    cfg = {"type": typ, "rating": 4.5, "location": "Dubai"}
    if enabled:
        cfg["auto_repricing_enabled"] = True
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config=cfg)
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, price=1000, capacity=2):
    s = Service(tenant_id=t.id, type="room", name="Room",
                price=Decimal(str(price)), currency="AED", capacity=capacity,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _user(db, t, email="g@x.com"):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db, t, u, svc, target_date, status="confirmed"):
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_id=svc.id, service_name=svc.name,
                check_in=target_date, check_out=target_date + timedelta(days=1),
                guests=1, amount=Decimal("1000"), discount=Decimal("0"),
                total_amount=Decimal("1000"), currency="AED",
                status=status, payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_invalid_language(db):
    t = _tenant(db, "ar-lang")
    s = _svc(db, t)
    with pytest.raises(ValueError):
        ar.suggest_price(db, tenant=t, service=s, language="xx")


def test_disabled_tenant(db):
    t = _tenant(db, "ar-disabled", enabled=False)
    s = _svc(db, t)
    out = ar.suggest_price(db, tenant=t, service=s)
    assert out["status"] == "disabled"
    assert out["suggested_price"] is None


def test_not_found(db):
    t = _tenant(db, "ar-nf")
    out = ar.suggest_price(db, tenant=t, service=None)
    assert out["status"] == "not_found"


def test_high_occupancy_raises_price(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "ar-high")
    u = _user(db, t)
    s = _svc(db, t, price=1000, capacity=2)
    target = date.today() + timedelta(days=1)
    _booking(db, t, u, s, target)
    u2 = _user(db, t, "u2@x.com")
    _booking(db, t, u2, s, target)

    out = ar.suggest_price(db, tenant=t, service=s, target_date=target)
    assert out["status"] == "ok"
    assert out["suggested_price"] > out["base_price"]
    assert out["signals"]["occupancy_pct"] == 100.0


def test_low_occupancy_lowers_price(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "ar-low")
    s = _svc(db, t, price=1000, capacity=10)
    target = date.today() + timedelta(days=10)
    out = ar.suggest_price(db, tenant=t, service=s, target_date=target)
    assert out["status"] == "ok"
    assert out["suggested_price"] <= out["base_price"]


def test_suggested_price_bounded_upper(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "ar-cap-up")
    u = _user(db, t)
    s = _svc(db, t, price=1000, capacity=1)
    target = date.today() + timedelta(days=1)
    _booking(db, t, u, s, target)
    for i in range(15):
        _booking(db, t, u, s, target + timedelta(days=20))
    out = ar.suggest_price(db, tenant=t, service=s, target_date=target)
    assert out["suggested_price"] <= float(Decimal("1000") * (Decimal("1") + ar.MAX_UP))


def test_suggested_price_bounded_lower(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "ar-cap-down")
    s = _svc(db, t, price=1000, capacity=100)
    target = date.today() + timedelta(days=60)
    out = ar.suggest_price(db, tenant=t, service=s, target_date=target)
    assert out["suggested_price"] >= float(Decimal("1000") * (Decimal("1") - ar.MAX_DOWN))


def test_fallback_when_ai_fails(db, monkeypatch):
    from app.services.ai import service as ai_service
    def _boom(*a, **kw): raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)
    t = _tenant(db, "ar-fb")
    s = _svc(db, t, price=1000)
    out = ar.suggest_price(db, tenant=t, service=s)
    assert out["status"] == "ok"
    assert out["provider"] == "fallback"
    assert out["rationale"]
