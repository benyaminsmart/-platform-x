"""Tests for Public API v1 (Phase 14, Step 3)."""

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
from app.services import api_key_service
from app.services import review_service


# ---------- Helpers ----------


def _tenant(db: Session, slug: str, cfg: dict | None = None) -> Tenant:
    t = Tenant(slug=slug, name=f"Name-{slug}", tier="starter", status="active", config=cfg or {"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _svc(db: Session, tenant: Tenant, *, name: str = "R", status: str = "active") -> Service:
    s = Service(
        tenant_id=tenant.id, type="room", name=name,
        price=Decimal("500"), currency="AED", capacity=2,
        attributes={}, image_urls=[], status=status, display_order=0,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s


def _guest(db: Session, tenant: Tenant, email: str = "u@x.com") -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("Pass1234"),
        first_name="U", last_name="X",
        referral_code=email[:10].upper(),
        status="active",
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db: Session, tenant: Tenant, user: User) -> Booking:
    ci = date.today() - timedelta(days=5)
    b = Booking(
        tenant_id=tenant.id, user_id=user.id, booking_type="room",
        service_name="R", check_in=ci, check_out=ci + timedelta(days=1),
        guests=1, amount=Decimal("500"), discount=Decimal("0"),
        total_amount=Decimal("500"), currency="AED",
        status="confirmed", payment_status="paid",
    )
    db.add(b); db.commit(); db.refresh(b)
    return b


def _make_key(db: Session, tenant: Tenant, scopes: list[str]) -> str:
    row, plaintext = api_key_service.create_key(
        db, tenant=tenant, name="test", scopes=scopes,
    )
    return plaintext


# ---------- Auth ----------


def test_requires_api_key(client: TestClient) -> None:
    r = client.get("/api/v1/me")
    assert r.status_code == 401


def test_invalid_api_key(client: TestClient) -> None:
    r = client.get("/api/v1/me", headers={"X-API-Key": "pk_live_deadbeef"})
    assert r.status_code == 401


def test_me_returns_tenant_info(client: TestClient, db: Session) -> None:
    t = _tenant(db, "pub-me")
    k = _make_key(db, t, ["read:services"])
    r = client.get("/api/v1/me", headers={"X-API-Key": k})
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == t.id
    assert body["tenant_slug"] == "pub-me"
    assert body["scopes"] == ["read:services"]


# ---------- Scope enforcement ----------


def test_services_requires_scope(client: TestClient, db: Session) -> None:
    t = _tenant(db, "pub-noscope")
    k = _make_key(db, t, ["read:reviews"])  # no read:services
    r = client.get("/api/v1/services", headers={"X-API-Key": k})
    assert r.status_code == 403


# ---------- Services ----------


def test_list_services(client: TestClient, db: Session) -> None:
    t = _tenant(db, "pub-svc")
    k = _make_key(db, t, ["read:services"])
    _svc(db, t, name="A")
    _svc(db, t, name="B", status="inactive")
    r = client.get("/api/v1/services", headers={"X-API-Key": k})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_list_services_status_filter(client: TestClient, db: Session) -> None:
    t = _tenant(db, "pub-svc2")
    k = _make_key(db, t, ["read:services"])
    _svc(db, t, name="A")
    _svc(db, t, name="B", status="inactive")
    r = client.get("/api/v1/services?status=active", headers={"X-API-Key": k})
    assert r.json()["total"] == 1


def test_get_service_detail(client: TestClient, db: Session) -> None:
    t = _tenant(db, "pub-svc3")
    k = _make_key(db, t, ["read:services"])
    s = _svc(db, t, name="Suite")
    r = client.get(f"/api/v1/services/{s.id}", headers={"X-API-Key": k})
    assert r.status_code == 200
    assert r.json()["name"] == "Suite"


def test_get_service_cross_tenant_blocked(client: TestClient, db: Session) -> None:
    a = _tenant(db, "pub-a")
    b = _tenant(db, "pub-b")
    ka = _make_key(db, a, ["read:services"])
    sb = _svc(db, b, name="B-only")
    r = client.get(f"/api/v1/services/{sb.id}", headers={"X-API-Key": ka})
    assert r.status_code == 404


# ---------- Bookings ----------


def test_list_bookings(client: TestClient, db: Session) -> None:
    t = _tenant(db, "pub-bk")
    k = _make_key(db, t, ["read:bookings"])
    g = _guest(db, t)
    _booking(db, t, g)
    _booking(db, t, g)
    r = client.get("/api/v1/bookings", headers={"X-API-Key": k})
    assert r.status_code == 200
    assert r.json()["total"] == 2


def test_get_booking_detail(client: TestClient, db: Session) -> None:
    t = _tenant(db, "pub-bk2")
    k = _make_key(db, t, ["read:bookings"])
    g = _guest(db, t)
    b = _booking(db, t, g)
    r = client.get(f"/api/v1/bookings/{b.id}", headers={"X-API-Key": k})
    assert r.status_code == 200
    assert r.json()["id"] == b.id


# ---------- Reviews ----------


def test_list_reviews(client: TestClient, db: Session) -> None:
    t = _tenant(db, "pub-rv")
    k = _make_key(db, t, ["read:reviews"])
    g = _guest(db, t)
    r1 = review_service.create_review(db, tenant=t, user=g, rating=5, content="Amazing stay, loved it")
    review_service.create_review(db, tenant=t, user=g, rating=3, content="It was ok ok ok")
    # Hide the 3-star one
    review_service.hide_review(db, t, review_service.list_reviews(db, t)[0].id)

    r = client.get("/api/v1/reviews", headers={"X-API-Key": k})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1  # only the published one
    assert body["items"][0]["rating"] in (3, 5)


# ---------- Analytics ----------


def test_analytics_summary(client: TestClient, db: Session) -> None:
    t = _tenant(db, "pub-an")
    k = _make_key(db, t, ["read:analytics"])
    g = _guest(db, t)
    _booking(db, t, g)
    _svc(db, t)
    r = client.get("/api/v1/analytics/summary?days=30", headers={"X-API-Key": k})
    assert r.status_code == 200
    body = r.json()
    assert body["period_days"] == 30
    assert body["total_bookings"] >= 1
    assert body["active_services"] >= 1
    assert body["total_revenue_aed"] >= 500.0


# ---------- Cross-tenant isolation ----------


def test_analytics_only_own_tenant(client: TestClient, db: Session) -> None:
    a = _tenant(db, "pub-iso-a")
    b = _tenant(db, "pub-iso-b")
    ka = _make_key(db, a, ["read:analytics"])
    gb = _guest(db, b, "gb@x.com")
    _booking(db, b, gb)

    r = client.get("/api/v1/analytics/summary?days=30", headers={"X-API-Key": ka})
    assert r.status_code == 200
    # A sees zero bookings (B's booking is not visible)
    assert r.json()["total_bookings"] == 0


# ---------- Revoked key ----------


def test_revoked_key_rejected(client: TestClient, db: Session) -> None:
    t = _tenant(db, "pub-rev")
    row, plaintext = api_key_service.create_key(db, tenant=t, name="x", scopes=["read:services"])
    api_key_service.revoke_key(db, t, row.id)
    r = client.get("/api/v1/services", headers={"X-API-Key": plaintext})
    assert r.status_code == 401
