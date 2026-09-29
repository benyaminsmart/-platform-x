"""Tests for Market Insights service (Phase 27, Step 1)."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import market_insights


# ---------- Helpers ----------


def _tenant(db: Session, slug: str, *, cfg: dict | None = None) -> Tenant:
    t = Tenant(slug=slug, name=slug, tier="starter", status="active", config=cfg or {"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db: Session, tenant: Tenant, *, name: str = "R", price: float = 500, status: str = "active") -> Service:
    s = Service(
        tenant_id=tenant.id, type="room", name=name,
        price=Decimal(str(price)), currency="AED", capacity=2,
        attributes={}, image_urls=[], status=status, display_order=0,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s


def _booking(db: Session, tenant: Tenant, *, days_ago: int = 5, amount: float = 500, status: str = "confirmed") -> Booking:
    # need a user
    u = db.query(User).filter(User.tenant_id == tenant.id).first()
    if u is None:
        u = User(
            tenant_id=tenant.id, email=f"u-{tenant.slug}@x.com",
            password_hash=hash_password("Pass1234"),
            first_name="U", last_name="X",
            referral_code=(tenant.slug[:10]).upper(),
            status="active",
        )
        db.add(u); db.commit(); db.refresh(u)
    ci = date.today() - timedelta(days=days_ago)
    b = Booking(
        tenant_id=tenant.id, user_id=u.id, booking_type="room",
        service_name="R", check_in=ci, check_out=ci + timedelta(days=1),
        guests=1, amount=Decimal(str(amount)), discount=Decimal("0"),
        total_amount=Decimal(str(amount)), currency="AED",
        status=status, payment_status="paid",
    )
    db.add(b); db.commit(); db.refresh(b)
    return b


# ---------- category_summary ----------


def test_category_summary_no_peers(db: Session) -> None:
    t = _tenant(db, "only-hotel", cfg={"type": "hotel"})
    out = market_insights.category_summary(db, category="hotels", exclude_tenant_id=t.id)
    assert out["cohort_size"] == 0
    assert "note" in out


def test_category_summary_with_peers(db: Session) -> None:
    t_self = _tenant(db, "self", cfg={"type": "hotel", "rating": 4.5})
    p1 = _tenant(db, "p1", cfg={"type": "hotel", "rating": 4.0})
    p2 = _tenant(db, "p2", cfg={"type": "hotel", "rating": 4.8})
    p3 = _tenant(db, "p3", cfg={"type": "hotel", "rating": 3.5})
    _svc(db, p1, price=300)
    _svc(db, p2, price=700)
    _svc(db, p3, price=500)

    out = market_insights.category_summary(db, category="hotels", exclude_tenant_id=t_self.id)
    assert out["cohort_size"] == 3
    assert out["metrics"]["avg_price"]["min"] == 300.0
    assert out["metrics"]["avg_price"]["max"] == 700.0
    assert out["metrics"]["avg_price"]["median"] == 500.0
    assert out["metrics"]["rating"]["median"] == 4.0


def test_category_summary_excludes_self(db: Session) -> None:
    t_self = _tenant(db, "self", cfg={"type": "hotel"})
    _tenant(db, "other", cfg={"type": "hotel"})
    out = market_insights.category_summary(db, category="hotels", exclude_tenant_id=t_self.id)
    assert out["cohort_size"] == 1


def test_category_summary_excludes_inactive(db: Session) -> None:
    t_self = _tenant(db, "self", cfg={"type": "hotel"})
    _tenant(db, "active-hotel", cfg={"type": "hotel"})
    inactive = _tenant(db, "inactive", cfg={"type": "hotel"})
    inactive.status = "suspended"
    db.commit()

    out = market_insights.category_summary(db, category="hotels", exclude_tenant_id=t_self.id)
    assert out["cohort_size"] == 1  # only active


# ---------- tenant_position ----------


def test_position_no_peers(db: Session) -> None:
    t = _tenant(db, "solo", cfg={"type": "hotel", "rating": 4.5})
    _svc(db, t, price=500)
    out = market_insights.tenant_position(db, t)
    assert out["cohort_size"] == 0
    assert out["positions"] is None


def test_position_price_percentile(db: Session) -> None:
    t_self = _tenant(db, "self", cfg={"type": "hotel", "rating": 4.0})
    _svc(db, t_self, price=800)  # expensive

    p1 = _tenant(db, "p1", cfg={"type": "hotel", "rating": 4.0})
    p2 = _tenant(db, "p2", cfg={"type": "hotel", "rating": 4.0})
    p3 = _tenant(db, "p3", cfg={"type": "hotel", "rating": 4.0})
    _svc(db, p1, price=300)
    _svc(db, p2, price=400)
    _svc(db, p3, price=500)

    out = market_insights.tenant_position(db, t_self)
    pos = out["positions"]["avg_price"]
    assert pos["value"] == 800.0
    # 800 > all 3 peers => 100%
    assert pos["percentile"] == 100.0


def test_position_price_low(db: Session) -> None:
    t_self = _tenant(db, "self", cfg={"type": "hotel", "rating": 4.0})
    _svc(db, t_self, price=100)

    for i, pr in enumerate([300, 400, 500], start=1):
        p = _tenant(db, f"p{i}", cfg={"type": "hotel", "rating": 4.0})
        _svc(db, p, price=pr)

    out = market_insights.tenant_position(db, t_self)
    assert out["positions"]["avg_price"]["percentile"] == 0.0


def test_position_rating_percentile(db: Session) -> None:
    t_self = _tenant(db, "self", cfg={"type": "hotel", "rating": 5.0})
    _svc(db, t_self, price=500)
    for i, r in enumerate([3.5, 4.0, 4.5], start=1):
        p = _tenant(db, f"p{i}", cfg={"type": "hotel", "rating": r})
        _svc(db, p, price=500)

    out = market_insights.tenant_position(db, t_self)
    assert out["positions"]["rating"]["percentile"] == 100.0


def test_position_bookings_30d(db: Session) -> None:
    t_self = _tenant(db, "self", cfg={"type": "hotel"})
    _svc(db, t_self, price=500)
    for i in range(10):
        _booking(db, t_self, days_ago=i + 1, amount=500)

    p1 = _tenant(db, "p1", cfg={"type": "hotel"})
    _svc(db, p1, price=500)
    _booking(db, p1, days_ago=5, amount=500)

    out = market_insights.tenant_position(db, t_self)
    assert out["positions"]["bookings_last_30d"]["value"] == 10.0
    assert out["positions"]["bookings_last_30d"]["percentile"] == 100.0


def test_position_services_count(db: Session) -> None:
    t_self = _tenant(db, "self", cfg={"type": "hotel"})
    for i in range(5):
        _svc(db, t_self, name=f"S{i}", price=500)

    p1 = _tenant(db, "p1", cfg={"type": "hotel"})
    _svc(db, p1, price=500)

    out = market_insights.tenant_position(db, t_self)
    assert out["positions"]["service_count"]["value"] == 5.0
    assert out["positions"]["service_count"]["percentile"] == 100.0


# ---------- region_summary ----------


def test_region_summary(db: Session) -> None:
    t_self = _tenant(db, "self", cfg={"type": "hotel", "location": "Downtown, Dubai, UAE"})
    p1 = _tenant(db, "p1", cfg={"type": "hotel", "location": "Marina, Dubai, UAE"})
    p2 = _tenant(db, "p2", cfg={"type": "restaurant", "location": "Downtown, Dubai, UAE"})
    p3 = _tenant(db, "p3", cfg={"type": "hotel", "location": "Abu Dhabi, UAE"})

    _svc(db, p1, price=600)
    _svc(db, p2, price=800)
    _svc(db, p3, price=400)

    out = market_insights.region_summary(db, region="UAE", exclude_tenant_id=t_self.id)
    assert out["cohort_size"] == 3
    assert out["categories"]["hotels"] == 2
    assert out["categories"]["restaurants"] == 1
    # avg of 600, 800, 400 = 600
    assert out["avg_price"] == 600.0


def test_region_summary_no_region(db: Session) -> None:
    t = _tenant(db, "noregion", cfg={"type": "hotel"})
    out = market_insights.region_summary(db, region="Mars", exclude_tenant_id=t.id)
    assert out["cohort_size"] == 0


# ---------- market_insights (combined) ----------


def test_market_insights_combined(db: Session) -> None:
    t = _tenant(db, "self", cfg={"type": "hotel", "location": "Downtown, Dubai, UAE", "rating": 4.5})
    _svc(db, t, price=500)
    p1 = _tenant(db, "p1", cfg={"type": "hotel", "location": "Marina, Dubai, UAE", "rating": 4.2})
    _svc(db, p1, price=600)

    out = market_insights.market_insights(db, t)
    assert out["tenant_category"] == "hotels"
    assert out["tenant_region"] == "UAE"
    assert out["category_summary"]["cohort_size"] == 1
    assert out["tenant_position"]["cohort_size"] == 1
    assert out["region_summary"]["cohort_size"] == 1


def test_market_insights_no_region(db: Session) -> None:
    t = _tenant(db, "self", cfg={"type": "hotel"})
    out = market_insights.market_insights(db, t)
    assert out["tenant_region"] is None
    assert out["region_summary"] is None
