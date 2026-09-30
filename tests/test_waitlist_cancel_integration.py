"""Tests for Waitlist ↔ cancellation integration (Phase 48, Step 4)."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.models.waitlist_entry import WaitlistEntry
from app.services import waitlist_service as wls
from app.services import booking_service as bs
from app.services import cancellation_service as cs


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t, capacity=1):
    s = Service(tenant_id=t.id, type="room", name="Room",
                price=Decimal("500"), currency="AED", capacity=capacity,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _user(db, t, email):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db, t, u, svc, ci, co, status="confirmed"):
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_id=svc.id, service_name=svc.name,
                check_in=ci, check_out=co, guests=1,
                amount=Decimal("500"), discount=Decimal("0"),
                total_amount=Decimal("500"), currency="AED",
                status=status, payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_booking_service_cancel_triggers_waitlist_notify(db):
    t = _tenant(db, "wl-int-1")
    s = _svc(db, t, capacity=1)
    u1 = _user(db, t, "u1@x.com")
    u2 = _user(db, t, "u2@x.com")
    ci = date(2030, 1, 1)
    co = date(2030, 1, 3)
    b = _booking(db, t, u1, s, ci, co)
    # u2 joins waitlist
    entry, st = wls.join(db, user_id=u2.id, service_id=s.id, check_in=ci, check_out=co)
    assert st == "ok"
    assert entry.notified_at is None

    # Cancel via booking_service
    bs.cancel_booking(db, user_id=u1.id, booking_id=b.id)

    # Reload entry
    db.refresh(entry)
    assert entry.notified_at is not None


def test_cancellation_service_triggers_waitlist_notify(db):
    t = _tenant(db, "wl-int-2")
    s = _svc(db, t, capacity=1)
    u1 = _user(db, t, "u3@x.com")
    u2 = _user(db, t, "u4@x.com")
    ci = date(2030, 2, 1)
    co = date(2030, 2, 3)
    b = _booking(db, t, u1, s, ci, co)
    entry, st = wls.join(db, user_id=u2.id, service_id=s.id, check_in=ci, check_out=co)
    assert st == "ok"

    # Cancel via cancellation_service
    out = cs.cancel_with_refund(db, booking=b)
    assert out["ok"] is True

    db.refresh(entry)
    assert entry.notified_at is not None


def test_hook_never_breaks_cancel(db, monkeypatch):
    """Even if waitlist notify fails, cancellation must still succeed."""
    t = _tenant(db, "wl-int-3")
    s = _svc(db, t, capacity=1)
    u1 = _user(db, t, "u5@x.com")
    ci = date(2030, 3, 1)
    co = date(2030, 3, 3)
    b = _booking(db, t, u1, s, ci, co)

    def _boom(*a, **kw):
        raise RuntimeError("boom")
    monkeypatch.setattr(wls, "check_and_notify", _boom)

    # Should not raise
    out = bs.cancel_booking(db, user_id=u1.id, booking_id=b.id)
    db.refresh(out)
    assert out.status == "cancelled"


def test_fifo_order_via_integration(db):
    t = _tenant(db, "wl-int-fifo")
    s = _svc(db, t, capacity=1)
    u1 = _user(db, t, "f1@x.com")
    u2 = _user(db, t, "f2@x.com")
    u3 = _user(db, t, "f3@x.com")
    ci = date(2030, 4, 1)
    co = date(2030, 4, 3)
    b = _booking(db, t, u1, s, ci, co)

    wls.join(db, user_id=u2.id, service_id=s.id, check_in=ci, check_out=co)
    wls.join(db, user_id=u3.id, service_id=s.id, check_in=ci, check_out=co)

    bs.cancel_booking(db, user_id=u1.id, booking_id=b.id)

    # u2 (first FIFO) must be the one notified
    e2 = db.query(WaitlistEntry).filter(WaitlistEntry.user_id == u2.id).one()
    e3 = db.query(WaitlistEntry).filter(WaitlistEntry.user_id == u3.id).one()
    assert e2.notified_at is not None
    assert e3.notified_at is None
