"""Tests for /api/availability (Phase 30, Step 4)."""
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, tenant, name="R", capacity=2):
    s = Service(tenant_id=tenant.id, type="room", name=name,
                price=Decimal("500"), currency="AED", capacity=capacity,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _booking(db, tenant, user, svc, ci, co):
    b = Booking(tenant_id=tenant.id, user_id=user.id, booking_type="room",
                service_id=svc.id, service_name=svc.name,
                check_in=ci, check_out=co, guests=1,
                amount=Decimal("500"), discount=Decimal("0"), total_amount=Decimal("500"),
                currency="AED", status="confirmed", payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_not_found(client):
    r = client.get("/api/availability/does-not-exist")
    assert r.status_code == 404


def test_empty_tenant(client, db):
    t = _tenant(db, "av-empty")
    r = client.get(f"/api/availability/{t.slug}?days=7")
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_slug"] == t.slug
    assert body["services"] == []


def test_with_service(client, db):
    t = _tenant(db, "av-svc")
    _svc(db, t, name="Room A", capacity=2)
    r = client.get(f"/api/availability/{t.slug}?days=7")
    body = r.json()
    assert len(body["services"]) == 1
    svc = body["services"][0]
    assert svc["service_name"] == "Room A"
    assert len(svc["days"]) == 7
    for day in svc["days"]:
        assert day["free"] == 2
        assert day["full"] is False


def test_full_day(client, db):
    t = _tenant(db, "av-full")
    s = _svc(db, t, capacity=1)
    u = User(tenant_id=t.id, email="u@x.com", password_hash=hash_password("Pass1234"),
             first_name="U", last_name="X", referral_code="U123", status="active")
    db.add(u); db.commit(); db.refresh(u)
    # Book days 5-8
    _booking(db, t, u, s, date.today() + timedelta(days=5), date.today() + timedelta(days=8))

    r = client.get(f"/api/availability/{t.slug}?days=10")
    body = r.json()
    days = {d["date"]: d for d in body["services"][0]["days"]}
    # days 5, 6, 7 should be full
    for offset in [5, 6, 7]:
        key = (date.today() + timedelta(days=offset)).isoformat()
        assert days[key]["full"] is True
        assert days[key]["free"] == 0
    # day 0 should be free
    k0 = date.today().isoformat()
    assert days[k0]["free"] == 1


def test_no_capacity_service(client, db):
    t = _tenant(db, "av-nocap")
    _svc(db, t, name="Menu", capacity=None)
    r = client.get(f"/api/availability/{t.slug}?days=3")
    body = r.json()
    for day in body["services"][0]["days"]:
        assert day["free"] is None
        assert day["full"] is False


def test_days_clamped(client, db):
    t = _tenant(db, "av-clamp")
    r1 = client.get(f"/api/availability/{t.slug}?days=1")
    assert r1.status_code == 200
    assert len(r1.json()["services"]) == 0  # no services
    r2 = client.get(f"/api/availability/{t.slug}?days=999")
    assert r2.status_code == 422
