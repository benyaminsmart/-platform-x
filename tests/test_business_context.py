"""Tests for the Business Context Builder (Phase 21, Step 1).

Validates that real DB data is aggregated correctly and that the
prompt flattening produces useful output.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import hash_password
from app.services.ai.business_context import build_business_context, context_to_prompt


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


def _service(db: Session, tenant: Tenant, **kw) -> Service:
    s = Service(
        tenant_id=tenant.id,
        type=kw.get("type", "room"),
        name=kw.get("name", "Room"),
        price=Decimal(str(kw.get("price", 500))),
        currency="AED",
        capacity=kw.get("capacity", 2),
        attributes=kw.get("attributes", {}),
        image_urls=[],
        status=kw.get("status", "active"),
        display_order=kw.get("display_order", 0),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _booking(
    db: Session,
    tenant: Tenant,
    user: User,
    *,
    service_name: str = "Room",
    check_in: date | None = None,
    amount: float = 500,
    status: str = "pending",
    payment_status: str = "pending",
) -> Booking:
    ci = check_in or date.today()
    b = Booking(
        tenant_id=tenant.id,
        user_id=user.id,
        booking_type="room",
        service_id=None,
        service_name=service_name,
        check_in=ci,
        check_out=ci + timedelta(days=1),
        guests=2,
        amount=Decimal(str(amount)),
        discount=Decimal("0"),
        total_amount=Decimal(str(amount)),
        currency="AED",
        status=status,
        payment_status=payment_status,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


# ---------- Empty tenant ----------


def test_context_empty_tenant(db: Session, sample_tenant: Tenant) -> None:
    ctx = build_business_context(db, sample_tenant)

    assert ctx["tenant"]["slug"] == sample_tenant.slug
    assert ctx["tenant"]["dominant_type"] is None
    assert ctx["portfolio"]["total_services"] == 0
    assert ctx["portfolio"]["active_services"] == 0
    assert ctx["portfolio"]["pricing_by_type"] == {}
    assert ctx["portfolio"]["services"] == []
    assert ctx["performance"]["total_bookings"] == 0
    assert ctx["performance"]["confirmed_bookings"] == 0
    assert ctx["performance"]["confirmation_rate_pct"] == 0.0
    assert ctx["performance"]["total_revenue_aed"] == 0.0
    assert ctx["performance"]["avg_booking_value_aed"] == 0.0
    assert ctx["monthly"]["this_month"]["bookings"] == 0
    assert ctx["monthly"]["revenue_growth_pct"] is None
    assert ctx["benchmark"]["cohort_type"] is None
    assert ctx["benchmark"]["cohort_size"] == 0


# ---------- Portfolio + pricing ----------


def test_context_pricing_by_type(db: Session, sample_tenant: Tenant) -> None:
    _service(db, sample_tenant, type="room", name="A", price=100)
    _service(db, sample_tenant, type="room", name="B", price=300)
    _service(db, sample_tenant, type="room", name="C", price=500)
    _service(db, sample_tenant, type="suite", name="D", price=1000)
    _service(db, sample_tenant, type="room", name="Inactive", price=9999, status="inactive")

    ctx = build_business_context(db, sample_tenant)
    p = ctx["portfolio"]["pricing_by_type"]

    assert p["room"]["count"] == 3  # inactive excluded
    assert p["room"]["min"] == 100.0
    assert p["room"]["max"] == 500.0
    assert p["room"]["avg"] == 300.0
    assert p["room"]["median"] == 300.0
    assert p["suite"]["count"] == 1
    assert p["suite"]["avg"] == 1000.0

    # dominant type is "room"
    assert ctx["tenant"]["dominant_type"] == "room"
    assert ctx["portfolio"]["active_services"] == 4
    assert ctx["portfolio"]["total_services"] == 5


# ---------- Performance ----------


def test_context_performance_and_confirmation_rate(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant)
    _booking(db, sample_tenant, u, status="confirmed", payment_status="paid", amount=200)
    _booking(db, sample_tenant, u, status="confirmed", payment_status="paid", amount=300)
    _booking(db, sample_tenant, u, status="pending", payment_status="pending", amount=999)
    _booking(db, sample_tenant, u, status="cancelled", payment_status="pending", amount=50)

    ctx = build_business_context(db, sample_tenant)
    perf = ctx["performance"]

    assert perf["total_bookings"] == 4
    assert perf["confirmed_bookings"] == 2
    assert perf["cancelled_bookings"] == 1
    assert perf["confirmation_rate_pct"] == 50.0
    assert perf["total_revenue_aed"] == 500.0  # only paid
    assert perf["avg_booking_value_aed"] == 250.0  # 500 / 2 paid


def test_context_top_services(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant)
    _booking(db, sample_tenant, u, service_name="Deluxe")
    _booking(db, sample_tenant, u, service_name="Deluxe")
    _booking(db, sample_tenant, u, service_name="Deluxe")
    _booking(db, sample_tenant, u, service_name="Standard")
    _booking(db, sample_tenant, u, service_name="Standard")
    _booking(db, sample_tenant, u, service_name="Suite")

    ctx = build_business_context(db, sample_tenant)
    tops = ctx["performance"]["top_services"]
    assert tops[0]["name"] == "Deluxe"
    assert tops[0]["bookings"] == 3
    assert tops[1]["name"] == "Standard"
    assert tops[1]["bookings"] == 2


# ---------- Monthly growth ----------


def test_context_monthly_growth(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant)
    today = date.today()
    # This month
    this_month_ci = today.replace(day=min(today.day, 15))
    # Prev month
    first_this = today.replace(day=1)
    prev_month_ci = (first_this - timedelta(days=1)).replace(day=10)

    _booking(db, sample_tenant, u, check_in=this_month_ci, amount=1000,
             status="confirmed", payment_status="paid")
    _booking(db, sample_tenant, u, check_in=prev_month_ci, amount=500,
             status="confirmed", payment_status="paid")

    ctx = build_business_context(db, sample_tenant)
    m = ctx["monthly"]
    assert m["this_month"]["bookings"] == 1
    assert m["this_month"]["revenue_aed"] == 1000.0
    assert m["prev_month"]["bookings"] == 1
    assert m["prev_month"]["revenue_aed"] == 500.0
    assert m["revenue_growth_pct"] == 100.0
    assert m["bookings_growth_pct"] == 0.0


# ---------- Rolling 30d ----------


def test_context_rolling_30d(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant)
    today = date.today()
    # last 30 days
    _booking(db, sample_tenant, u, check_in=today - timedelta(days=5))
    _booking(db, sample_tenant, u, check_in=today - timedelta(days=20))
    # prev 30
    _booking(db, sample_tenant, u, check_in=today - timedelta(days=45))

    ctx = build_business_context(db, sample_tenant)
    r = ctx["rolling_30d"]
    assert r["bookings_last_30d"] == 2
    assert r["bookings_prev_30d"] == 1
    assert r["growth_pct"] == 100.0


# ---------- Benchmark ----------


def test_context_benchmark_anonymized(db: Session, sample_tenant: Tenant) -> None:
    # Self: 2 rooms, avg 300
    _service(db, sample_tenant, type="room", name="Mine A", price=200)
    _service(db, sample_tenant, type="room", name="Mine B", price=400)

    # Peers
    peer1 = Tenant(slug="peer-1", name="Peer 1", tier="starter", status="active", config={})
    peer2 = Tenant(slug="peer-2", name="Peer 2", tier="starter", status="active", config={})
    db.add_all([peer1, peer2])
    db.commit()
    _service(db, peer1, type="room", name="P1", price=500)
    _service(db, peer2, type="room", name="P2", price=500)

    ctx = build_business_context(db, sample_tenant)
    b = ctx["benchmark"]
    assert b["cohort_type"] == "room"
    assert b["cohort_size"] == 2
    assert b["avg_price"] == 500.0
    assert b["median_price"] == 500.0
    # Self avg = 300, cohort = 500 → -40%
    assert b["tenant_price_vs_cohort_pct"] == -40.0
    # Never leaks peer identity
    assert "peer" not in str(b).lower()
    assert "Peer" not in str(b)


def test_context_benchmark_excludes_inactive_peers(db: Session, sample_tenant: Tenant) -> None:
    _service(db, sample_tenant, type="room", name="Mine", price=100)

    active_peer = Tenant(slug="a", name="A", tier="starter", status="active", config={})
    inactive_peer = Tenant(slug="b", name="B", tier="starter", status="suspended", config={})
    db.add_all([active_peer, inactive_peer])
    db.commit()
    _service(db, active_peer, type="room", name="AP", price=200)
    _service(db, inactive_peer, type="room", name="IP", price=9999)

    ctx = build_business_context(db, sample_tenant)
    assert ctx["benchmark"]["cohort_size"] == 1
    assert ctx["benchmark"]["avg_price"] == 200.0  # inactive excluded


# ---------- Prompt flattening ----------


def test_context_to_prompt_smoke(db: Session, sample_tenant: Tenant) -> None:
    _service(db, sample_tenant, type="room", name="R1", price=500)
    u = _user(db, sample_tenant)
    _booking(db, sample_tenant, u, status="confirmed", payment_status="paid")

    ctx = build_business_context(db, sample_tenant)
    text = context_to_prompt(ctx)

    assert "BUSINESS:" in text
    assert sample_tenant.name in text
    assert "SERVICES:" in text
    assert "BOOKINGS:" in text
    assert "REVENUE" in text
    assert "AED" in text


def test_context_to_prompt_empty_tenant(db: Session, sample_tenant: Tenant) -> None:
    ctx = build_business_context(db, sample_tenant)
    text = context_to_prompt(ctx)
    assert "BUSINESS:" in text
    assert sample_tenant.name in text
    # no crash on empty
    assert "SERVICES: 0 active / 0 total" in text
