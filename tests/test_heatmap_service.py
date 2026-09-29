"""Tests for Heatmap service (Phase 26, Step 2)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import heatmap


# ---------- Helpers ----------


def _tenant(db: Session, slug: str = "hm") -> Tenant:
    t = Tenant(slug=slug, name="HM", tier="starter", status="active", config={"type": "hotel"})
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


def _svc(db: Session, tenant: Tenant) -> Service:
    s = Service(
        tenant_id=tenant.id, type="room", name="R",
        price=Decimal("500"), currency="AED", capacity=2,
        attributes={}, image_urls=[], status="active", display_order=0,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s


def _booking(
    db: Session, tenant: Tenant, user: User, svc: Service, *,
    check_in: date, amount: float = 500,
    created_at: datetime | None = None,
    status: str = "confirmed",
) -> Booking:
    b = Booking(
        tenant_id=tenant.id, user_id=user.id, booking_type="room",
        service_id=svc.id, service_name=svc.name,
        check_in=check_in, check_out=check_in + timedelta(days=1),
        guests=1, amount=Decimal(str(amount)), discount=Decimal("0"),
        total_amount=Decimal(str(amount)), currency="AED",
        status=status, payment_status="paid",
    )
    db.add(b); db.commit(); db.refresh(b)
    if created_at:
        # ORM may use the default on insert; force the created_at explicitly.
        from sqlalchemy import update
        db.execute(update(Booking).where(Booking.id == b.id).values(created_at=created_at))
        db.commit()
        db.refresh(b)
    return b


# ---------- Day of week ----------


def test_dow_empty(db: Session) -> None:
    t = _tenant(db)
    out = heatmap.day_of_week_heatmap(db, t, today=date(2026, 9, 15), days=90)
    assert out["total_bookings"] == 0
    assert len(out["items"]) == 7
    assert all(x["bookings"] == 0 for x in out["items"])


def test_dow_distribution(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t)
    u = _user(db, t)
    today = date(2026, 9, 15)  # Tuesday

    # Create bookings on known weekdays within last 90 days
    # 2026-09-12 is Saturday (weekday=5)
    _booking(db, t, u, s, check_in=date(2026, 9, 12), amount=1000)
    _booking(db, t, u, s, check_in=date(2026, 9, 12), amount=500)
    # 2026-09-13 is Sunday (weekday=6)
    _booking(db, t, u, s, check_in=date(2026, 9, 13), amount=200)

    out = heatmap.day_of_week_heatmap(db, t, today=today, days=90)
    assert out["total_bookings"] == 3
    sat = next(x for x in out["items"] if x["weekday"] == 5)
    sun = next(x for x in out["items"] if x["weekday"] == 6)
    assert sat["bookings"] == 2
    assert sat["revenue_aed"] == 1500.0
    assert sun["bookings"] == 1
    assert sun["revenue_aed"] == 200.0
    # Share pct
    assert sat["share_pct"] == round((2 / 3) * 100, 2)


def test_dow_excludes_cancelled(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t)
    u = _user(db, t)
    today = date(2026, 9, 15)
    _booking(db, t, u, s, check_in=date(2026, 9, 12), status="cancelled")
    out = heatmap.day_of_week_heatmap(db, t, today=today, days=90)
    assert out["total_bookings"] == 0


# ---------- Hour of day ----------


def test_hod_empty(db: Session) -> None:
    t = _tenant(db)
    out = heatmap.hour_of_day_heatmap(db, t, today=date(2026, 9, 15), days=90)
    assert out["total_bookings"] == 0
    assert len(out["items"]) == 24


def test_hod_distribution(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t)
    u = _user(db, t)
    today = date(2026, 9, 15)

    # Create bookings with known created_at hours (UTC)
    base = datetime(2026, 9, 10, 14, 0, tzinfo=timezone.utc)
    _booking(db, t, u, s, check_in=date(2026, 9, 12), created_at=base)
    _booking(db, t, u, s, check_in=date(2026, 9, 12), created_at=base.replace(hour=14))
    _booking(db, t, u, s, check_in=date(2026, 9, 12), created_at=base.replace(hour=9))

    out = heatmap.hour_of_day_heatmap(db, t, today=today, days=90)
    assert out["total_bookings"] == 3
    h14 = next(x for x in out["items"] if x["hour"] == 14)
    h09 = next(x for x in out["items"] if x["hour"] == 9)
    assert h14["bookings"] == 2
    assert h09["bookings"] == 1


# ---------- Calendar ----------


def test_calendar_empty_fills_range(db: Session) -> None:
    t = _tenant(db)
    out = heatmap.calendar_heatmap(db, t, today=date(2026, 9, 15), days=30)
    # items length = days (window is [to_date - days, to_date))
    assert len(out["items"]) == 30
    assert all(x["bookings"] == 0 for x in out["items"])
    assert out["peak"] is not None  # peak exists (first item)


def test_calendar_marks_peak(db: Session) -> None:
    t = _tenant(db)
    s = _svc(db, t)
    u = _user(db, t)
    today = date(2026, 9, 15)

    _booking(db, t, u, s, check_in=date(2026, 9, 12))
    _booking(db, t, u, s, check_in=date(2026, 9, 12))
    _booking(db, t, u, s, check_in=date(2026, 9, 12))
    _booking(db, t, u, s, check_in=date(2026, 9, 13))

    out = heatmap.calendar_heatmap(db, t, today=today, days=30)
    assert out["peak"]["date"] == "2026-09-12"
    assert out["peak"]["bookings"] == 3


def test_calendar_clamps_days(db: Session) -> None:
    t = _tenant(db)
    lo = heatmap.calendar_heatmap(db, t, today=date(2026, 9, 15), days=1)
    assert lo["days"] == 7
    hi = heatmap.calendar_heatmap(db, t, today=date(2026, 9, 15), days=9999)
    assert hi["days"] == 365


# ---------- Cross-tenant ----------


def test_cross_tenant_isolation(db: Session) -> None:
    t1 = _tenant(db, "hm-a")
    t2 = _tenant(db, "hm-b")
    s1 = _svc(db, t1)
    s2 = _svc(db, t2)
    u1 = _user(db, t1, "a@x.com")
    u2 = _user(db, t2, "b@x.com")
    today = date(2026, 9, 15)

    _booking(db, t1, u1, s1, check_in=date(2026, 9, 12))
    _booking(db, t2, u2, s2, check_in=date(2026, 9, 12))
    _booking(db, t2, u2, s2, check_in=date(2026, 9, 12))

    out_a = heatmap.day_of_week_heatmap(db, t1, today=today, days=90)
    out_b = heatmap.day_of_week_heatmap(db, t2, today=today, days=90)
    assert out_a["total_bookings"] == 1
    assert out_b["total_bookings"] == 2
