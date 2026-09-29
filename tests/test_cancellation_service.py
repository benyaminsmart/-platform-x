"""Tests for Cancellation service (Phase 30, Step 5)."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User
from app.services import cancellation_service


def _tenant(db, slug="cx"):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, tenant, email="u@x.com"):
    u = User(tenant_id=tenant.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="U", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db, tenant, user, *, check_in_offset=10, amount=1000, status="confirmed"):
    ci = date.today() + timedelta(days=check_in_offset)
    b = Booking(tenant_id=tenant.id, user_id=user.id, booking_type="room",
                service_name="R", check_in=ci, check_out=ci + timedelta(days=1),
                guests=1, amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency="AED",
                status=status, payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_full_refund(db):
    t = _tenant(db, "cxf")
    u = _user(db, t, "a@x.com")
    b = _booking(db, t, u, check_in_offset=10, amount=1000)
    r = cancellation_service.compute_refund_policy(b)
    assert r["refund_pct"] == 100
    assert r["policy_label"] == "full"
    assert r["refund_amount"] == "1000.00"
    assert r["days_until_check_in"] == 10


def test_partial_refund(db):
    t = _tenant(db, "cxp")
    u = _user(db, t, "b@x.com")
    b = _booking(db, t, u, check_in_offset=5, amount=1000)
    r = cancellation_service.compute_refund_policy(b)
    assert r["refund_pct"] == 50
    assert r["policy_label"] == "partial"
    assert r["refund_amount"] == "500.00"


def test_no_refund(db):
    t = _tenant(db, "cxn")
    u = _user(db, t, "c@x.com")
    b = _booking(db, t, u, check_in_offset=1, amount=1000)
    r = cancellation_service.compute_refund_policy(b)
    assert r["refund_pct"] == 0
    assert r["policy_label"] == "none"
    assert r["refund_amount"] == "0.00"


def test_boundary_7_days(db):
    t = _tenant(db, "cx7")
    u = _user(db, t, "d@x.com")
    b = _booking(db, t, u, check_in_offset=7, amount=1000)
    r = cancellation_service.compute_refund_policy(b)
    assert r["refund_pct"] == 50


def test_boundary_8_days(db):
    t = _tenant(db, "cx8")
    u = _user(db, t, "e@x.com")
    b = _booking(db, t, u, check_in_offset=8, amount=1000)
    r = cancellation_service.compute_refund_policy(b)
    assert r["refund_pct"] == 100


def test_boundary_3_days(db):
    t = _tenant(db, "cx3")
    u = _user(db, t, "f@x.com")
    b = _booking(db, t, u, check_in_offset=3, amount=1000)
    r = cancellation_service.compute_refund_policy(b)
    assert r["refund_pct"] == 50


def test_boundary_2_days(db):
    t = _tenant(db, "cx2")
    u = _user(db, t, "g@x.com")
    b = _booking(db, t, u, check_in_offset=2, amount=1000)
    r = cancellation_service.compute_refund_policy(b)
    assert r["refund_pct"] == 0


def test_cancel_ok(db):
    t = _tenant(db, "cxok")
    u = _user(db, t, "h@x.com")
    b = _booking(db, t, u, check_in_offset=10, amount=800)
    out = cancellation_service.cancel_booking(db, booking=b, by_user=u)
    assert out["ok"] is True
    assert out["refund"]["refund_amount"] == "800.00"
    db.refresh(b)
    assert b.status == "cancelled"
    assert b.cancelled_at is not None
    assert "cancelled by user" in (b.notes or "")


def test_cancel_invalid_status(db):
    t = _tenant(db, "cxinv")
    u = _user(db, t, "i@x.com")
    b = _booking(db, t, u, status="cancelled")
    with pytest.raises(ValueError):
        cancellation_service.cancel_booking(db, booking=b)


def test_can_cancel(db):
    t = _tenant(db, "cxcc")
    u = _user(db, t, "j@x.com")
    b = _booking(db, t, u, status="pending")
    assert cancellation_service.can_cancel(b) is True
    b.status = "cancelled"
    assert cancellation_service.can_cancel(b) is False
