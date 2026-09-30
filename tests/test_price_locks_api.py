"""Tests for Price Locks API (Phase 47, Step 2)."""
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


def _svc(db, t, price=500):
    s = Service(tenant_id=t.id, type="room", name="Room",
                price=Decimal(str(price)), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _user(db, t, email="plapi@x.com"):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _login(client, slug, email):
    r = client.post("/auth/login", json={"email": email, "password": "Pass1234"},
                    headers={"X-Tenant-Slug": slug})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_create_requires_auth(client: TestClient) -> None:
    r = client.post("/me/price-locks", json={"service_id": "x"})
    assert r.status_code == 401


def test_create_list_delete(client: TestClient, db: Session) -> None:
    t = _tenant(db, "pl-api-1")
    s = _svc(db, t, price=500)
    u = _user(db, t)
    token = _login(client, t.slug, u.email)
    h = {"Authorization": f"Bearer {token}"}

    r = client.post("/me/price-locks", json={"service_id": s.id}, headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["service_id"] == s.id
    assert body["locked_price"] == 500.0
    assert body["active"] is True
    lock_id = body["id"]

    r = client.get("/me/price-locks", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.delete(f"/me/price-locks/{lock_id}", headers=h)
    assert r.status_code == 200
    assert r.json()["deleted"] is True

    r = client.get("/me/price-locks", headers=h)
    assert r.status_code == 200
    assert r.json() == []


def test_create_not_found(client: TestClient, db: Session) -> None:
    t = _tenant(db, "pl-api-nf")
    u = _user(db, t, "nf@x.com")
    token = _login(client, t.slug, u.email)
    r = client.post("/me/price-locks", json={"service_id": "does-not-exist"},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_create_bad_window(client: TestClient, db: Session) -> None:
    t = _tenant(db, "pl-api-bw")
    s = _svc(db, t)
    u = _user(db, t, "bw@x.com")
    token = _login(client, t.slug, u.email)
    r = client.post("/me/price-locks",
                    json={"service_id": s.id, "window_hours": 999},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422


def test_consume_lock(client: TestClient, db: Session) -> None:
    t = _tenant(db, "pl-api-consume")
    s = _svc(db, t, price=500)
    u = _user(db, t, "consume@x.com")
    ci = date.today() + timedelta(days=10)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_id=s.id, service_name=s.name,
                check_in=ci, check_out=ci + timedelta(days=1), guests=1,
                amount=Decimal("500"), discount=Decimal("0"),
                total_amount=Decimal("500"), currency="AED",
                status="pending", payment_status="pending")
    db.add(b); db.commit(); db.refresh(b)
    token = _login(client, t.slug, u.email)
    h = {"Authorization": f"Bearer {token}"}

    r = client.post("/me/price-locks", json={"service_id": s.id}, headers=h)
    assert r.status_code == 201

    r = client.post("/me/price-locks/consume",
                    json={"service_id": s.id, "booking_id": b.id}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["locked_price"] == 500.0
    assert r.json()["status"] == "ok"

    r = client.post("/me/price-locks/consume",
                    json={"service_id": s.id, "booking_id": b.id}, headers=h)
    assert r.status_code == 409


def test_consume_not_found(client: TestClient, db: Session) -> None:
    t = _tenant(db, "pl-api-cnf")
    u = _user(db, t, "cnf@x.com")
    token = _login(client, t.slug, u.email)
    r = client.post("/me/price-locks/consume",
                    json={"service_id": "x", "booking_id": "y"},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_cross_user_isolation(client: TestClient, db: Session) -> None:
    t = _tenant(db, "pl-api-iso")
    s = _svc(db, t)
    u1 = _user(db, t, "u1@x.com")
    u2 = _user(db, t, "u2@x.com")
    tok1 = _login(client, t.slug, u1.email)
    tok2 = _login(client, t.slug, u2.email)

    r = client.post("/me/price-locks", json={"service_id": s.id},
                    headers={"Authorization": f"Bearer {tok1}"})
    assert r.status_code == 201
    lock_id = r.json()["id"]

    r = client.delete(f"/me/price-locks/{lock_id}",
                      headers={"Authorization": f"Bearer {tok2}"})
    assert r.status_code == 404

    r = client.get("/me/price-locks", headers={"Authorization": f"Bearer {tok2}"})
    assert r.json() == []
