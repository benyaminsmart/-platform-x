"""Tests for messages API (Phase 39, Step 5)."""
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


def _biz(db, t, email="owner@biz.test", role="owner"):
    u = User(tenant_id=t.id, email=email, password_hash=hash_password("OwnerPass123"),
             first_name="O", last_name="X", business_role=role, status="active",
             referral_code=email[:10].upper())
    db.add(u); db.commit(); db.refresh(u)
    return u


def _bk(db, t, u):
    ci = date.today() + timedelta(days=10)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_name="R", check_in=ci, check_out=ci + timedelta(days=2),
                guests=1, amount=Decimal("1000"), discount=Decimal("0"),
                total_amount=Decimal("1000"), currency="AED",
                status="confirmed", payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def _uh(u, t):
    tok = create_access_token(u.id, tenant_id=t.id)
    return {"Authorization": f"Bearer {tok}", "X-Tenant-Slug": t.slug}


def _bh(client, slug):
    r = client.post("/business/api/auth/login",
                    json={"email": "owner@biz.test", "password": "OwnerPass123"},
                    headers={"X-Tenant-Slug": slug})
    return {"Authorization": f"Bearer {r.json()['access_token']}", "X-Tenant-Slug": slug}


def test_user_requires_auth(client, db):
    t = _tenant(db, "msg-noauth")
    r = client.get("/messages/threads", headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 401


def test_user_threads_empty(client, db):
    t = _tenant(db, "msg-empty")
    u = _user(db, t)
    h = _uh(u, t)
    r = client.get("/messages/threads", headers=h)
    assert r.status_code == 200
    assert r.json() == []


def test_user_and_business_exchange(client, db):
    t = _tenant(db, "msg-ex")
    u = _user(db, t)
    _biz(db, t)
    b = _bk(db, t, u)

    uh = _uh(u, t)
    r = client.post(f"/messages/{b.id}", json={"body": "Hi, what time is checkin?"}, headers=uh)
    assert r.status_code == 201

    threads = client.get("/messages/threads", headers=uh).json()
    assert len(threads) == 1
    assert threads[0]["thread_id"] == b.id

    bh = _bh(client, t.slug)
    bthreads = client.get("/business/api/messages/threads", headers=bh).json()
    assert len(bthreads) == 1
    assert bthreads[0]["unread"] == 1

    r = client.post(f"/business/api/messages/{b.id}", json={"body": "Checkin is at 3pm"}, headers=bh)
    assert r.status_code == 201

    msgs = client.get(f"/messages/{b.id}", headers=uh).json()
    assert len(msgs) == 2


def test_user_cannot_access_others_thread(client, db):
    t = _tenant(db, "msg-other")
    u1 = _user(db, t, "u1@x.com")
    u2 = _user(db, t, "u2@x.com")
    b = _bk(db, t, u2)
    h = _uh(u1, t)
    r = client.get(f"/messages/{b.id}", headers=h)
    assert r.status_code == 404


def test_business_cross_tenant(client, db):
    a = _tenant(db, "msg-a")
    b_tenant = _tenant(db, "msg-b")
    ua = _user(db, a)
    _biz(db, a)
    bh = _bh(client, a.slug)
    other = _bk(db, b_tenant, ua)
    r = client.get(f"/business/api/messages/{other.id}", headers=bh)
    assert r.status_code == 404
