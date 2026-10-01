"""Tests for Business Group service (Phase 58, Step 1)."""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.business_group import BusinessGroup
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import business_group_service as bgs


def _tenant(db, slug, typ="hotel", rating=4.5, currency="AED"):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": typ, "rating": rating, "location": "Dubai",
                       "currency": currency})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _owner(db, tenant, email="owner@x.com"):
    # referral_code must be globally unique — mix tenant slug
    rc = ("OWN" + email.split("@")[0].upper() + "-" + tenant.slug.upper())[:30]
    u = User(tenant_id=tenant.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="O", last_name="X", business_role="owner",
             referral_code=rc, status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _svc(db, t, price=500):
    s = Service(tenant_id=t.id, type="room", name=f"R-{t.slug}",
                price=Decimal(str(price)), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def _booking(db, t, u, amount=1000, days_ago=5, status="confirmed"):
    ci = date.today() - timedelta(days=days_ago)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_name="R", check_in=ci,
                check_out=ci + timedelta(days=1), guests=1,
                amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency="AED",
                status=status, payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    return b


def test_create_group_ok(db):
    t = _tenant(db, "bg-1")
    u = _owner(db, t)
    g, st = bgs.create_group(db, owner_user_id=u.id, name="My Hotels")
    assert st == "ok"
    assert g.slug == "my-hotels"


def test_create_group_empty_name(db):
    t = _tenant(db, "bg-empty")
    u = _owner(db, t, "empty@x.com")
    g, st = bgs.create_group(db, owner_user_id=u.id, name="   ")
    assert st == "bad_name"
    assert g is None


def test_create_group_duplicate_slug(db):
    t = _tenant(db, "bg-dup")
    u = _owner(db, t, "dup@x.com")
    bgs.create_group(db, owner_user_id=u.id, name="Chain")
    g2, st = bgs.create_group(db, owner_user_id=u.id, name="Chain")
    assert st == "ok"
    assert g2.slug == "chain-2"


def test_list_groups(db):
    t = _tenant(db, "bg-list")
    u = _owner(db, t, "list@x.com")
    bgs.create_group(db, owner_user_id=u.id, name="Alpha")
    bgs.create_group(db, owner_user_id=u.id, name="Beta")
    rows = bgs.list_groups(db, owner_user_id=u.id)
    assert len(rows) == 2
    names = {r["name"] for r in rows}
    assert {"Alpha", "Beta"} == names


def test_attach_tenant_ok(db):
    t = _tenant(db, "bg-attach-1")
    t2 = _tenant(db, "bg-attach-2")
    u = _owner(db, t, "attach@x.com")
    g, _ = bgs.create_group(db, owner_user_id=u.id, name="Group A")
    # owner also owns t2 (same email, business_role=owner)
    _owner(db, t2, "attach@x.com")
    out, st = bgs.attach_tenant(db, owner_user_id=u.id, group_id=g.id, tenant_slug="bg-attach-2")
    assert st == "ok"
    assert out.slug == "bg-attach-2"
    assert out.group_id == g.id


def test_attach_tenant_not_owner(db):
    t = _tenant(db, "bg-own-1")
    t2 = _tenant(db, "bg-own-2")
    u = _owner(db, t, "me@x.com")
    _owner(db, t2, "other@x.com")
    g, _ = bgs.create_group(db, owner_user_id=u.id, name="Group")
    _, st = bgs.attach_tenant(db, owner_user_id=u.id, group_id=g.id, tenant_slug="bg-own-2")
    assert st == "not_owner"


def test_detach_tenant(db):
    t = _tenant(db, "bg-det-1")
    t2 = _tenant(db, "bg-det-2")
    u = _owner(db, t, "det@x.com")
    _owner(db, t2, "det@x.com")
    g, _ = bgs.create_group(db, owner_user_id=u.id, name="G")
    bgs.attach_tenant(db, owner_user_id=u.id, group_id=g.id, tenant_slug=t2.slug)
    assert bgs.detach_tenant(db, owner_user_id=u.id, group_id=g.id, tenant_slug=t2.slug) is True
    db.refresh(t2)
    assert t2.group_id is None


def test_delete_group_detaches_members(db):
    t = _tenant(db, "bg-del-1")
    t2 = _tenant(db, "bg-del-2")
    u = _owner(db, t, "del@x.com")
    _owner(db, t2, "del@x.com")
    g, _ = bgs.create_group(db, owner_user_id=u.id, name="ToDelete")
    bgs.attach_tenant(db, owner_user_id=u.id, group_id=g.id, tenant_slug=t2.slug)
    assert bgs.delete_group(db, owner_user_id=u.id, group_id=g.id) is True
    db.refresh(t2)
    assert t2.group_id is None
    assert db.query(BusinessGroup).filter(BusinessGroup.id == g.id).one_or_none() is None


def test_aggregate_metrics(db):
    t1 = _tenant(db, "bg-agg-1", rating=4.0)
    t2 = _tenant(db, "bg-agg-2", rating=4.6)
    u = _owner(db, t1, "agg@x.com")
    _owner(db, t2, "agg@x.com")
    g, _ = bgs.create_group(db, owner_user_id=u.id, name="Agg")
    bgs.attach_tenant(db, owner_user_id=u.id, group_id=g.id, tenant_slug=t1.slug)
    bgs.attach_tenant(db, owner_user_id=u.id, group_id=g.id, tenant_slug=t2.slug)
    _svc(db, t1)
    _svc(db, t2)
    _booking(db, t1, u, amount=1000)
    _booking(db, t2, u, amount=500)

    out = bgs.aggregate_metrics(db, group_id=g.id, window_days=30)
    assert out["members_count"] == 2
    assert out["services_count"] == 2
    assert out["bookings_30d"] == 2
    assert out["revenue_30d"] == "1500.00"
    assert out["avg_rating"] == 4.3


def test_aggregate_empty_group(db):
    t = _tenant(db, "bg-noagg")
    u = _owner(db, t, "noagg@x.com")
    g, _ = bgs.create_group(db, owner_user_id=u.id, name="Empty")
    out = bgs.aggregate_metrics(db, group_id=g.id)
    assert out["members_count"] == 0
    assert out["revenue_30d"] == "0.00"
