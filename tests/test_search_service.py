"""Tests for Search service (Wave 0, Step 1)."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services import search_service


# ---------- Helpers ----------


def _tenant(db: Session, slug: str, *, cfg: dict | None = None, status: str = "active") -> Tenant:
    t = Tenant(slug=slug, name=f"Name-{slug}", tier="starter", status=status, config=cfg or {"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db: Session, tenant: Tenant, *, name: str = "R", price: float = 500, capacity: int | None = 2, status: str = "active", typ: str = "room") -> Service:
    s = Service(
        tenant_id=tenant.id, type=typ, name=name,
        price=Decimal(str(price)), currency="AED", capacity=capacity,
        attributes={}, image_urls=[], status=status, display_order=0,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s


def _guest(db: Session, tenant: Tenant, email: str) -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("Pass1234"),
        first_name="U", last_name="X",
        referral_code=email[:10].upper(),
        status="active",
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


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


# ---------- Basic ----------


def test_search_empty(db: Session) -> None:
    out = search_service.search_services(db)
    assert out["total"] == 0
    assert out["items"] == []


def test_search_returns_active_services(db: Session) -> None:
    t = _tenant(db, "s1")
    _svc(db, t, name="A")
    _svc(db, t, name="B", status="inactive")
    out = search_service.search_services(db)
    assert out["total"] == 1
    assert out["items"][0]["service_name"] == "A"


def test_search_excludes_inactive_tenants(db: Session) -> None:
    t1 = _tenant(db, "active")
    t2 = _tenant(db, "inactive", status="suspended")
    _svc(db, t1, name="Visible")
    _svc(db, t2, name="Hidden")
    out = search_service.search_services(db)
    assert out["total"] == 1
    assert out["items"][0]["service_name"] == "Visible"


def test_search_filter_by_slug(db: Session) -> None:
    t1 = _tenant(db, "h1")
    t2 = _tenant(db, "h2")
    _svc(db, t1, name="A")
    _svc(db, t2, name="B")
    out = search_service.search_services(db, tenant_slug="h1")
    assert out["total"] == 1
    assert out["items"][0]["tenant_slug"] == "h1"


def test_search_filter_by_category(db: Session) -> None:
    t_hotel = _tenant(db, "hh", cfg={"type": "hotel"})
    t_rest = _tenant(db, "rr", cfg={"type": "restaurant"})
    _svc(db, t_hotel, name="Hotel Room")
    _svc(db, t_rest, name="Restaurant Table", typ="table")

    hotels = search_service.search_services(db, category="hotels")
    assert hotels["total"] == 1
    assert hotels["items"][0]["category"] == "hotels"

    restaurants = search_service.search_services(db, category="restaurants")
    assert restaurants["total"] == 1
    assert restaurants["items"][0]["category"] == "restaurants"


def test_search_filter_by_price_range(db: Session) -> None:
    t = _tenant(db, "p1")
    _svc(db, t, name="Cheap", price=100)
    _svc(db, t, name="Mid", price=500)
    _svc(db, t, name="Expensive", price=2000)

    cheap = search_service.search_services(db, max_price=300)
    assert cheap["total"] == 1
    assert cheap["items"][0]["service_name"] == "Cheap"

    mid = search_service.search_services(db, min_price=200, max_price=1000)
    assert mid["total"] == 1
    assert mid["items"][0]["service_name"] == "Mid"


def test_search_filter_by_guests(db: Session) -> None:
    t = _tenant(db, "g1")
    _svc(db, t, name="Small", capacity=2)
    _svc(db, t, name="Large", capacity=6)
    _svc(db, t, name="NoCap", capacity=None)

    out = search_service.search_services(db, guests=4)
    names = [i["service_name"] for i in out["items"]]
    assert "Small" not in names
    assert "Large" in names
    assert "NoCap" in names  # unlimited capacity services always pass


def test_search_sort_price_asc(db: Session) -> None:
    t = _tenant(db, "srt")
    _svc(db, t, name="B", price=800)
    _svc(db, t, name="A", price=200)
    _svc(db, t, name="C", price=500)
    out = search_service.search_services(db, sort="price_asc")
    assert [i["service_name"] for i in out["items"]] == ["A", "C", "B"]


def test_search_sort_price_desc(db: Session) -> None:
    t = _tenant(db, "srt2")
    _svc(db, t, name="B", price=800)
    _svc(db, t, name="A", price=200)
    out = search_service.search_services(db, sort="price_desc")
    assert [i["service_name"] for i in out["items"]] == ["B", "A"]


def test_search_sort_rating(db: Session) -> None:
    t1 = _tenant(db, "r1", cfg={"type": "hotel", "rating": 3.5})
    t2 = _tenant(db, "r2", cfg={"type": "hotel", "rating": 4.9})
    t3 = _tenant(db, "r3", cfg={"type": "hotel", "rating": 4.2})
    _svc(db, t1, name="A")
    _svc(db, t2, name="B")
    _svc(db, t3, name="C")
    out = search_service.search_services(db, sort="rating")
    assert [i["tenant_slug"] for i in out["items"]] == ["r2", "r3", "r1"]


def test_search_pagination(db: Session) -> None:
    t = _tenant(db, "pag")
    for i in range(7):
        _svc(db, t, name=f"S{i}")
    page1 = search_service.search_services(db, page=1, page_size=3)
    page2 = search_service.search_services(db, page=2, page_size=3)
    assert page1["total"] == 7
    assert len(page1["items"]) == 3
    assert len(page2["items"]) == 3


# ---------- Date availability ----------


def test_search_availability_excludes_full(db: Session) -> None:
    t = _tenant(db, "avail")
    s = _svc(db, t, name="Room A", capacity=1)
    g = _guest(db, t, "g1@x.com")

    # Book it fully for 5 days
    ci = date.today() + timedelta(days=10)
    co = date.today() + timedelta(days=15)
    _booking(db, t, g, s, ci=ci, co=co)

    # Search for the same window -> should be excluded
    out = search_service.search_services(db, check_in=ci, check_out=co)
    assert out["total"] == 0


def test_search_availability_includes_free_window(db: Session) -> None:
    t = _tenant(db, "avail2")
    s = _svc(db, t, name="Room B", capacity=1)
    g = _guest(db, t, "g2@x.com")

    # Booked days 5-10
    _booking(db, t, g, s, ci=date.today() + timedelta(days=5), co=date.today() + timedelta(days=10))

    # Search for days 15-20 -> should be available
    out = search_service.search_services(
        db,
        check_in=date.today() + timedelta(days=15),
        check_out=date.today() + timedelta(days=20),
    )
    assert out["total"] == 1
    assert out["items"][0]["service_name"] == "Room B"


def test_search_availability_with_capacity_2(db: Session) -> None:
    t = _tenant(db, "avail3")
    s = _svc(db, t, name="Room C", capacity=2)
    g1 = _guest(db, t, "gc1@x.com")
    g2 = _guest(db, t, "gc2@x.com")

    ci = date.today() + timedelta(days=20)
    co = date.today() + timedelta(days=25)
    _booking(db, t, g1, s, ci=ci, co=co)
    # Only 1 booked of 2 -> still available
    out = search_service.search_services(db, check_in=ci, check_out=co)
    assert out["total"] == 1

    # Now book the second
    _booking(db, t, g2, s, ci=ci, co=co)
    out2 = search_service.search_services(db, check_in=ci, check_out=co)
    assert out2["total"] == 0


def test_search_availability_ignores_cancelled(db: Session) -> None:
    t = _tenant(db, "avail4")
    s = _svc(db, t, name="Room D", capacity=1)
    g = _guest(db, t, "gc@x.com")

    ci = date.today() + timedelta(days=30)
    co = date.today() + timedelta(days=32)
    _booking(db, t, g, s, ci=ci, co=co, status="cancelled")

    out = search_service.search_services(db, check_in=ci, check_out=co)
    assert out["total"] == 1


def test_search_no_capacity_service_always_passes(db: Session) -> None:
    t = _tenant(db, "nocap", cfg={"type": "restaurant"})
    _svc(db, t, name="Table", capacity=None, typ="table")
    out = search_service.search_services(
        db,
        check_in=date.today() + timedelta(days=1),
        check_out=date.today() + timedelta(days=2),
    )
    assert out["total"] == 1


# ---------- Validation ----------


def test_search_invalid_sort_defaults_to_popular(db: Session) -> None:
    t = _tenant(db, "vsort")
    _svc(db, t, name="A")
    out = search_service.search_services(db, sort="bogus")
    assert out["sort"] == "popular"


def test_search_unknown_category_returns_empty(db: Session) -> None:
    t = _tenant(db, "uc")
    _svc(db, t, name="A")
    out = search_service.search_services(db, category="does-not-exist")
    assert out["total"] == 0
