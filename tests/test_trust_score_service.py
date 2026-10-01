"""Tests for Trust Score service (Phase 49, Step 1)."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.review import Review
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import trust_score_service as tss


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db, t):
    s = Service(tenant_id=t.id, type="room", name="R",
                price=Decimal("500"), currency="AED", capacity=2,
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


def _review(db, t, u, rating=5, verified=True, responded=False, status="published"):
    r = Review(tenant_id=t.id, user_id=u.id, rating=rating,
               title="t", content="c", status=status, verified=verified,
               response_text=("r" if responded else None))
    db.add(r); db.commit(); db.refresh(r)
    return r


def _booking(db, t, u, svc, status="confirmed", created_offset_days=5):
    ci = date.today() + timedelta(days=10)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_id=svc.id, service_name=svc.name,
                check_in=ci, check_out=ci + timedelta(days=1), guests=1,
                amount=Decimal("500"), discount=Decimal("0"),
                total_amount=Decimal("500"), currency="AED",
                status=status, payment_status="paid")
    db.add(b); db.commit(); db.refresh(b)
    b.created_at = datetime.now(timezone.utc) - timedelta(days=created_offset_days)
    db.commit()
    return b


def test_empty_tenant_neutral_baseline(db):
    t = _tenant(db, "ts-empty")
    out = tss.compute(db, tenant_id=t.id)
    assert out["score"] == 50.0 * 0.4 + 50.0 * 0.2 + 50.0 * 0.2 + 0.0 * 0.2
    assert out["meta"]["rating"]["reviews_count"] == 0
    assert out["meta"]["volume"]["bookings_30d"] == 0


def test_perfect_tenant_scores_high(db):
    t = _tenant(db, "ts-perfect")
    s = _svc(db, t)
    u = _user(db, t, "perf@x.com")
    for i in range(5):
        _review(db, t, u, rating=5, verified=True, responded=True)
    for i in range(35):
        _booking(db, t, u, s, status="confirmed", created_offset_days=5)

    out = tss.compute(db, tenant_id=t.id)
    assert out["components"]["rating"] == 100.0
    assert out["components"]["verification"] == 100.0
    assert out["components"]["responsiveness"] == 100.0
    assert out["components"]["volume"] >= 95.0
    assert out["score"] >= 95.0


def test_poor_tenant_scores_low(db):
    t = _tenant(db, "ts-poor")
    u = _user(db, t, "poor@x.com")
    for i in range(4):
        _review(db, t, u, rating=1, verified=False, responded=False)
    out = tss.compute(db, tenant_id=t.id)
    assert out["components"]["rating"] == 0.0
    assert out["components"]["verification"] == 0.0
    assert out["components"]["responsiveness"] == 0.0
    assert out["score"] < 25.0


def test_volume_window_excludes_old(db):
    t = _tenant(db, "ts-window")
    s = _svc(db, t)
    u = _user(db, t, "win@x.com")
    for i in range(5):
        _booking(db, t, u, s, created_offset_days=5)
    for i in range(5):
        _booking(db, t, u, s, created_offset_days=60)
    out = tss.compute(db, tenant_id=t.id)
    assert out["meta"]["volume"]["bookings_30d"] == 5


def test_cancelled_bookings_excluded_from_volume(db):
    t = _tenant(db, "ts-canc")
    s = _svc(db, t)
    u = _user(db, t, "canc@x.com")
    _booking(db, t, u, s, status="confirmed")
    _booking(db, t, u, s, status="cancelled")
    out = tss.compute(db, tenant_id=t.id)
    assert out["meta"]["volume"]["bookings_30d"] == 1


def test_hidden_reviews_excluded(db):
    t = _tenant(db, "ts-hidden")
    u = _user(db, t, "hid@x.com")
    _review(db, t, u, rating=5, status="published")
    _review(db, t, u, rating=1, status="hidden")
    out = tss.compute(db, tenant_id=t.id)
    assert out["meta"]["rating"]["reviews_count"] == 1


def test_get_by_slug(db):
    t = _tenant(db, "ts-slug")
    out = tss.get_by_slug(db, slug="ts-slug")
    assert out is not None
    assert out["tenant_slug"] == "ts-slug"
    assert "score" in out


def test_get_by_slug_not_found(db):
    assert tss.get_by_slug(db, slug="does-not-exist") is None


def test_compute_many(db):
    t1 = _tenant(db, "ts-m1")
    t2 = _tenant(db, "ts-m2")
    out = tss.compute_many(db, tenant_ids=[t1.id, t2.id])
    assert t1.id in out and t2.id in out
    assert "score" in out[t1.id]


def test_tier_label():
    assert tss.tier_label(90) == "excellent"
    assert tss.tier_label(75) == "very_good"
    assert tss.tier_label(60) == "good"
    assert tss.tier_label(45) == "fair"
    assert tss.tier_label(20) == "new"
