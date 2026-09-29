"""Tests for GroupMember model + is_group on Booking (Phase 40, Step 1)."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.booking import Booking
from app.models.group_member import GroupMember
from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import hash_password


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="g@x.com"):
    u = User(tenant_id=t.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db, t, u, *, is_group=False):
    ci = date.today() + timedelta(days=10)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_name="R", check_in=ci, check_out=ci + timedelta(days=2),
                guests=1, amount=Decimal("1000"), discount=Decimal("0"),
                total_amount=Decimal("1000"), currency="AED",
                status="confirmed", payment_status="paid", is_group=is_group)
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_booking_default_not_group(db):
    t = _tenant(db, "gm-bk")
    u = _user(db, t)
    b = _booking(db, t, u)
    assert b.is_group is False


def test_booking_is_group_flag(db):
    t = _tenant(db, "gm-bkg")
    u = _user(db, t)
    b = _booking(db, t, u, is_group=True)
    db.refresh(b)
    assert b.is_group is True


def test_group_member_create(db):
    t = _tenant(db, "gm-create")
    u = _user(db, t)
    b = _booking(db, t, u, is_group=True)
    m = GroupMember(tenant_id=t.id, booking_id=b.id, name="Ali",
                    email="ali@x.com", share_amount=Decimal("250"), paid=False)
    db.add(m); db.commit(); db.refresh(m)
    assert m.id
    assert m.paid is False


def test_group_member_unique_email_per_booking(db):
    t = _tenant(db, "gm-uniq")
    u = _user(db, t)
    b = _booking(db, t, u, is_group=True)
    db.add(GroupMember(tenant_id=t.id, booking_id=b.id, name="A",
                       email="a@x.com", share_amount=Decimal("100")))
    db.commit()
    db.add(GroupMember(tenant_id=t.id, booking_id=b.id, name="B",
                       email="a@x.com", share_amount=Decimal("100")))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_group_member_defaults(db):
    t = _tenant(db, "gm-def")
    u = _user(db, t)
    b = _booking(db, t, u, is_group=True)
    m = GroupMember(tenant_id=t.id, booking_id=b.id, name="X", email="x@y.com")
    db.add(m); db.commit(); db.refresh(m)
    assert m.share_amount == Decimal("0")
    assert m.paid is False
    assert m.note is None
