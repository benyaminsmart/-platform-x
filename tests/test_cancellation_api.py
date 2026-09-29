"""Tests for Cancellation API (Phase 30, Step 5b)."""
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.booking import Booking
from app.models.tenant import Tenant


def _tenant(db, slug="cap"):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _login_guest(client, tenant, email):
    r = client.post(
        "/auth/register",
        json={"email": email, "password": "GuestPass123", "first_name": "G", "last_name": "X"},
        headers={"X-Tenant-Slug": tenant.slug},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}", "X-Tenant-Slug": tenant.slug}


def _booking_for(db, tenant, email, offset=10, amount=1000, status="confirmed"):
    from app.models.user import User
    u = db.query(User).filter(User.tenant_id == tenant.id, User.email == email).first()
    ci = date.today() + timedelta(days=offset)
    b = Booking(tenant_id=tenant.id, user_id=u.id, booking_type="room",
                service_name="R", check_in=ci, check_out=ci + timedelta(days=1),
                guests=1, amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency="AED",
                status=status, payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_preview_requires_auth(client, db):
    t = _tenant(db, "cap-noauth")
    r = client.get(f"/bookings/xxx/refund-preview", headers={"X-Tenant-Slug": t.slug})
    assert r.status_code == 401


def test_preview_not_found(client, db):
    t = _tenant(db, "cap-nf")
    h = _login_guest(client, t, "n@x.com")
    r = client.get("/bookings/nope/refund-preview", headers=h)
    assert r.status_code == 404


def test_preview_full_refund(client, db):
    t = _tenant(db, "cap-full")
    h = _login_guest(client, t, "full@x.com")
    b = _booking_for(db, t, "full@x.com", offset=10, amount=1000)
    r = client.get(f"/bookings/{b.id}/refund-preview", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["refund_pct"] == 100
    assert body["refund_amount"] == "1000.00"
    assert body["can_cancel"] is True


def test_preview_partial_refund(client, db):
    t = _tenant(db, "cap-part")
    h = _login_guest(client, t, "part@x.com")
    b = _booking_for(db, t, "part@x.com", offset=5, amount=1000)
    r = client.get(f"/bookings/{b.id}/refund-preview", headers=h)
    body = r.json()
    assert body["refund_pct"] == 50
    assert body["refund_amount"] == "500.00"


def test_cancel_with_refund(client, db):
    t = _tenant(db, "cap-cxl")
    h = _login_guest(client, t, "cxl@x.com")
    b = _booking_for(db, t, "cxl@x.com", offset=10, amount=800)
    r = client.post(f"/bookings/{b.id}/cancel-with-refund", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "cancelled"
    assert body["refund_amount"] == "800.00"
    assert body["policy_label"] == "full"
    db.refresh(b)
    assert b.status == "cancelled"


def test_cancel_twice_conflict(client, db):
    t = _tenant(db, "cap-2x")
    h = _login_guest(client, t, "twice@x.com")
    b = _booking_for(db, t, "twice@x.com", offset=10)
    r1 = client.post(f"/bookings/{b.id}/cancel-with-refund", headers=h)
    assert r1.status_code == 200
    r2 = client.post(f"/bookings/{b.id}/cancel-with-refund", headers=h)
    assert r2.status_code == 409


def test_cross_user_blocked(client, db):
    t = _tenant(db, "cap-xu")
    h1 = _login_guest(client, t, "u1@x.com")
    _login_guest(client, t, "u2@x.com")
    b = _booking_for(db, t, "u2@x.com", offset=10)
    r = client.get(f"/bookings/{b.id}/refund-preview", headers=h1)
    assert r.status_code == 404
