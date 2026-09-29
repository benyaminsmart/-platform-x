"""Tests for Marketing customer segmentation (Phase 25, Step 1)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User
from app.services import marketing


# ---------- Helpers ----------


def _tenant(db: Session, slug: str = "mkt") -> Tenant:
    t = Tenant(slug=slug, name="Mkt Biz", tier="starter", status="active", config={})
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _user(db: Session, tenant: Tenant, email: str, *, tier: str = "welcome", status: str = "active") -> User:
    u = User(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password("Pass1234"),
        first_name="U", last_name="X",
        referral_code=email[:10].upper(),
        tier=tier, status=status,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _booking(db: Session, tenant: Tenant, user: User, *, check_in: date, amount: float = 500) -> Booking:
    b = Booking(
        tenant_id=tenant.id, user_id=user.id, booking_type="room",
        service_name="R", check_in=check_in, check_out=check_in + timedelta(days=1),
        guests=1, amount=Decimal(str(amount)), discount=Decimal("0"),
        total_amount=Decimal(str(amount)), currency="AED",
        status="confirmed", payment_status="paid",
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


# ---------- Empty tenant ----------


def test_segment_empty_tenant(db: Session) -> None:
    t = _tenant(db)
    out = marketing.segment_customers(db, t)
    assert out["totals"]["customers"] == 0
    assert out["totals"]["all_time_revenue"] == 0.0
    for s in marketing.SEGMENTS:
        assert out["segments"][s]["count"] == 0


# ---------- All / past bookers ----------


def test_segment_all_and_past_bookers(db: Session) -> None:
    t = _tenant(db)
    u1 = _user(db, t, "a@x.com")
    u2 = _user(db, t, "b@x.com")
    # u1 has booking, u2 does not
    _booking(db, t, u1, check_in=date.today() - timedelta(days=10))

    out = marketing.segment_customers(db, t)
    # "all" only includes users with bookings (aggregation is from Booking table)
    assert out["segments"]["all"]["count"] == 1
    assert out["segments"]["past_bookers"]["count"] == 1


# ---------- inactive_90d ----------


def test_inactive_90d(db: Session) -> None:
    t = _tenant(db)
    u_active = _user(db, t, "active@x.com")
    u_inactive = _user(db, t, "inactive@x.com")
    today = date.today()
    _booking(db, t, u_active, check_in=today - timedelta(days=10))
    _booking(db, t, u_inactive, check_in=today - timedelta(days=200))

    out = marketing.segment_customers(db, t)
    assert out["segments"]["inactive_90d"]["count"] == 1


# ---------- new_30d ----------


def test_new_30d(db: Session) -> None:
    t = _tenant(db)
    u_new = _user(db, t, "new@x.com")
    u_old = _user(db, t, "old@x.com")
    today = date.today()
    _booking(db, t, u_new, check_in=today - timedelta(days=5))
    _booking(db, t, u_old, check_in=today - timedelta(days=100))

    out = marketing.segment_customers(db, t)
    assert out["segments"]["new_30d"]["count"] == 1


# ---------- high_value ----------


def test_high_value_top_20_percent(db: Session) -> None:
    t = _tenant(db)
    today = date.today()
    # 5 users with increasing spend
    for i, amt in enumerate([100, 200, 300, 400, 5000], start=1):
        u = _user(db, t, f"u{i}@x.com")
        _booking(db, t, u, check_in=today - timedelta(days=i), amount=amt)

    out = marketing.segment_customers(db, t)
    hv = out["segments"]["high_value"]
    # Top 20% of 5 users => at least the top spender
    assert hv["count"] >= 1
    assert hv["top20_threshold_aed"] is not None
    # The 5000 spender must be included
    assert "u5@x.com" in hv["sample_emails"]


# ---------- loyalty_gold_plus ----------


def test_loyalty_gold_plus(db: Session) -> None:
    t = _tenant(db)
    today = date.today()
    u_std = _user(db, t, "std@x.com", tier="welcome")
    u_gold = _user(db, t, "gold@x.com", tier="gold")
    u_platinum = _user(db, t, "plat@x.com", tier="platinum")
    for u in [u_std, u_gold, u_platinum]:
        _booking(db, t, u, check_in=today - timedelta(days=5))

    out = marketing.segment_customers(db, t)
    assert out["segments"]["loyalty_gold_plus"]["count"] == 2


# ---------- inactive users excluded ----------


def test_suspended_user_excluded(db: Session) -> None:
    t = _tenant(db)
    today = date.today()
    u_active = _user(db, t, "a@x.com", status="active")
    u_susp = _user(db, t, "s@x.com", status="suspended")
    _booking(db, t, u_active, check_in=today - timedelta(days=5))
    _booking(db, t, u_susp, check_in=today - timedelta(days=5))

    out = marketing.segment_customers(db, t)
    assert out["segments"]["all"]["count"] == 1  # suspended excluded


# ---------- Cross-tenant isolation ----------


def test_cross_tenant_isolation(db: Session) -> None:
    t1 = _tenant(db, "iso-a")
    t2 = _tenant(db, "iso-b")
    u1 = _user(db, t1, "a@x.com")
    u2 = _user(db, t2, "b@x.com")
    today = date.today()
    _booking(db, t1, u1, check_in=today)
    _booking(db, t2, u2, check_in=today)

    out_a = marketing.segment_customers(db, t1)
    out_b = marketing.segment_customers(db, t2)
    assert out_a["segments"]["all"]["count"] == 1
    assert out_b["segments"]["all"]["count"] == 1


# ---------- get_segment_customers ----------


def test_get_segment_customers_all(db: Session) -> None:
    t = _tenant(db, "get-seg")
    today = date.today()
    for i in range(3):
        u = _user(db, t, f"u{i}@x.com")
        _booking(db, t, u, check_in=today - timedelta(days=i))

    rows = marketing.get_segment_customers(db, t, "all")
    assert len(rows) == 3
    assert all("email" in r for r in rows)


def test_get_segment_customers_unknown_raises(db: Session) -> None:
    t = _tenant(db, "unknown-seg")
    with pytest.raises(ValueError):
        marketing.get_segment_customers(db, t, "bogus")


def test_get_segment_customers_limit(db: Session) -> None:
    t = _tenant(db, "limit-seg")
    today = date.today()
    for i in range(5):
        u = _user(db, t, f"u{i}@x.com")
        _booking(db, t, u, check_in=today - timedelta(days=i))
    rows = marketing.get_segment_customers(db, t, "all", limit=2)
    assert len(rows) == 2


# ---------- estimate_audience_size ----------


def test_estimate_audience_size(db: Session) -> None:
    t = _tenant(db, "size-seg")
    today = date.today()
    for i in range(4):
        u = _user(db, t, f"u{i}@x.com")
        _booking(db, t, u, check_in=today - timedelta(days=i))

    assert marketing.estimate_audience_size(db, t, "all") == 4
    assert marketing.estimate_audience_size(db, t, "past_bookers") == 4


def test_estimate_audience_unknown_raises(db: Session) -> None:
    t = _tenant(db, "size-bad")
    with pytest.raises(ValueError):
        marketing.estimate_audience_size(db, t, "bogus")
