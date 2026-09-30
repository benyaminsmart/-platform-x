"""Tests for Waitlist API (Phase 48, Step 2)."""
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
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, price=500, capacity=1):
    s = Service(tenant_id=t.id, type="room", name="Room",
                price=Decimal(str(price)), currency="AED", capacity=capacity,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _user(db, t, email):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db, t, u, svc, ci, co):
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_id=svc.id, service_name=svc.name,
                check_in=ci, check_out=co, guests=1,
                amount=Decimal("500"), discount=Decimal("0"),
                total_amount=Decimal("500"), currency="AED",
                status="confirmed", payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def _login(client, slug, email):
    r = client.post("/auth/login", json={"email": email, "password": "Pass1234"},
                    headers={"X-Tenant-Slug": slug})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_join_requires_auth(client: TestClient) -> None:
    r = client.post("/me/waitlist", json={"service_id": "x",
                    "check_in": "2030-01-01", "check_out": "2030-01-02"})
    assert r.status_code == 401


def test_join_not_full(client: TestClient, db: Session) -> None:
    t = _tenant(db, "wl-api-nf")
    s = _svc(db, t, capacity=5)
    u = _user(db, t, "nf@x.com")
    token = _login(client, t.slug, u.email)
    r = client.post("/me/waitlist", json={
        "service_id": s.id, "check_in": "2030-01-01", "check_out": "2030-01-03",
    }, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 409


def test_join_ok_list_delete(client: TestClient, db: Session) -> None:
    t = _tenant(db, "wl-api-ok")
    s = _svc(db, t, capacity=1)
    u1 = _user(db, t, "u1@x.com")
    u2 = _user(db, t, "u2@x.com")
    ci = date(2030, 1, 1)
    co = date(2030, 1, 3)
    _booking(db, t, u1, s, ci, co)

    token = _login(client, t.slug, u2.email)
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/me/waitlist", json={
        "service_id": s.id, "check_in": ci.isoformat(), "check_out": co.isoformat(),
    }, headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["service_id"] == s.id
    assert body["position"] == 1
    entry_id = body["id"]

    r = client.get("/me/waitlist", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.delete(f"/me/waitlist/{entry_id}", headers=h)
    assert r.status_code == 200
    assert r.json()["deleted"] is True


def test_join_bad_dates(client: TestClient, db: Session) -> None:
    t = _tenant(db, "wl-api-bd")
    s = _svc(db, t, capacity=1)
    u = _user(db, t, "bd@x.com")
    token = _login(client, t.slug, u.email)
    r = client.post("/me/waitlist", json={
        "service_id": s.id, "check_in": "2030-01-05", "check_out": "2030-01-05",
    }, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422


def test_check_and_notify(client: TestClient, db: Session) -> None:
    t = _tenant(db, "wl-api-check")
    s = _svc(db, t, capacity=1)
    u1 = _user(db, t, "c1@x.com")
    u2 = _user(db, t, "c2@x.com")
    ci = date(2030, 1, 1)
    co = date(2030, 1, 3)
    b = _booking(db, t, u1, s, ci, co)

    token = _login(client, t.slug, u2.email)
    h = {"Authorization": f"Bearer {token}"}
    client.post("/me/waitlist", json={
        "service_id": s.id, "check_in": ci.isoformat(), "check_out": co.isoformat(),
    }, headers=h)

    # Still full → not notified
    r = client.post("/me/waitlist/check", json={
        "service_id": s.id, "check_in": ci.isoformat(), "check_out": co.isoformat(),
    }, headers=h)
    assert r.status_code == 200
    assert r.json()["notified"] is False

    # Cancel booking → notify first FIFO
    b.status = "cancelled"
    db.commit()
    r = client.post("/me/waitlist/check", json={
        "service_id": s.id, "check_in": ci.isoformat(), "check_out": co.isoformat(),
    }, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["notified"] is True
    assert body["user_id"] == u2.id


def test_cross_user_isolation(client: TestClient, db: Session) -> None:
    t = _tenant(db, "wl-api-iso")
    s = _svc(db, t, capacity=1)
    u1 = _user(db, t, "i1@x.com")
    u2 = _user(db, t, "i2@x.com")
    u3 = _user(db, t, "i3@x.com")
    ci = date(2030, 1, 1)
    co = date(2030, 1, 3)
    _booking(db, t, u1, s, ci, co)

    tok2 = _login(client, t.slug, u2.email)
    tok3 = _login(client, t.slug, u3.email)
    r = client.post("/me/waitlist", json={
        "service_id": s.id, "check_in": ci.isoformat(), "check_out": co.isoformat(),
    }, headers={"Authorization": f"Bearer {tok2}"})
    assert r.status_code == 201
    entry_id = r.json()["id"]

    r = client.delete(f"/me/waitlist/{entry_id}",
                      headers={"Authorization": f"Bearer {tok3}"})
    assert r.status_code == 404

    r = client.get("/me/waitlist", headers={"Authorization": f"Bearer {tok3}"})
    assert r.json() == []
