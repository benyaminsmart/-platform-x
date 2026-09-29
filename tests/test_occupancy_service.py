"""Tests for Occupancy service (Phase 26, Step 1)."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import occupancy


# ---------- Helpers ----------


def _tenant(db: Session, slug: str = "occ") -> Tenant:
    t = Tenant(slug=slug, name="Occ Biz", tier="starter", status="active",
               config={"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db: Session, tenant: Tenant, email: str = "u@x.com") -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("Pass1234"),
        first_name="U", last_name="X",
        referral_code="USER12345",
        status="active",
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _svc(db: Session, tenant: Tenant, *, name: str = "R", capacity: int | None = 2, status: str = "active") -> Service:
    s = Service(
        tenant_id=tenant.id, type="room", name=name,
        price=Decimal("500"), currency="AED",
        capacity=capacity, attributes={}, image_urls=[],
        status=status, display_order=0,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s


def _booking(
    db: Session, tenant: Tenant, user: User, service: Service | None, *,
    check_in: date, check_out: date, status: str = "confirmed", guests: int = 2,
) -> Booking:
    b = Booking(
        tenant_id=tenant.id, user_id=user.id, booking_type="room",
        service_id=service.id if service else None,
        service_name=service.name if service else "R",
        check_in=check_in, check_out=check_out, guests=guests,
        amount=Decimal("500"), discount=Decimal("0"),
        total_amount=Decimal("500"), currency="AED",
        status=status, payment_status="paid",
    )
    db.add(b); db.commit(); db.refresh(b)
    return b


# ---------- Summary ----------


def test_summary_empty(db: Session) -> None:
    t = _tenant(db)
    out = occupancy.occupancy_summary(db, t, from_date=date(2026, 9, 1), to_date=date(2026, 10, 1))
    assert out["total_bookings"] == 0
    assert out["booked_nights"] == 0
    assert out["occupancy_pct"] == 0.0
    assert out["capacity_nights"] == 0


def test_summary_empty_range(db: Session) -> None:
    t = _tenant(db)
    out = occupancy.occupancy_summary(db, t, from_date=date(2026, 9, 10), to_date=date(2026, 9, 10))
    assert out["days"] == 0
    assert out["occupancy_pct"] == 0.0


def test_summary_single_capacity_service(db: Session) -> None:
    t = _tenant(db)
    _svc(db, t, capacity=2)
    u = _user(db, t)

    # 10-day window; capacity 2/night => 20 capacity_nights
    out = occupancy.occupancy_summary(db, t, from_date=date(2026, 9, 1), to_date=date(2026, 9, 11))
    assert out["capacity_nights"] == 20
    assert out["booked_nights"] == 0
    assert out["occupancy_pct"] == 0.0


def test_summary_with_bookings(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t, capacity=2)
    u = _user(db, t)

    # Book Sept 3-5 (2 nights), capacity 2 => 2 booked of 20 total
    _booking(db, t, u, s, check_in=date(2026, 9, 3), check_out=date(2026, 9, 5))

    out = occupancy.occupancy_summary(db, t, from_date=date(2026, 9, 1), to_date=date(2026, 9, 11))
    assert out["total_bookings"] == 1
    assert out["booked_nights"] == 2
    assert out["capacity_nights"] == 20
    assert out["occupancy_pct"] == 10.0


def test_summary_clamps_bookings_to_window(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t, capacity=1)
    u = _user(db, t)

    # Booking straddles the window: Sept 28 - Oct 3
    _booking(db, t, u, s, check_in=date(2026, 9, 28), check_out=date(2026, 10, 3))

    # Window: Sept 30 - Oct 2 (2 days, capacity 1 => 2 capacity nights)
    out = occupancy.occupancy_summary(db, t, from_date=date(2026, 9, 30), to_date=date(2026, 10, 2))
    # Clamped nights: Sept 30 - Oct 2 => 2 nights
    assert out["booked_nights"] == 2
    assert out["capacity_nights"] == 2
    assert out["occupancy_pct"] == 100.0


def test_summary_excludes_cancelled(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t, capacity=2)
    u = _user(db, t)
    _booking(db, t, u, s, check_in=date(2026, 9, 3), check_out=date(2026, 9, 5), status="cancelled")
    out = occupancy.occupancy_summary(db, t, from_date=date(2026, 9, 1), to_date=date(2026, 9, 11))
    assert out["booked_nights"] == 0


def test_summary_guests_summed(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t, capacity=4)
    u = _user(db, t)
    _booking(db, t, u, s, check_in=date(2026, 9, 3), check_out=date(2026, 9, 5), guests=2)
    _booking(db, t, u, s, check_in=date(2026, 9, 6), check_out=date(2026, 9, 7), guests=3)
    out = occupancy.occupancy_summary(db, t, from_date=date(2026, 9, 1), to_date=date(2026, 9, 11))
    assert out["total_guests"] == 5


def test_summary_no_capacity_services(db: Session) -> None:
    t = _tenant(db)
    # Service without capacity
    _svc(db, t, capacity=None)
    u = _user(db, t)
    _booking(db, t, u, None, check_in=date(2026, 9, 3), check_out=date(2026, 9, 5))
    out = occupancy.occupancy_summary(db, t, from_date=date(2026, 9, 1), to_date=date(2026, 9, 11))
    assert out["capacity_nights"] == 0
    assert out["occupancy_pct"] == 0.0
    assert out["note"]


# ---------- By service ----------


def test_by_service_only_capacity_services(db: Session) -> None:
    t = _tenant(db)
    s1 = _svc(db, t, name="Room A", capacity=2)
    _svc(db, t, name="Item", capacity=None)  # not returned
    out = occupancy.occupancy_by_service(db, t, from_date=date(2026, 9, 1), to_date=date(2026, 9, 11))
    assert len(out) == 1
    assert out[0]["service_name"] == "Room A"


def test_by_service_sorted_by_occupancy(db: Session) -> None:
    t = _tenant(db)
    s_hi = _svc(db, t, name="Hi", capacity=1)
    s_lo = _svc(db, t, name="Lo", capacity=5)
    u = _user(db, t)
    # Hi: 5 nights on cap 1 => 5/10 = 50%
    _booking(db, t, u, s_hi, check_in=date(2026, 9, 1), check_out=date(2026, 9, 6))
    # Lo: 1 night on cap 5 => 1/50 = 2%
    _booking(db, t, u, s_lo, check_in=date(2026, 9, 1), check_out=date(2026, 9, 2))

    out = occupancy.occupancy_by_service(db, t, from_date=date(2026, 9, 1), to_date=date(2026, 9, 11))
    assert out[0]["service_name"] == "Hi"
    assert out[0]["occupancy_pct"] == 50.0
    assert out[1]["service_name"] == "Lo"
    assert out[1]["occupancy_pct"] == 2.0


def test_by_service_empty_range(db: Session) -> None:
    t = _tenant(db)
    _svc(db, t, capacity=2)
    out = occupancy.occupancy_by_service(db, t, from_date=date(2026, 9, 1), to_date=date(2026, 9, 1))
    assert out == []


# ---------- Trend ----------


def test_trend_empty(db: Session) -> None:
    t = _tenant(db)
    out = occupancy.occupancy_trend(db, t, today=date(2026, 9, 15), days=30)
    assert out["days"] == 30
    assert out["current"]["occupancy_pct"] == 0.0
    assert out["previous"]["occupancy_pct"] == 0.0
    assert out["occupancy_delta_pct"] is None


def test_trend_positive_delta(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t, capacity=1)
    u = _user(db, t)
    today = date(2026, 9, 15)
    # Current window: last 30 days before today; 5 nights booked
    _booking(db, t, u, s, check_in=today - timedelta(days=10), check_out=today - timedelta(days=5))
    # Previous window: 0 nights booked
    out = occupancy.occupancy_trend(db, t, today=today, days=30)
    assert out["current"]["booked_nights"] == 5
    assert out["previous"]["booked_nights"] == 0


def test_trend_clamps_days(db: Session) -> None:
    t = _tenant(db)
    out_lo = occupancy.occupancy_trend(db, t, today=date(2026, 9, 15), days=1)
    assert out_lo["days"] == 7
    out_hi = occupancy.occupancy_trend(db, t, today=date(2026, 9, 15), days=9999)
    assert out_hi["days"] == 365
