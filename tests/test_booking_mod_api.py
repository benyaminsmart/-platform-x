"""Tests for booking modification API (Phase 35, Step 2)."""
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import hash_password, create_access_token


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="u@x.com"):
    u = User(tenant_id=t.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="U", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _svc(db, t, price=500, capacity=2):
    s = Service(tenant_id=t.id, type="room", name="R",
                price=Decimal(str(price)), currency="AED", capacity=capacity,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _bk(db, t, u, s, offset=10, nights=2, amount=1000, status="confirmed"):
    ci = date.today() + timedelta(days=offset)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_id=s.id, service_name=s.name,
                check_in=ci, check_out=ci + timedelta(days=nights),
                guests=1, amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency="AED",
                status=status, payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def _h(u, t):
    tok = create_access_token(u.id, tenant_id=t.id)
    return {"Authorization": f"Bearer {tok}", "X-Tenant-Slug": t.slug}


def test_preview_requires_auth(client, db):
    t = _tenant(db, "bm-noauth")
    u = _user(db, t)
    s = _svc(db, t)
    b = _bk(db, t, u, s)
    r = client.get(f"/bookings/{b.id}/modify-preview?new_check_in=2026-12-01",
                   headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 401


def test_preview_ok(client, db):
    t = _tenant(db, "bm-ok")
    u = _user(db, t)
    s = _svc(db, t, price=500)
    b = _bk(db, t, u, s, offset=10, nights=2, amount=1000)
    new_ci = (date.today() + timedelta(days=30)).isoformat()
    new_co = (date.today() + timedelta(days=33)).isoformat()
    r = client.get(f"/bookings/{b.id}/modify-preview?new_check_in={new_ci}&new_check_out={new_co}", headers=_h(u, t))
    assert r.status_code == 200
    body = r.json()
    assert body["can_modify"] is True
    assert body["delta_amount"] == "500.00"
    assert body["new_total"] == "1500.00"


def test_modify_ok(client, db):
    t = _tenant(db, "bm-mod")
    u = _user(db, t)
    s = _svc(db, t, price=500)
    b = _bk(db, t, u, s, offset=10, nights=2, amount=1000)
    new_ci = (date.today() + timedelta(days=30)).isoformat()
    new_co = (date.today() + timedelta(days=32)).isoformat()
    r = client.post(f"/bookings/{b.id}/modify",
                    json={"new_check_in": new_ci, "new_check_out": new_co},
                    headers=_h(u, t))
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    db.refresh(b)
    assert str(b.check_in) == new_ci


def test_modify_not_found(client, db):
    t = _tenant(db, "bm-nf")
    u = _user(db, t)
    r = client.post("/bookings/bogus/modify",
                    json={"new_check_in": (date.today() + timedelta(days=10)).isoformat()},
                    headers=_h(u, t))
    assert r.status_code == 404


def test_modify_other_user_blocked(client, db):
    t = _tenant(db, "bm-xu")
    u1 = _user(db, t, "u1@x.com")
    u2 = _user(db, t, "u2@x.com")
    s = _svc(db, t)
    b = _bk(db, t, u2, s, offset=10)
    r = client.post(f"/bookings/{b.id}/modify",
                    json={"new_check_in": (date.today() + timedelta(days=30)).isoformat()},
                    headers=_h(u1, t))
    assert r.status_code == 404
