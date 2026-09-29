"""Tests for exports API (Phase 34, Step 1)."""
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import hash_password


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _biz(db, tenant, email="owner@biz.test", role="owner"):
    u = User(tenant_id=tenant.id, email=email, password_hash=hash_password("OwnerPass123"),
             first_name="O", last_name="X", business_role=role, status="active",
             referral_code=email[:10].upper())
    db.add(u); db.commit(); db.refresh(u)
    return u


def _user(db, tenant, email="u@x.com"):
    u = User(tenant_id=tenant.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="U", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _bk(db, tenant, user, days_ago=5, amount=500):
    ci = date.today() - timedelta(days=days_ago)
    b = Booking(tenant_id=tenant.id, user_id=user.id, booking_type="room",
                service_name="R", check_in=ci, check_out=ci + timedelta(days=1),
                guests=1, amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency="AED",
                status="confirmed", payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def _login(client, slug, email="owner@biz.test"):
    r = client.post("/business/api/auth/login",
                    json={"email": email, "password": "OwnerPass123"},
                    headers={"X-Tenant-Slug": slug})
    return {"Authorization": f"Bearer {r.json()['access_token']}", "X-Tenant-Slug": slug}


def test_bookings_csv_requires_auth(client, db):
    t = _tenant(db, "exp-noauth")
    r = client.get("/business/api/exports/bookings.csv", headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 401


def test_bookings_csv_staff_forbidden(client, db):
    t = _tenant(db, "exp-staff")
    _biz(db, t, email="staff@biz.test", role="staff")
    h = _login(client, t.slug, "staff@biz.test")
    r = client.get("/business/api/exports/bookings.csv", headers=h)
    assert r.status_code == 403


def test_bookings_csv_ok(client, db):
    t = _tenant(db, "exp-bk")
    _biz(db, t)
    u = _user(db, t)
    _bk(db, t, u, days_ago=5, amount=500)
    _bk(db, t, u, days_ago=10, amount=1000)
    h = _login(client, t.slug)
    r = client.get("/business/api/exports/bookings.csv?days=30", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers.get("content-disposition", "")
    body = r.text
    assert "booking_id" in body
    assert "500" in body


def test_customers_csv(client, db):
    t = _tenant(db, "exp-cust")
    _biz(db, t)
    u = _user(db, t, "c1@x.com")
    _bk(db, t, u)
    h = _login(client, t.slug)
    r = client.get("/business/api/exports/customers.csv", headers=h)
    assert r.status_code == 200
    assert "c1@x.com" in r.text


def test_revenue_csv(client, db):
    t = _tenant(db, "exp-rev")
    _biz(db, t)
    u = _user(db, t, "r@x.com")
    _bk(db, t, u, days_ago=3, amount=800)
    h = _login(client, t.slug)
    r = client.get("/business/api/exports/revenue.csv?days=30", headers=h)
    assert r.status_code == 200
    assert "revenue" in r.text


def test_cross_tenant_isolation(client, db):
    a = _tenant(db, "exp-a")
    b = _tenant(db, "exp-b")
    _biz(db, a)
    ub = _user(db, b, "ub@x.com")
    _bk(db, b, ub, days_ago=5, amount=9999)
    h = _login(client, a.slug)
    r = client.get("/business/api/exports/bookings.csv?days=30", headers=h)
    assert r.status_code == 200
    assert "9999" not in r.text
