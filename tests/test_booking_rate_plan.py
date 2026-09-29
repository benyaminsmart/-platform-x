"""Tests for rate plan integration with booking (Phase 37, Step 3)."""
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password, create_access_token
from app.models.rate_plan import RatePlan
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


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


def _plan(db, t, s, code="bb", modifier=15, mtype="percent"):
    rp = RatePlan(tenant_id=t.id, service_id=s.id, name=code.upper(), code=code,
                  price_modifier_type=mtype, price_modifier_value=Decimal(str(modifier)),
                  meal_plan="breakfast", refundable=True, active=True)
    db.add(rp); db.commit(); db.refresh(rp)
    return rp


def _h(u, t):
    tok = create_access_token(u.id, tenant_id=t.id)
    return {"Authorization": f"Bearer {tok}", "X-Tenant-Slug": t.slug}


def test_booking_with_rate_plan_percent(client, db):
    t = _tenant(db, "brp-pct")
    u = _user(db, t)
    s = _svc(db, t, price=500)
    p = _plan(db, t, s, code="bb", modifier=15, mtype="percent")
    ci = (date.today() + timedelta(days=10)).isoformat()
    co = (date.today() + timedelta(days=12)).isoformat()
    r = client.post("/bookings",
                    json={"booking_type": "room", "service_id": s.id, "service_name": "R",
                          "check_in": ci, "check_out": co, "guests": 1,
                          "amount": "500", "rate_plan_id": p.id},
                    headers=_h(u, t))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["rate_plan_id"] == p.id
    assert body["rate_plan_code"] == "bb"
    assert body["total_amount"] == "575.00"


def test_booking_with_rate_plan_fixed(client, db):
    t = _tenant(db, "brp-fix")
    u = _user(db, t)
    s = _svc(db, t, price=500)
    p = _plan(db, t, s, code="plus50", modifier=50, mtype="fixed")
    ci = (date.today() + timedelta(days=10)).isoformat()
    co = (date.today() + timedelta(days=12)).isoformat()
    r = client.post("/bookings",
                    json={"booking_type": "room", "service_id": s.id, "service_name": "R",
                          "check_in": ci, "check_out": co, "guests": 1,
                          "amount": "999", "rate_plan_id": p.id},
                    headers=_h(u, t))
    assert r.status_code == 201
    assert r.json()["total_amount"] == "550.00"


def test_booking_invalid_rate_plan(client, db):
    t = _tenant(db, "brp-bad")
    u = _user(db, t)
    s = _svc(db, t)
    ci = (date.today() + timedelta(days=10)).isoformat()
    r = client.post("/bookings",
                    json={"booking_type": "room", "service_id": s.id, "service_name": "R",
                          "check_in": ci, "guests": 1, "amount": "500",
                          "rate_plan_id": "bogus"},
                    headers=_h(u, t))
    assert r.status_code == 400


def test_booking_without_rate_plan(client, db):
    t = _tenant(db, "brp-none")
    u = _user(db, t)
    s = _svc(db, t, price=500)
    ci = (date.today() + timedelta(days=10)).isoformat()
    r = client.post("/bookings",
                    json={"booking_type": "room", "service_id": s.id, "service_name": "R",
                          "check_in": ci, "guests": 1, "amount": "500"},
                    headers=_h(u, t))
    assert r.status_code == 201
    assert r.json()["total_amount"] == "500.00"
