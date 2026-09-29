"""Tests for printable business report (Phase 34, Step 3)."""
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import hash_password


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"Hotel {slug}", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai, UAE"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _biz(db, t, email="owner@biz.test"):
    u = User(tenant_id=t.id, email=email, password_hash=hash_password("OwnerPass123"),
             first_name="O", last_name="X", business_role="owner", status="active",
             referral_code=email[:10].upper())
    db.add(u); db.commit(); db.refresh(u)
    return u


def _user(db, t, email="g@x.com"):
    u = User(tenant_id=t.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _bk(db, t, u, days_ago=5, amount=500):
    ci = date.today() - timedelta(days=days_ago)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_name="Deluxe", check_in=ci, check_out=ci + timedelta(days=1),
                guests=2, amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency="AED",
                status="confirmed", payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def _login(client, slug):
    r = client.post("/business/api/auth/login",
                    json={"email": "owner@biz.test", "password": "OwnerPass123"},
                    headers={"X-Tenant-Slug": slug})
    return {"Authorization": f"Bearer {r.json()['access_token']}", "X-Tenant-Slug": slug}


def test_report_requires_auth(client, db):
    t = _tenant(db, "rep-noauth")
    r = client.get("/business/reports/print", headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 401


def test_report_renders(client, db):
    t = _tenant(db, "rep-ok")
    _biz(db, t)
    u = _user(db, t)
    _bk(db, t, u, days_ago=3, amount=800)
    h = _login(client, t.slug)
    r = client.get("/business/reports/print?days=30", headers=h)
    assert r.status_code == 200
    html = r.text
    assert "Business report" in html
    assert "Hotel rep-ok" in html
    assert "Total bookings" in html
    assert "Revenue" in html
    assert "800" in html
    assert "window.print()" in html


def test_report_empty(client, db):
    t = _tenant(db, "rep-empty")
    _biz(db, t)
    h = _login(client, t.slug)
    r = client.get("/business/reports/print?days=30", headers=h)
    assert r.status_code == 200
    assert "No data for this period." in r.text
