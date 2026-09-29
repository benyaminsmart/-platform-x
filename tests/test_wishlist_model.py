"""Tests for Wishlist model (Phase 33, Step 1)."""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.tenant import Tenant
from app.models.service import Service
from app.models.user import User
from app.models.wishlist import Wishlist
from app.core.security import hash_password
from decimal import Decimal


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active", config={})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, tenant, email):
    u = User(tenant_id=tenant.id, email=email, password_hash=hash_password("Pass1234"),
             first_name="U", last_name="X", referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _svc(db, tenant, name="R"):
    s = Service(tenant_id=tenant.id, type="room", name=name,
                price=Decimal("500"), currency="AED", capacity=2,
                attributes={}, image_urls=[], status="active", display_order=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


def test_wishlist_create(db):
    t = _tenant(db, "w-create")
    u = _user(db, t, "u@x.com")
    s = _svc(db, t, "Room")
    w = Wishlist(user_id=u.id, service_id=s.id, tenant_id=t.id, note="For next trip")
    db.add(w); db.commit(); db.refresh(w)
    assert w.id
    assert w.note == "For next trip"


def test_wishlist_unique_constraint(db):
    t = _tenant(db, "w-uniq")
    u = _user(db, t, "u2@x.com")
    s = _svc(db, t, "R")
    db.add(Wishlist(user_id=u.id, service_id=s.id, tenant_id=t.id))
    db.commit()
    db.add(Wishlist(user_id=u.id, service_id=s.id, tenant_id=t.id))
    try:
        db.commit()
        assert False, "should have raised"
    except IntegrityError:
        db.rollback()
