"""Tests for Business Insights API (Phase 26, Step 5)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


# ---------- Helpers ----------


def _tenant(db: Session, slug: str = "ins") -> Tenant:
    t = Tenant(slug=slug, name="Ins", tier="starter", status="active", config={"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _biz_user(db: Session, tenant: Tenant, *, email: str = "owner@biz.test") -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("OwnerPass123"),
        first_name="O", last_name="X",
        business_role="owner", status="active",
        referral_code=email[:10].upper(),
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _guest(db: Session, tenant: Tenant, email: str = "g@x.com") -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("GuestPass123"),
        first_name="G", last_name="X",
        referral_code=email[:10].upper(),
        status="active",
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _svc(db: Session, tenant: Tenant, *, name: str = "R", capacity: int | None = 2) -> Service:
    s = Service(
        tenant_id=tenant.id, type="room", name=name,
        price=Decimal("500"), currency="AED", capacity=capacity,
        attributes={}, image_urls=[], status="active", display_order=0,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s


def _booking(db: Session, tenant: Tenant, user: User, svc: Service, *, days_ahead: int = 5, nights: int = 2, status: str = "confirmed") -> Booking:
    ci = date.today() + timedelta(days=days_ahead)
    b = Booking(
        tenant_id=tenant.id, user_id=user.id, booking_type="room",
        service_id=svc.id, service_name=svc.name,
        check_in=ci, check_out=ci + timedelta(days=nights), guests=2,
        amount=Decimal("500"), discount=Decimal("0"),
        total_amount=Decimal("1000"), currency="AED",
        status=status, payment_status="paid",
    )
    db.add(b); db.commit(); db.refresh(b)
    return b


def _login(client: TestClient, slug: str, email: str = "owner@biz.test") -> str:
    r = client.post(
        "/business/api/auth/login",
        json={"email": email, "password": "OwnerPass123"},
        headers={"X-Tenant-Slug": slug},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(tok: str, slug: str) -> dict:
    return {"Authorization": f"Bearer {tok}", "X-Tenant-Slug": slug}


# ---------- Auth ----------


@pytest.mark.parametrize("path", [
    "/business/api/insights/occupancy",
    "/business/api/insights/occupancy/trend",
    "/business/api/insights/occupancy/by-service",
    "/business/api/insights/heatmap/day-of-week",
    "/business/api/insights/heatmap/hour-of-day",
    "/business/api/insights/heatmap/calendar",
    "/business/api/insights/revenue/forecast",
    "/business/api/insights/capacity/available",
    "/business/api/insights/capacity/near-full",
])
def test_endpoints_require_auth(client: TestClient, sample_tenant: Tenant, path: str) -> None:
    r = client.get(path, headers={"X-Tenant-Slug": sample_tenant.slug})
    assert r.status_code == 401


# ---------- Occupancy ----------


def test_occupancy_summary(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    s = _svc(db, t, capacity=2)
    g = _guest(db, t)
    # /occupancy looks BACKWARD (last N days), so place the booking in the past
    _booking(db, t, g, s, days_ahead=-5, nights=2)

    tok = _login(client, t.slug)
    r = client.get("/business/api/insights/occupancy?days=30", headers=_h(tok, t.slug))
    assert r.status_code == 200
    body = r.json()
    assert body["total_bookings"] >= 1
    assert "occupancy_pct" in body


def test_occupancy_by_service(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    s = _svc(db, t, name="Room A", capacity=2)
    _svc(db, t, name="No cap", capacity=None)
    tok = _login(client, t.slug)
    r = client.get("/business/api/insights/occupancy/by-service?days=30", headers=_h(tok, t.slug))
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["service_name"] == "Room A"


def test_occupancy_trend(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.get("/business/api/insights/occupancy/trend?days=30", headers=_h(tok, t.slug))
    assert r.status_code == 200
    body = r.json()
    assert body["days"] == 30
    assert "current" in body
    assert "previous" in body


# ---------- Heatmaps ----------


def test_heatmap_day_of_week(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.get("/business/api/insights/heatmap/day-of-week?days=90", headers=_h(tok, t.slug))
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 7


def test_heatmap_hour_of_day(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.get("/business/api/insights/heatmap/hour-of-day?days=90", headers=_h(tok, t.slug))
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 24


def test_heatmap_calendar(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.get("/business/api/insights/heatmap/calendar?days=30", headers=_h(tok, t.slug))
    assert r.status_code == 200
    body = r.json()
    assert body["days"] == 30
    assert len(body["items"]) == 30


# ---------- Revenue forecast ----------


def test_revenue_forecast_metrics_only(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    s = _svc(db, t)
    g = _guest(db, t)
    _booking(db, t, g, s, days_ahead=1, nights=1)

    tok = _login(client, t.slug)
    r = client.get("/business/api/insights/revenue/forecast?days=30", headers=_h(tok, t.slug))
    assert r.status_code == 200
    body = r.json()
    assert "metrics" in body
    assert body["advice"] is None
    assert "expected_revenue" in body["metrics"]


def test_revenue_forecast_with_advice(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    s = _svc(db, t)
    g = _guest(db, t)
    _booking(db, t, g, s, days_ahead=1, nights=1)

    tok = _login(client, t.slug)
    r = client.get("/business/api/insights/revenue/forecast?days=30&with_advice=true", headers=_h(tok, t.slug))
    assert r.status_code == 200
    body = r.json()
    assert body["advice"]  # non-empty


# ---------- Capacity ----------


def test_capacity_available(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    _svc(db, t, capacity=3)
    tok = _login(client, t.slug)
    r = client.get("/business/api/insights/capacity/available?days=7", headers=_h(tok, t.slug))
    assert r.status_code == 200
    body = r.json()
    assert body["total_capacity_per_day"] == 3
    assert len(body["items"]) == 7


def test_capacity_near_full(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.get("/business/api/insights/capacity/near-full?days=7&threshold=90", headers=_h(tok, t.slug))
    assert r.status_code == 200
    body = r.json()
    assert body["threshold_pct"] == 90.0


def test_capacity_next_available(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    s = _svc(db, t, capacity=2)
    tok = _login(client, t.slug)
    r = client.get(f"/business/api/insights/capacity/next-available/{s.id}?guests=1", headers=_h(tok, t.slug))
    assert r.status_code == 200
    body = r.json()
    assert body["service_id"] == s.id
    assert body["next_date"] is not None


def test_capacity_next_available_service_not_found(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.get("/business/api/insights/capacity/next-available/bogus", headers=_h(tok, t.slug))
    assert r.status_code == 404


# ---------- Cross-tenant ----------


def test_cross_tenant_isolation_occupancy(client: TestClient, db: Session) -> None:
    a = _tenant(db, "ins-a")
    b = _tenant(db, "ins-b")
    _biz_user(db, a, email="owner@a.test")
    sb = _svc(db, b, capacity=2)
    gb = _guest(db, b, "gb@x.com")
    _booking(db, b, gb, sb, days_ahead=5, nights=2)

    tok_a = _login(client, a.slug, "owner@a.test")
    r = client.get("/business/api/insights/occupancy?days=30", headers=_h(tok_a, a.slug))
    assert r.status_code == 200
    # A has no bookings of its own
    assert r.json()["total_bookings"] == 0
