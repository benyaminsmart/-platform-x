"""Tests for group service (Phase 40, Step 2)."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User
from app.services import group_service


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


def test_add_member_ok(db):
    t = _tenant(db, "gs-add")
    u = _user(db, t)
    b = _booking(db, t, u)
    m = group_service.add_member(db, booking=b, name="Ali", email="ali@x.com", share_amount=250)
    assert m.id


def test_add_member_not_group(db):
    t = _tenant(db, "gs-notgroup")
    u = _user(db, t)
    b = _booking(db, t, u, is_group=False)
    with pytest.raises(ValueError):
        group_service.add_member(db, booking=b, name="A", email="a@x.com")


def test_add_member_duplicate_email(db):
    t = _tenant(db, "gs-dup")
    u = _user(db, t)
    b = _booking(db, t, u)
    group_service.add_member(db, booking=b, name="A", email="a@x.com")
    with pytest.raises(ValueError):
        group_service.add_member(db, booking=b, name="B", email="a@x.com")


def test_add_member_invalid_email(db):
    t = _tenant(db, "gs-bademail")
    u = _user(db, t)
    b = _booking(db, t, u)
    with pytest.raises(ValueError):
        group_service.add_member(db, booking=b, name="A", email="not-an-email")


def test_share_cannot_exceed_booking_total(db):
    t = _tenant(db, "gs-exceed")
    u = _user(db, t)
    b = _booking(db, t, u, amount=1000)
    group_service.add_member(db, booking=b, name="A", email="a@x.com", share_amount=600)
    group_service.add_member(db, booking=b, name="B", email="b@x.com", share_amount=300)
    with pytest.raises(ValueError):
        group_service.add_member(db, booking=b, name="C", email="c@x.com", share_amount=200)


def test_update_member(db):
    t = _tenant(db, "gs-upd")
    u = _user(db, t)
    b = _booking(db, t, u)
    m = group_service.add_member(db, booking=b, name="A", email="a@x.com", share_amount=100)
    m2 = group_service.update_member(db, booking=b, member_id=m.id,
                                     updates={"share_amount": 200, "paid": True})
    assert m2.share_amount == Decimal("200.00")
    assert m2.paid is True


def test_remove_member(db):
    t = _tenant(db, "gs-rm")
    u = _user(db, t)
    b = _booking(db, t, u)
    m = group_service.add_member(db, booking=b, name="A", email="a@x.com")
    ok = group_service.remove_member(db, booking=b, member_id=m.id)
    assert ok is True
    assert group_service.list_members(db, booking_id=b.id) == []


def test_share_summary(db):
    t = _tenant(db, "gs-sum")
    u = _user(db, t)
    b = _booking(db, t, u, amount=1000)
    group_service.add_member(db, booking=b, name="A", email="a@x.com", share_amount=400)
    group_service.add_member(db, booking=b, name="B", email="b@x.com", share_amount=300)
    m_c = group_service.add_member(db, booking=b, name="C", email="c@x.com", share_amount=100)
    group_service.update_member(db, booking=b, member_id=m_c.id, updates={"paid": True})
    s = group_service.share_summary(db, booking=b)
    assert s["booking_total"] == "1000.00"
    assert s["shares_total"] == "800.00"
    assert s["paid_total"] == "100.00"
    assert s["unpaid_total"] == "700.00"
    assert s["remaining_to_allocate"] == "200.00"
    assert s["members_count"] == 3
    assert s["paid_members_count"] == 1
