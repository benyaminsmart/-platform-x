"""Tests for booking receipt endpoint (Phase 30, Step 7)."""
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import hash_password, create_access_token


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"Hotel {slug}", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai, UAE"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, tenant, email):
    u = User(tenant_id=tenant.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="U", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db, tenant, user):
    ci = date.today() + timedelta(days=10)
    b = Booking(tenant_id=tenant.id, user_id=user.id, booking_type="room",
                service_name="Deluxe Room", check_in=ci, check_out=ci + timedelta(days=2),
                guests=2, amount=Decimal("1000"), discount=Decimal("0"),
                total_amount=Decimal("1000"), currency="AED",
                status="confirmed", payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_receipt_requires_auth(client, db):
    t = _tenant(db, "rec-noauth")
    u = _user(db, t, "n@x.com")
    b = _booking(db, t, u)
    r = client.get(f"/bookings/{b.id}/receipt")
    assert r.status_code == 401


def test_receipt_not_found(client, db):
    t = _tenant(db, "rec-nf")
    u = _user(db, t, "nf@x.com")
    token = create_access_token(u.id, tenant_id=t.id)
    r = client.get("/bookings/nope/receipt",
                   headers={"Authorization": f"Bearer {token}", "X-Tenant-Slug": t.slug})
    assert r.status_code == 404


def test_receipt_renders(client, db):
    t = _tenant(db, "rec-ok")
    u = _user(db, t, "ok@x.com")
    b = _booking(db, t, u)
    token = create_access_token(u.id, tenant_id=t.id)
    r = client.get(f"/bookings/{b.id}/receipt",
                   headers={"Authorization": f"Bearer {token}", "X-Tenant-Slug": t.slug})
    assert r.status_code == 200
    html = r.text
    assert "Platform-X" in html
    assert "Booking receipt" in html
    assert "Deluxe Room" in html
    assert "1000" in html
    assert "AED" in html
    assert "Hotel rec-ok" in html
    assert "Dubai, UAE" in html
    assert "window.print()" in html
