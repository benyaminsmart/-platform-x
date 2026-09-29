"""Tests for group booking API (Phase 40, Step 3)."""
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import hash_password, create_access_token
from app.models.booking import Booking
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


def _booking(db, t, u, *, is_group=True, amount=1000):
    ci = date.today() + timedelta(days=10)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_name="R", check_in=ci, check_out=ci + timedelta(days=2),
                guests=1, amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency="AED",
                status="confirmed", payment_status="paid", is_group=is_group)
    db.add(b); db.commit(); db.refresh(b)
    return b


def _h(u, t):
    tok = create_access_token(u.id, tenant_id=t.id)
    return {"Authorization": f"Bearer {tok}", "X-Tenant-Slug": t.slug}


def test_requires_auth(client, db):
    t = _tenant(db, "grp-noauth")
    u = _user(db, t)
    b = _booking(db, t, u)
    r = client.get(f"/bookings/{b.id}/group", headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 401


def test_empty_group(client, db):
    t = _tenant(db, "grp-empty")
    u = _user(db, t)
    b = _booking(db, t, u)
    h = _h(u, t)
    r = client.get(f"/bookings/{b.id}/group", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["is_group"] is True
    assert body["members_count"] == 0


def test_add_and_list(client, db):
    t = _tenant(db, "grp-add")
    u = _user(db, t)
    b = _booking(db, t, u)
    h = _h(u, t)
    r = client.post(f"/bookings/{b.id}/group",
                    json={"name": "Ali", "email": "ali@x.com", "share_amount": 250},
                    headers=h)
    assert r.status_code == 201, r.text
    r2 = client.get(f"/bookings/{b.id}/group", headers=h)
    body = r2.json()
    assert body["members_count"] == 1
    assert body["shares_total"] == "250.00"


def test_not_group_rejected(client, db):
    t = _tenant(db, "grp-ng")
    u = _user(db, t)
    b = _booking(db, t, u, is_group=False)
    h = _h(u, t)
    r = client.post(f"/bookings/{b.id}/group",
                    json={"name": "A", "email": "a@x.com", "share_amount": 100},
                    headers=h)
    assert r.status_code == 400


def test_update_member(client, db):
    t = _tenant(db, "grp-upd")
    u = _user(db, t)
    b = _booking(db, t, u)
    h = _h(u, t)
    r = client.post(f"/bookings/{b.id}/group",
                    json={"name": "A", "email": "a@x.com", "share_amount": 100},
                    headers=h)
    mid = r.json()["id"]
    r = client.patch(f"/bookings/{b.id}/group/{mid}",
                     json={"paid": True, "share_amount": 300}, headers=h)
    assert r.status_code == 200
    assert r.json()["paid"] is True


def test_remove_member(client, db):
    t = _tenant(db, "grp-rm")
    u = _user(db, t)
    b = _booking(db, t, u)
    h = _h(u, t)
    r = client.post(f"/bookings/{b.id}/group",
                    json={"name": "A", "email": "a@x.com", "share_amount": 100},
                    headers=h)
    mid = r.json()["id"]
    r = client.delete(f"/bookings/{b.id}/group/{mid}", headers=h)
    assert r.status_code == 200
    assert client.get(f"/bookings/{b.id}/group", headers=h).json()["members_count"] == 0


def test_other_user_blocked(client, db):
    t = _tenant(db, "grp-xu")
    u1 = _user(db, t, "u1@x.com")
    u2 = _user(db, t, "u2@x.com")
    b = _booking(db, t, u2)
    h = _h(u1, t)
    r = client.get(f"/bookings/{b.id}/group", headers=h)
    assert r.status_code == 404


def test_over_allocation_rejected(client, db):
    t = _tenant(db, "grp-over")
    u = _user(db, t)
    b = _booking(db, t, u, amount=500)
    h = _h(u, t)
    client.post(f"/bookings/{b.id}/group",
                json={"name": "A", "email": "a@x.com", "share_amount": 400}, headers=h)
    r = client.post(f"/bookings/{b.id}/group",
                    json={"name": "B", "email": "b@x.com", "share_amount": 200}, headers=h)
    assert r.status_code == 400
