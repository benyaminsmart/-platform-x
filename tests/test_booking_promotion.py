"""Tests for promotion code integration with booking (Phase 38, Step 4)."""
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password, create_access_token
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import promotion_service


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="g@x.com"):
    u = User(tenant_id=t.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _svc(db, t, price=500):
    s = Service(tenant_id=t.id, type="room", name="R",
                price=Decimal(str(price)), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _h(u, t):
    tok = create_access_token(u.id, tenant_id=t.id)
    return {"Authorization": f"Bearer {tok}", "X-Tenant-Slug": t.slug}


def test_booking_with_promotion_percent(client, db):
    t = _tenant(db, "bp-pct")
    u = _user(db, t)
    s = _svc(db, t, price=500)
    promotion_service.create_promotion(db, t, code="save10", name="Save 10",
                                       discount_type="percent", discount_value=10)
    ci = (date.today() + timedelta(days=10)).isoformat()
    r = client.post("/bookings",
                    json={"booking_type": "room", "service_id": s.id, "service_name": "R",
                          "check_in": ci, "guests": 1, "amount": "500",
                          "promotion_code": "SAVE10"},
                    headers=_h(u, t))
    assert r.status_code == 201, r.text
    assert r.json()["total_amount"] == "450.00"


def test_booking_with_promotion_fixed(client, db):
    t = _tenant(db, "bp-fix")
    u = _user(db, t)
    s = _svc(db, t, price=500)
    promotion_service.create_promotion(db, t, code="minus50", name="Minus 50",
                                       discount_type="fixed", discount_value=50)
    ci = (date.today() + timedelta(days=10)).isoformat()
    r = client.post("/bookings",
                    json={"booking_type": "room", "service_id": s.id, "service_name": "R",
                          "check_in": ci, "guests": 1, "amount": "500",
                          "promotion_code": "minus50"},
                    headers=_h(u, t))
    assert r.status_code == 201
    assert r.json()["total_amount"] == "450.00"


def test_booking_invalid_code_400(client, db):
    t = _tenant(db, "bp-bad")
    u = _user(db, t)
    s = _svc(db, t)
    ci = (date.today() + timedelta(days=10)).isoformat()
    r = client.post("/bookings",
                    json={"booking_type": "room", "service_id": s.id, "service_name": "R",
                          "check_in": ci, "guests": 1, "amount": "500",
                          "promotion_code": "MISSING"},
                    headers=_h(u, t))
    assert r.status_code == 400


def test_booking_increments_usage(client, db):
    t = _tenant(db, "bp-inc")
    u = _user(db, t)
    s = _svc(db, t, price=500)
    p = promotion_service.create_promotion(db, t, code="x", name="X",
                                           discount_type="percent", discount_value=5)
    assert p.used_count == 0
    ci = (date.today() + timedelta(days=10)).isoformat()
    r = client.post("/bookings",
                    json={"booking_type": "room", "service_id": s.id, "service_name": "R",
                          "check_in": ci, "guests": 1, "amount": "500",
                          "promotion_code": "x"},
                    headers=_h(u, t))
    assert r.status_code == 201
    db.refresh(p)
    assert p.used_count == 1


def test_booking_without_code(client, db):
    t = _tenant(db, "bp-none")
    u = _user(db, t)
    s = _svc(db, t, price=500)
    ci = (date.today() + timedelta(days=10)).isoformat()
    r = client.post("/bookings",
                    json={"booking_type": "room", "service_id": s.id, "service_name": "R",
                          "check_in": ci, "guests": 1, "amount": "500"},
                    headers=_h(u, t))
    assert r.status_code == 201
    assert r.json()["total_amount"] == "500.00"
