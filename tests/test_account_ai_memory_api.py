"""Tests for AI Trip Memory API (Phase 46, Step 2)."""
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User


def _tenant(db, slug, typ="hotel", location="Dubai"):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": typ, "rating": 4.5, "location": location})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="m@x.com"):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db, t, u, amount=500):
    ci = date.today() - timedelta(days=5)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_name="Room", check_in=ci,
                check_out=ci + timedelta(days=1), guests=2,
                amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency="AED",
                status="confirmed", payment_status="paid")
    db.add(b); db.commit()
    return b


def _login(client, email, password="Pass1234", tenant_slug=None):
    headers = {}
    if tenant_slug:
        headers["X-Tenant-Slug"] = tenant_slug
    r = client.post("/auth/login", json={"email": email, "password": password},
                    headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_memory_requires_auth(client: TestClient) -> None:
    r = client.get("/account/api/ai/memory")
    assert r.status_code == 401


def test_memory_empty(client: TestClient, db: Session) -> None:
    t = _tenant(db, "mem-empty")
    u = _user(db, t, "empty@x.com")
    token = _login(client, u.email, tenant_slug=t.slug)
    r = client.get("/account/api/ai/memory",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["profile"]["total_bookings"] == 0
    assert body["provider"] == "fallback"
    assert "No trips recorded" in body["recap"]


def test_memory_with_bookings(client: TestClient, db: Session) -> None:
    t = _tenant(db, "mem-full", typ="hotel", location="Dubai")
    u = _user(db, t, "full@x.com")
    _booking(db, t, u, 500)
    _booking(db, t, u, 700)
    token = _login(client, u.email, tenant_slug=t.slug)
    r = client.get("/account/api/ai/memory",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["profile"]["total_bookings"] == 2
    assert body["profile"]["favorite_category"] == "hotels"
    assert "Dubai" in body["profile"]["cities"]


def test_memory_invalid_language(client: TestClient, db: Session) -> None:
    t = _tenant(db, "mem-lang")
    u = _user(db, t, "lang@x.com")
    token = _login(client, u.email, tenant_slug=t.slug)
    r = client.get("/account/api/ai/memory?language=xx",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422
