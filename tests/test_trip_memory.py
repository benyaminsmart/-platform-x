"""Tests for AI Trip Memory (Phase 46, Step 1)."""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai import trip_memory as tm


def _tenant(db, slug, typ="hotel", location="Dubai", name=None):
    t = Tenant(slug=slug, name=name or f"N-{slug}", tier="starter", status="active",
               config={"type": typ, "rating": 4.5, "location": location})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="tm@x.com"):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db, t, u, *, amount=500, guests=2, days_ago=5, status="confirmed", cur="AED"):
    ci = date.today() - timedelta(days=days_ago)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_name="Room", check_in=ci,
                check_out=ci + timedelta(days=1), guests=guests,
                amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency=cur,
                status=status, payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_invalid_language(db):
    t = _tenant(db, "tm-lang")
    u = _user(db, t)
    import pytest
    with pytest.raises(ValueError):
        tm.summarize(db, user_id=u.id, language="xx")


def test_empty_profile(db):
    t = _tenant(db, "tm-empty")
    u = _user(db, t, "empty@x.com")
    out = tm.summarize(db, user_id=u.id)
    assert out["profile"]["total_bookings"] == 0
    assert out["provider"] == "fallback"
    assert "No trips recorded" in out["recap"]


def test_profile_aggregation(db):
    t = _tenant(db, "tm-agg", typ="hotel", location="Dubai")
    u = _user(db, t, "agg@x.com")
    _booking(db, t, u, amount=600, guests=2)
    _booking(db, t, u, amount=400, guests=4)
    _booking(db, t, u, amount=999, status="cancelled")  # excluded
    prof = tm.build_profile(db, u.id)
    assert prof["total_bookings"] == 2
    assert prof["favorite_category"] == "hotels"
    assert "Dubai" in prof["cities"]
    assert prof["avg_price"] == "500.00"
    assert prof["currency"] == "AED"
    assert prof["avg_guests"] == 3.0
    assert len(prof["preferred_months"]) >= 1


def test_summarize_uses_ai(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI_RECAP", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "tm-ai", typ="restaurant", location="Abu Dhabi")
    u = _user(db, t, "ai@x.com")
    _booking(db, t, u, amount=200)
    out = tm.summarize(db, user_id=u.id)
    assert out["provider"] == "ai"
    assert out["recap"] == "AI_RECAP"
    assert out["profile"]["favorite_category"] == "restaurants"


def test_summarize_fallback_when_ai_fails(db, monkeypatch):
    from app.services.ai import service as ai_service
    def _boom(*a, **kw): raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)
    t = _tenant(db, "tm-fb")
    u = _user(db, t, "fb@x.com")
    _booking(db, t, u, amount=100)
    out = tm.summarize(db, user_id=u.id)
    assert out["provider"] == "fallback"
    assert "trips so far" in out["recap"]


def test_top_tenants_ordering(db):
    t1 = _tenant(db, "tm-t1", name="Alpha Hotel")
    t2 = _tenant(db, "tm-t2", name="Beta Hotel")
    u = _user(db, t1, "top@x.com")
    _booking(db, t1, u)
    _booking(db, t1, u)
    _booking(db, t2, u)
    prof = tm.build_profile(db, u.id)
    assert prof["top_tenants"][0]["name"] == "Alpha Hotel"
    assert prof["top_tenants"][0]["count"] == 2
