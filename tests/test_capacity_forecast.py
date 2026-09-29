"""Tests for Predictive Capacity service (Phase 26, Step 4)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import capacity_forecast


# ---------- Helpers ----------


def _tenant(db: Session, slug: str = "cap") -> Tenant:
    t = Tenant(slug=slug, name="Cap", tier="starter", status="active", config={"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db: Session, tenant: Tenant, email: str = "u@x.com") -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("Pass1234"),
        first_name="U", last_name="X",
        referral_code=email[:10].upper(),
        status="active",
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _svc(db: Session, tenant: Tenant, *, name: str = "R", capacity: int | None = 2, status: str = "active") -> Service:
    s = Service(
        tenant_id=tenant.id, type="room", name=name,
        price=Decimal("500"), currency="AED", capacity=capacity,
        attributes={}, image_urls=[], status=status, display_order=0,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s


def _booking(db: Session, tenant: Tenant, user: User, svc: Service, *, ci: date, co: date, status: str = "confirmed") -> Booking:
    b = Booking(
        tenant_id=tenant.id, user_id=user.id, booking_type="room",
        service_id=svc.id, service_name=svc.name,
        check_in=ci, check_out=co, guests=1,
        amount=Decimal("500"), discount=Decimal("0"),
        total_amount=Decimal("500"), currency="AED",
        status=status, payment_status="paid",
    )
    db.add(b); db.commit(); db.refresh(b)
    return b


# ---------- available_capacity ----------


def test_available_empty_range(db: Session) -> None:
    t = _tenant(db)
    out = capacity_forecast.available_capacity(
        db, t, from_date=date(2026, 9, 10), to_date=date(2026, 9, 10)
    )
    assert out["days"] == 0
    assert out["items"] == []


def test_available_no_capacity_services(db: Session) -> None:
    t = _tenant(db)
    _svc(db, t, capacity=None)
    out = capacity_forecast.available_capacity(
        db, t, from_date=date(2026, 9, 1), to_date=date(2026, 9, 4)
    )
    assert out["total_capacity_per_day"] == 0
    assert out["note"]


def test_available_full_capacity(db: Session) -> None:
    t = _tenant(db)
    _svc(db, t, capacity=2)
    out = capacity_forecast.available_capacity(
        db, t, from_date=date(2026, 9, 1), to_date=date(2026, 9, 4)
    )
    assert out["total_capacity_per_day"] == 2
    assert out["days"] == 3
    assert len(out["items"]) == 3
    for x in out["items"]:
        assert x["available"] == 2
        assert x["occupancy_pct"] == 0.0
    assert out["summary"]["min_available"] == 2
    assert out["summary"]["max_available"] == 2


def test_available_with_bookings(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t, capacity=3)
    u = _user(db, t)

    # 2 bookings covering Sep 1-3 and Sep 2-3
    _booking(db, t, u, s, ci=date(2026, 9, 1), co=date(2026, 9, 3))
    _booking(db, t, u, s, ci=date(2026, 9, 2), co=date(2026, 9, 3))

    out = capacity_forecast.available_capacity(
        db, t, from_date=date(2026, 9, 1), to_date=date(2026, 9, 4)
    )
    # Sep 1: 1 booked -> 2 available
    # Sep 2: 2 booked -> 1 available
    # Sep 3: 0 booked -> 3 available
    assert out["items"][0]["available"] == 2
    assert out["items"][1]["available"] == 1
    assert out["items"][2]["available"] == 3
    assert out["summary"]["min_available"] == 1
    assert out["summary"]["max_available"] == 3


def test_available_never_negative(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t, capacity=1)
    u = _user(db, t)
    # Overbook: 3 bookings on the same day with capacity 1
    _booking(db, t, u, s, ci=date(2026, 9, 1), co=date(2026, 9, 2))
    _booking(db, t, u, s, ci=date(2026, 9, 1), co=date(2026, 9, 2))
    _booking(db, t, u, s, ci=date(2026, 9, 1), co=date(2026, 9, 2))
    out = capacity_forecast.available_capacity(
        db, t, from_date=date(2026, 9, 1), to_date=date(2026, 9, 2)
    )
    assert out["items"][0]["available"] == 0


def test_available_excludes_cancelled(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t, capacity=1)
    u = _user(db, t)
    _booking(db, t, u, s, ci=date(2026, 9, 1), co=date(2026, 9, 2), status="cancelled")
    out = capacity_forecast.available_capacity(
        db, t, from_date=date(2026, 9, 1), to_date=date(2026, 9, 2)
    )
    assert out["items"][0]["available"] == 1


# ---------- near_fully_booked ----------


def test_near_fully_booked_detects_high_occupancy(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t, capacity=1)
    u = _user(db, t)
    _booking(db, t, u, s, ci=date(2026, 9, 1), co=date(2026, 9, 3))

    out = capacity_forecast.near_fully_booked(
        db, t, from_date=date(2026, 9, 1), to_date=date(2026, 9, 5), threshold_pct=90.0
    )
    assert out["count"] == 2  # Sep 1 and Sep 2 at 100%
    assert all(x["occupancy_pct"] >= 90.0 for x in out["items"])


def test_near_fully_booked_empty(db: Session) -> None:
    t = _tenant(db)
    _svc(db, t, capacity=5)
    out = capacity_forecast.near_fully_booked(
        db, t, from_date=date(2026, 9, 1), to_date=date(2026, 9, 5), threshold_pct=90.0
    )
    assert out["count"] == 0


# ---------- next_available_date ----------


def test_next_available_no_capacity_service(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t, capacity=None)
    out = capacity_forecast.next_available_date(
        db, t, service_id=s.id, from_date=date(2026, 9, 1)
    )
    assert out["next_date"] is None
    assert "no capacity" in (out["note"] or "")


def test_next_available_service_not_found(db: Session) -> None:
    t = _tenant(db)
    with pytest.raises(ValueError):
        capacity_forecast.next_available_date(
            db, t, service_id="bogus", from_date=date(2026, 9, 1)
        )


def test_next_available_when_empty(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t, capacity=2)
    out = capacity_forecast.next_available_date(
        db, t, service_id=s.id, from_date=date(2026, 9, 1)
    )
    assert out["next_date"] == "2026-09-01"


def test_next_available_skips_full_days(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t, capacity=1)
    u = _user(db, t)
    # Sep 1-3 booked fully (capacity 1)
    _booking(db, t, u, s, ci=date(2026, 9, 1), co=date(2026, 9, 3))

    out = capacity_forecast.next_available_date(
        db, t, service_id=s.id, from_date=date(2026, 9, 1)
    )
    assert out["next_date"] == "2026-09-03"


def test_next_available_guests_exceed_capacity(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t, capacity=2)
    out = capacity_forecast.next_available_date(
        db, t, service_id=s.id, guests=5, from_date=date(2026, 9, 1)
    )
    assert out["next_date"] is None
    assert "exceed" in (out["note"] or "")


def test_next_available_no_availability_in_window(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t, capacity=1)
    u = _user(db, t)
    # Book 400 days solid
    _booking(db, t, u, s, ci=date(2026, 9, 1), co=date(2027, 10, 6))

    out = capacity_forecast.next_available_date(
        db, t, service_id=s.id, from_date=date(2026, 9, 1), max_search_days=30
    )
    assert out["next_date"] is None
    assert "no availability" in (out["note"] or "")


# ---------- Cross-tenant ----------


def test_cross_tenant_isolation(db: Session) -> None:
    t1 = _tenant(db, "cap-a")
    t2 = _tenant(db, "cap-b")
    s1 = _svc(db, t1, capacity=1)
    s2 = _svc(db, t2, capacity=1)
    u1 = _user(db, t1, "a@x.com")
    u2 = _user(db, t2, "b@x.com")

    _booking(db, t1, u1, s1, ci=date(2026, 9, 1), co=date(2026, 9, 2))
    _booking(db, t2, u2, s2, ci=date(2026, 9, 1), co=date(2026, 9, 2))

    o1 = capacity_forecast.available_capacity(
        db, t1, from_date=date(2026, 9, 1), to_date=date(2026, 9, 2)
    )
    o2 = capacity_forecast.available_capacity(
        db, t2, from_date=date(2026, 9, 1), to_date=date(2026, 9, 2)
    )
    # Both have 0 available (they each have one booking on their own service)
    assert o1["items"][0]["available"] == 0
    assert o2["items"][0]["available"] == 0
