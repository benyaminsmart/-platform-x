"""Tests for AI Group Coordinator (Phase 59, Step 1)."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.group_member import GroupMember
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai import group_coordinator as gc


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="g@x.com"):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _svc(db, t, name="Room", price=500, capacity=2):
    s = Service(tenant_id=t.id, type="room", name=name,
                price=Decimal(str(price)), currency="AED", capacity=capacity,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _booking(db, t, u, svc=None, is_group=True, guests=12, amount=12000):
    ci = date.today() + timedelta(days=30)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_id=svc.id if svc else None,
                service_name="Room", check_in=ci,
                check_out=ci + timedelta(days=2), guests=guests,
                amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency="AED",
                status="confirmed", payment_status="paid",
                is_group=is_group)
    db.add(b); db.commit(); db.refresh(b)
    return b


def _member(db, booking, email, share=1000, paid=False):
    m = GroupMember(tenant_id=booking.tenant_id, booking_id=booking.id,
                    name=email.split("@")[0], email=email,
                    share_amount=Decimal(str(share)), paid=paid)
    db.add(m); db.commit(); db.refresh(m)
    return m


def test_invalid_language(db):
    t = _tenant(db, "gc-lang")
    u = _user(db, t)
    b = _booking(db, t, u)
    with pytest.raises(ValueError):
        gc.coordinate(db, booking=b, language="xx")


def test_not_group(db):
    t = _tenant(db, "gc-notgroup")
    u = _user(db, t, "ng@x.com")
    b = _booking(db, t, u, is_group=False)
    out = gc.coordinate(db, booking=b)
    assert out["status"] == "not_group"
    assert out["plan"] == ""


def test_too_small(db):
    t = _tenant(db, "gc-small")
    u = _user(db, t, "sm@x.com")
    b = _booking(db, t, u, guests=5)
    for i in range(3):
        _member(db, b, f"m{i}@x.com")
    out = gc.coordinate(db, booking=b)
    assert out["status"] == "too_small"
    assert out["stats"]["members_count"] == 3
    assert out["stats"]["min_required"] == 10


def test_ok_with_activities(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI_PLAN", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "gc-full")
    u = _user(db, t, "full@x.com")
    svc = _svc(db, t, capacity=2)
    _svc(db, t, name="Group Dinner", price=200, capacity=20)
    b = _booking(db, t, u, svc=svc, guests=12, amount=12000)
    for i in range(12):
        _member(db, b, f"m{i}@x.com", share=1000, paid=(i < 5))
    out = gc.coordinate(db, booking=b)
    assert out["status"] == "ok"
    assert out["provider"] == "ai"
    assert out["plan"] == "AI_PLAN"
    assert out["stats"]["members_count"] == 12
    assert out["stats"]["paid_members_count"] == 5
    assert out["stats"]["rooms_needed"] == 6
    assert len(out["activity_suggestions"]) >= 1


def test_remaining_allocation_math(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "x", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "gc-math")
    u = _user(db, t, "math@x.com")
    svc = _svc(db, t, capacity=2)
    b = _booking(db, t, u, svc=svc, guests=12, amount=12000)
    for i in range(12):
        _member(db, b, f"mm{i}@x.com", share=500, paid=(i < 8))
    out = gc.coordinate(db, booking=b)
    assert out["status"] == "ok"
    assert out["stats"]["suggested_per_unpaid"] == "1500.00"


def test_fallback_when_ai_fails(db, monkeypatch):
    from app.services.ai import service as ai_service
    def _boom(*a, **kw): raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)
    t = _tenant(db, "gc-fb")
    u = _user(db, t, "fb@x.com")
    svc = _svc(db, t)
    b = _booking(db, t, u, svc=svc, guests=12)
    for i in range(10):
        _member(db, b, f"fb{i}@x.com", share=1000)
    out = gc.coordinate(db, booking=b)
    assert out["status"] == "ok"
    assert out["provider"] == "fallback"
    assert "Group of 10" in out["plan"]
