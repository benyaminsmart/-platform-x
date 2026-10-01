"""Tests for AI Group Coordinator API (Phase 59, Step 2)."""
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.group_member import GroupMember
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="g@x.com"):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _svc(db, t):
    s = Service(tenant_id=t.id, type="room", name="Room",
                price=Decimal("500"), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _booking(db, t, u, svc, is_group=True, guests=12):
    ci = date.today() + timedelta(days=30)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_id=svc.id, service_name="Room", check_in=ci,
                check_out=ci + timedelta(days=2), guests=guests,
                amount=Decimal("12000"), discount=Decimal("0"),
                total_amount=Decimal("12000"), currency="AED",
                status="confirmed", payment_status="paid", is_group=is_group)
    db.add(b); db.commit(); db.refresh(b)
    return b


def _member(db, booking, email):
    m = GroupMember(tenant_id=booking.tenant_id, booking_id=booking.id,
                    name=email.split("@")[0], email=email,
                    share_amount=Decimal("1000"), paid=True)
    db.add(m); db.commit()
    return m


def _login(client, slug, email):
    r = client.post("/auth/login", json={"email": email, "password": "Pass1234"},
                    headers={"X-Tenant-Slug": slug})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_coordinate_requires_auth(client: TestClient) -> None:
    r = client.post("/bookings/x/group/coordinate")
    assert r.status_code == 401


def test_coordinate_ok(client: TestClient, db: Session, monkeypatch) -> None:
    from app.services.ai import service as ai_service
    monkeypatch.setattr(ai_service, "chat",
                        lambda *a, **kw: {"content": "AI_PLAN", "provider": "x",
                                          "model": "x", "tokens_used": 0})
    t = _tenant(db, "gca-ok")
    u = _user(db, t)
    svc = _svc(db, t)
    b = _booking(db, t, u, svc)
    for i in range(11):
        _member(db, b, f"m{i}@x.com")
    token = _login(client, t.slug, u.email)
    r = client.post(f"/bookings/{b.id}/group/coordinate",
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["plan"] == "AI_PLAN"
    assert body["stats"]["members_count"] == 11


def test_coordinate_not_found(client: TestClient, db: Session) -> None:
    t = _tenant(db, "gca-nf")
    u = _user(db, t, "nf@x.com")
    token = _login(client, t.slug, u.email)
    r = client.post("/bookings/missing/group/coordinate",
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_coordinate_not_group(client: TestClient, db: Session) -> None:
    t = _tenant(db, "gca-ng")
    u = _user(db, t, "ng@x.com")
    svc = _svc(db, t)
    b = _booking(db, t, u, svc, is_group=False)
    token = _login(client, t.slug, u.email)
    r = client.post(f"/bookings/{b.id}/group/coordinate",
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["status"] == "not_group"


def test_coordinate_invalid_language(client: TestClient, db: Session) -> None:
    t = _tenant(db, "gca-lang")
    u = _user(db, t, "lang@x.com")
    svc = _svc(db, t)
    b = _booking(db, t, u, svc)
    token = _login(client, t.slug, u.email)
    r = client.post(f"/bookings/{b.id}/group/coordinate?language=xx",
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422


def test_coordinate_cross_user_isolation(client: TestClient, db: Session) -> None:
    t = _tenant(db, "gca-iso")
    u1 = _user(db, t, "u1@x.com")
    u2 = _user(db, t, "u2@x.com")
    svc = _svc(db, t)
    b = _booking(db, t, u1, svc)
    token2 = _login(client, t.slug, u2.email)
    r = client.post(f"/bookings/{b.id}/group/coordinate",
                    headers={"Authorization": f"Bearer {token2}"})
    assert r.status_code == 404
