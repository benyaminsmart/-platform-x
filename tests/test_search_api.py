"""Tests for /api/search endpoint."""
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


def _tenant(db, slug, cfg=None, status="active"):
    t = Tenant(slug=slug, name=f"Name-{slug}", tier="starter", status=status,
               config=cfg or {"type": "hotel", "rating": 4.5, "location": "Dubai, UAE"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, tenant, name="R", price=500, capacity=2):
    s = Service(tenant_id=tenant.id, type="room", name=name,
                price=Decimal(str(price)), currency="AED", capacity=capacity,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_empty(client):
    r = client.get("/api/search")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_returns_services(client, db):
    t = _tenant(db, "srch-a")
    _svc(db, t, name="Deluxe Room", price=800)
    body = client.get("/api/search").json()
    assert body["total"] == 1
    assert body["items"][0]["service_name"] == "Deluxe Room"
    assert body["items"][0]["category"] == "hotels"


def test_filter_category(client, db):
    t1 = _tenant(db, "sh", cfg={"type": "hotel"})
    t2 = _tenant(db, "sr", cfg={"type": "restaurant"})
    _svc(db, t1, name="H")
    _svc(db, t2, name="R")
    body = client.get("/api/search?category=hotels").json()
    assert body["total"] == 1


def test_filter_price(client, db):
    t = _tenant(db, "sp")
    _svc(db, t, name="Cheap", price=100)
    _svc(db, t, name="Expensive", price=2000)
    body = client.get("/api/search?max_price=300").json()
    assert body["total"] == 1
    assert body["items"][0]["service_name"] == "Cheap"


def test_sort(client, db):
    t = _tenant(db, "ss")
    _svc(db, t, name="A", price=900)
    _svc(db, t, name="B", price=100)
    body = client.get("/api/search?sort=price_asc").json()
    assert [i["service_name"] for i in body["items"]] == ["B", "A"]


def test_pagination(client, db):
    t = _tenant(db, "spag")
    for i in range(5):
        _svc(db, t, name=f"S{i}", price=100 + i)
    body = client.get("/api/search?page=1&page_size=2").json()
    assert body["total"] == 5
    assert len(body["items"]) == 2


def test_invalid_sort(client):
    assert client.get("/api/search?sort=bogus").status_code == 422


def test_guests_validation(client):
    assert client.get("/api/search?guests=0").status_code == 422
    assert client.get("/api/search?guests=999").status_code == 422


def test_availability(client, db):
    t = _tenant(db, "sav")
    s = _svc(db, t, name="OnlyRoom", capacity=1)
    u = User(tenant_id=t.id, email="u@x.com", password_hash=hash_password("Pass1234"),
             first_name="U", last_name="X", referral_code="U123", status="active")
    db.add(u); db.commit(); db.refresh(u)
    ci = date.today() + timedelta(days=10)
    co = date.today() + timedelta(days=15)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_id=s.id, service_name=s.name, check_in=ci, check_out=co, guests=1,
                amount=Decimal("500"), discount=Decimal("0"), total_amount=Decimal("500"),
                currency="AED", status="confirmed", payment_status="paid")
    db.add(b); db.commit()
    assert client.get(f"/api/search?check_in={ci}&check_out={co}").json()["total"] == 0
    ci2 = date.today() + timedelta(days=20)
    co2 = date.today() + timedelta(days=22)
    assert client.get(f"/api/search?check_in={ci2}&check_out={co2}").json()["total"] == 1
