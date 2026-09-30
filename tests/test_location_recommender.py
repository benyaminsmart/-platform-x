"""Tests for AI Location Recommender (Phase 45, Step 1)."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.attraction import Attraction
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai import location_recommender as lr


def _tenant(db, slug, typ="hotel", rating=4.5, lat=25.20, lng=55.27):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": typ, "rating": rating, "location": "Dubai",
                       "coordinates": {"lat": lat, "lng": lng}})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, price=500, capacity=2):
    s = Service(tenant_id=t.id, type="room", name="Room",
                price=Decimal(str(price)), currency="AED", capacity=capacity,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _user(db, t, email="g@x.com"):
    u = User(tenant_id=t.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _attraction(db, name, lat=25.20, lng=55.27, category="landmark"):
    a = Attraction(name=name, category=category, lat=lat, lng=lng, city="Dubai")
    db.add(a); db.commit(); db.refresh(a)
    return a


def test_invalid_language(db):
    t = _tenant(db, "lr-lang")
    with pytest.raises(ValueError):
        lr.recommend(db, lat=25.20, lng=55.27, language="xx")


def test_empty_area_returns_fallback(db, monkeypatch):
    from app.services.ai import service as ai_service
    def _boom(*a, **kw): raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)
    out = lr.recommend(db, lat=0.0, lng=0.0, radius_km=1)
    assert out["attractions"] == []
    assert out["services"] == []
    assert out["provider"] == "fallback"


def test_returns_attractions_and_services(db, monkeypatch):
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat", lambda *a, **kw: {"content": "AI_ADVICE", "provider": "x", "model": "x", "tokens_used": 0})
    t = _tenant(db, "lr-full", lat=25.20, lng=55.27)
    _svc(db, t, price=500)
    _attraction(db, "Attraction A", lat=25.20, lng=55.27)
    out = lr.recommend(db, lat=25.20, lng=55.27, radius_km=5)
    assert out["provider"] == "ai"
    assert out["advice"] == "AI_ADVICE"
    assert len(out["attractions"]) >= 1
    assert len(out["services"]) >= 1


def test_fallback_when_ai_fails(db, monkeypatch):
    from app.services.ai import service as ai_service
    def _boom(*a, **kw): raise RuntimeError("fail")
    monkeypatch.setattr(ai_service, "chat", _boom)
    t = _tenant(db, "lr-fb")
    _svc(db, t)
    _attraction(db, "A")
    out = lr.recommend(db, lat=25.20, lng=55.27, radius_km=5)
    assert out["provider"] == "fallback"


def test_user_pref_category(db, monkeypatch):
    t_rest = _tenant(db, "lr-rest", typ="restaurant", lat=25.20, lng=55.27)
    u = _user(db, t_rest, "u@x.com")
    ci = date.today() - timedelta(days=5)
    b = Booking(tenant_id=t_rest.id, user_id=u.id, booking_type="table",
                service_name="R", check_in=ci, check_out=ci + timedelta(days=1),
                guests=1, amount=Decimal("100"), discount=Decimal("0"),
                total_amount=Decimal("100"), currency="AED",
                status="confirmed", payment_status="paid")
    db.add(b); db.commit()
    pref = lr._user_pref_category(db, u.id)
    assert pref == "restaurants"
