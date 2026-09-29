"""Tests for the Scoring Engine (Phase 29, Step 2).

Every criterion is tested in isolation with deterministic setups,
plus the weighted overall and the period helpers.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.service import Service
from app.models.subscription import Subscription
from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import hash_password
from app.services import scoring_engine


# ---------- Helpers ----------


def _user(db: Session, tenant: Tenant, email: str = "u@x.com") -> User:
    u = User(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password("Pass1234"),
        first_name="U",
        last_name="One",
        referral_code="ABCDEFGHIJ",
        status="active",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _svc(db: Session, tenant: Tenant, *, typ: str = "room", name: str = "R", price: float = 500, status: str = "active") -> Service:
    s = Service(
        tenant_id=tenant.id,
        type=typ,
        name=name,
        price=Decimal(str(price)),
        currency="AED",
        capacity=2,
        attributes={},
        image_urls=[],
        status=status,
        display_order=0,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _booking(db: Session, tenant: Tenant, user: User, *, ci: date, paid: bool = False) -> Booking:
    b = Booking(
        tenant_id=tenant.id,
        user_id=user.id,
        booking_type="room",
        service_name="R",
        check_in=ci,
        check_out=ci + timedelta(days=1),
        guests=1,
        amount=Decimal("500"),
        discount=Decimal("0"),
        total_amount=Decimal("500"),
        currency="AED",
        status="confirmed" if paid else "pending",
        payment_status="paid" if paid else "pending",
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def _tenant_with_config(db: Session, *, slug: str, cfg: dict, created_days_ago: int = 0) -> Tenant:
    t = Tenant(slug=slug, name=slug, tier="starter", status="active", config=cfg)
    db.add(t)
    db.commit()
    db.refresh(t)
    if created_days_ago:
        t.created_at = datetime.now(timezone.utc) - timedelta(days=created_days_ago)
        db.commit()
        db.refresh(t)
    return t


# ---------- Weights ----------


def test_weights_sum_to_one() -> None:
    assert abs(sum(scoring_engine.WEIGHTS.values()) - 1.0) < 1e-9


# ---------- Customer Satisfaction ----------


def test_cs_no_rating_baseline(db: Session) -> None:
    t = _tenant_with_config(db, slug="t-no-rating", cfg={})
    score, bd = scoring_engine.compute_customer_satisfaction(t)
    assert score == 50.0
    assert "baseline" in bd


def test_cs_high_rating_many_reviews(db: Session) -> None:
    t = _tenant_with_config(db, slug="t-high", cfg={"rating": 4.9, "reviews_count": 500})
    score, _ = scoring_engine.compute_customer_satisfaction(t)
    # base 98, confidence ~1.0 -> ~98
    assert 95.0 <= score <= 100.0


def test_cs_low_reviews_reduces_score(db: Session) -> None:
    t = _tenant_with_config(db, slug="t-new", cfg={"rating": 5.0, "reviews_count": 3})
    score, bd = scoring_engine.compute_customer_satisfaction(t)
    # base 100, low confidence -> much lower
    assert score < 50.0
    assert bd["reviews_count"] == 3


# ---------- Service Quality ----------


def test_sq_empty_tenant(db: Session, sample_tenant: Tenant) -> None:
    score, bd = scoring_engine.compute_service_quality(db, sample_tenant)
    # No services, no config -> close to 0
    assert score == 0.0
    assert bd["total_services"] == 0


def test_sq_with_services_and_profile(db: Session) -> None:
    t = _tenant_with_config(db, slug="t-sq", cfg={
        "type": "hotel",
        "tagline": "Luxury stay",
        "location": "Dubai",
        "cover_image": "x",
        "gallery": ["a"],
        "amenities": ["wifi"],
    })
    _svc(db, t, typ="room", name="Room A")
    _svc(db, t, typ="room", name="Room B")
    _svc(db, t, typ="suite", name="Suite")
    _svc(db, t, typ="room", name="Old", status="inactive")

    score, bd = scoring_engine.compute_service_quality(db, t)
    # activity: 3/4 active -> 22.5
    # diversity: 2 types -> 10
    # profile: 6/6 -> 40
    # total = 72.5
    assert 70.0 <= score <= 75.0
    assert bd["profile_fields_present"] == 6


# ---------- Pricing Competitiveness ----------


def test_pc_no_cohort_baseline(db: Session, sample_tenant: Tenant) -> None:
    _svc(db, sample_tenant, price=500)
    score, bd = scoring_engine.compute_pricing_competitiveness(db, sample_tenant)
    assert score == 60.0
    assert "baseline" in bd


def test_pc_at_market_perfect_score(db: Session) -> None:
    t = _tenant_with_config(db, slug="t-market", cfg={"type": "hotel"})
    _svc(db, t, typ="room", name="Mine", price=500)
    peer = _tenant_with_config(db, slug="peer-1", cfg={"type": "hotel"})
    _svc(db, peer, typ="room", name="P1", price=500)

    score, bd = scoring_engine.compute_pricing_competitiveness(db, t)
    # delta = 0% -> 100
    assert score >= 95.0
    assert bd["cohort_size"] == 1


def test_pc_below_market_by_20pct(db: Session) -> None:
    t = _tenant_with_config(db, slug="t-low", cfg={"type": "hotel"})
    _svc(db, t, typ="room", name="Mine", price=400)
    p1 = _tenant_with_config(db, slug="p1", cfg={"type": "hotel"})
    _svc(db, p1, typ="room", name="P1", price=500)
    p2 = _tenant_with_config(db, slug="p2", cfg={"type": "hotel"})
    _svc(db, p2, typ="room", name="P2", price=500)

    score, bd = scoring_engine.compute_pricing_competitiveness(db, t)
    # delta = -20% -> 100 - 20*2.5 = 50
    assert 48.0 <= score <= 52.0


def test_pc_far_from_market_low_score(db: Session) -> None:
    t = _tenant_with_config(db, slug="t-far", cfg={"type": "hotel"})
    _svc(db, t, typ="room", name="Mine", price=2000)
    p1 = _tenant_with_config(db, slug="pp1", cfg={"type": "hotel"})
    _svc(db, p1, typ="room", name="P1", price=100)
    p2 = _tenant_with_config(db, slug="pp2", cfg={"type": "hotel"})
    _svc(db, p2, typ="room", name="P2", price=100)

    score, _ = scoring_engine.compute_pricing_competitiveness(db, t)
    # delta huge -> 0
    assert score == 0.0


# ---------- Engagement ----------


def test_engagement_empty(db: Session, sample_tenant: Tenant) -> None:
    score, bd = scoring_engine.compute_engagement(db, sample_tenant)
    # No bookings anywhere, no AI -> booking_score=40, ai=0
    assert 35.0 <= score <= 45.0
    assert bd["bookings_last_30d"] == 0


def test_engagement_with_bookings(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant)
    today = date.today()
    for i in range(5):
        _booking(db, sample_tenant, u, ci=today - timedelta(days=i + 1))

    score, bd = scoring_engine.compute_engagement(db, sample_tenant)
    assert bd["bookings_last_30d"] == 5
    assert score >= 70.0


# ---------- Loyalty ----------


def test_loyalty_new_tenant_no_sub(db: Session) -> None:
    t = _tenant_with_config(db, slug="t-new", cfg={})
    score, bd = scoring_engine.compute_loyalty(db, t)
    # Age ~0, no sub, no paid bookings -> ~0
    assert score < 5.0
    assert bd["has_active_subscription"] is False


def test_loyalty_with_subscription_and_paid(db: Session) -> None:
    t = _tenant_with_config(db, slug="t-old", cfg={}, created_days_ago=180)  # 6 months
    u = _user(db, t)
    today = date.today()
    for i in range(5):
        _booking(db, t, u, ci=today - timedelta(days=i + 1), paid=True)

    now = datetime.now(timezone.utc)
    sub = Subscription(
        tenant_id=t.id,
        plan="starter",
        status="active",
        price=Decimal("100"),
        currency="AED",
        billing_cycle="monthly",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )
    db.add(sub)
    db.commit()

    score, bd = scoring_engine.compute_loyalty(db, t)
    # age: 6*3=18, sub: 20, paid: 5 -> 43
    assert 40.0 <= score <= 50.0
    assert bd["has_active_subscription"] is True


# ---------- Overall ----------


def test_compute_score_empty_tenant(db: Session, sample_tenant: Tenant) -> None:
    out = scoring_engine.compute_score(db, sample_tenant)
    assert "overall_score" in out
    assert "criteria_breakdown" in out
    assert out["category"] in ("other", "hotels", "restaurants", "travel", "entertainment")
    # All weights reflected in breakdown
    assert out["criteria_breakdown"]["weights"] == scoring_engine.WEIGHTS


def test_compute_score_category_mapping(db: Session) -> None:
    for typ, cat in [("hotel", "hotels"), ("restaurant", "restaurants"),
                     ("travel_agency", "travel"), ("entertainment", "entertainment")]:
        t = _tenant_with_config(db, slug=f"t-{typ}", cfg={"type": typ})
        out = scoring_engine.compute_score(db, t)
        assert out["category"] == cat


def test_compute_score_overall_bounded(db: Session, sample_tenant: Tenant) -> None:
    out = scoring_engine.compute_score(db, sample_tenant)
    assert 0.0 <= out["overall_score"] <= 100.0
    for key in ["customer_satisfaction", "service_quality",
                "pricing_competitiveness", "engagement", "loyalty"]:
        assert 0.0 <= out[key] <= 100.0


# ---------- Period helpers ----------


def test_current_period_september_2026() -> None:
    start, end = scoring_engine.current_period(date(2026, 9, 15))
    assert start == date(2026, 9, 1)
    assert end == date(2026, 10, 1)


def test_current_period_december_rollover() -> None:
    start, end = scoring_engine.current_period(date(2026, 12, 20))
    assert start == date(2026, 12, 1)
    assert end == date(2027, 1, 1)


def test_previous_period_september() -> None:
    start, end = scoring_engine.previous_period(date(2026, 9, 15))
    assert start == date(2026, 8, 1)
    assert end == date(2026, 9, 1)


def test_previous_period_january() -> None:
    start, end = scoring_engine.previous_period(date(2026, 1, 15))
    assert start == date(2025, 12, 1)
    assert end == date(2026, 1, 1)
