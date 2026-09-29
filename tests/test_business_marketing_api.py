"""Tests for Business Marketing API (Phase 25, Step 4)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User


# ---------- Helpers ----------


def _tenant(db: Session, slug: str = "mkt-api") -> Tenant:
    t = Tenant(slug=slug, name="Mkt API Biz", tier="starter", status="active",
               config={"type": "hotel", "location": "Dubai, UAE", "rating": 4.7, "reviews_count": 300})
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _biz_user(db: Session, tenant: Tenant, *, email: str = "owner@biz.test", role: str = "owner") -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("OwnerPass123"),
        first_name="O", last_name="X",
        business_role=role, status="active",
        referral_code=email[:10].upper(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _customer(db: Session, tenant: Tenant, email: str, *, days_ago: int = 5, tier: str = "welcome") -> User:
    u = User(
        tenant_id=tenant.id, email=email,
        password_hash=hash_password("CustPass123"),
        first_name="C", last_name="X",
        tier=tier, status="active",
        referral_code=email[:10].upper(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    ci = date.today() - timedelta(days=days_ago)
    b = Booking(
        tenant_id=tenant.id, user_id=u.id, booking_type="room",
        service_name="R", check_in=ci, check_out=ci + timedelta(days=1),
        guests=1, amount=Decimal("500"), discount=Decimal("0"),
        total_amount=Decimal("500"), currency="AED",
        status="confirmed", payment_status="paid",
    )
    db.add(b)
    db.commit()
    return u


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


# ---------- Config ----------


def test_config_endpoint(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.get("/business/api/marketing/config", headers=_h(tok, t.slug))
    assert r.status_code == 200
    body = r.json()
    # By default in tests EMAIL_ENABLED is off
    assert body["email_enabled"] is False


# ---------- Segments ----------


def test_segments_summary(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    _customer(db, t, "a@x.com", days_ago=5)
    _customer(db, t, "b@x.com", days_ago=200)

    tok = _login(client, t.slug)
    r = client.get("/business/api/marketing/segments", headers=_h(tok, t.slug))
    assert r.status_code == 200
    body = r.json()
    segs = {s["name"]: s for s in body["segments"]}
    assert segs["all"]["count"] == 2
    assert segs["inactive_90d"]["count"] == 1
    assert body["totals"]["customers"] == 2


def test_segment_users_owner(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    _customer(db, t, "a@x.com", days_ago=5)

    tok = _login(client, t.slug)
    r = client.get("/business/api/marketing/segments/all", headers=_h(tok, t.slug))
    assert r.status_code == 200
    body = r.json()
    assert body["segment"] == "all"
    assert "a@x.com" in body["emails"]


def test_segment_users_staff_forbidden(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t, email="staff@biz.test", role="staff")
    tok = _login(client, t.slug, "staff@biz.test")
    r = client.get("/business/api/marketing/segments/all", headers=_h(tok, t.slug))
    assert r.status_code == 403


def test_segment_users_invalid_segment(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.get("/business/api/marketing/segments/bogus", headers=_h(tok, t.slug))
    assert r.status_code == 400


def test_segments_requires_auth(client: TestClient, sample_tenant: Tenant) -> None:
    r = client.get(
        "/business/api/marketing/segments",
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    assert r.status_code == 401


# ---------- Campaigns ----------


def test_campaigns_suggest(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    _customer(db, t, "a@x.com", days_ago=5)

    tok = _login(client, t.slug)
    r = client.post(
        "/business/api/marketing/campaigns/suggest",
        json={"language": "en"},
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 200
    body = r.json()
    assert 3 <= len(body["campaigns"]) <= 5
    assert body["provider"] in ("ai", "fallback")


def test_campaigns_suggest_invalid_language(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.post(
        "/business/api/marketing/campaigns/suggest",
        json={"language": "fr"},
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 422


def test_campaigns_generate(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    _customer(db, t, "a@x.com", days_ago=5)

    tok = _login(client, t.slug)
    r = client.post(
        "/business/api/marketing/campaigns/generate",
        json={"segment": "past_bookers", "goal": "boost weekend bookings", "language": "en"},
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["campaign"]["target_segment"] == "past_bookers"


def test_campaigns_generate_invalid_segment(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.post(
        "/business/api/marketing/campaigns/generate",
        json={"segment": "bogus", "goal": "valid goal text", "language": "en"},
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 400


# ---------- Discounts ----------


def test_discounts_suggest(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    _customer(db, t, "a@x.com", days_ago=200)

    tok = _login(client, t.slug)
    r = client.post(
        "/business/api/marketing/discounts/suggest",
        json={"language": "en"},
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 200
    body = r.json()
    segs = {s["segment"] for s in body["suggestions"]}
    assert "inactive_90d" in segs


def test_discounts_suggest_invalid_segment_filter(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.post(
        "/business/api/marketing/discounts/suggest",
        json={"language": "en", "segments": ["bogus"]},
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 400


# ---------- Send (dry-run) ----------


def test_send_campaign_dry_run(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    _customer(db, t, "a@x.com", days_ago=5)
    _customer(db, t, "b@x.com", days_ago=5)

    tok = _login(client, t.slug)
    r = client.post(
        "/business/api/marketing/campaigns/send",
        json={"segment": "past_bookers", "subject": "Hi", "body": "Test body", "language": "en"},
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["email_enabled"] is False
    assert body["dry_run"] is True
    assert body["attempted"] == 2
    assert body["sent"] == 0
    assert body["note"]


def test_send_staff_forbidden(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t, email="staff@biz.test", role="staff")
    tok = _login(client, t.slug, "staff@biz.test")
    r = client.post(
        "/business/api/marketing/campaigns/send",
        json={"segment": "all", "subject": "X", "body": "Y", "language": "en"},
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 403


def test_send_invalid_segment(client: TestClient, db: Session) -> None:
    t = _tenant(db)
    _biz_user(db, t)
    tok = _login(client, t.slug)
    r = client.post(
        "/business/api/marketing/campaigns/send",
        json={"segment": "bogus", "subject": "X", "body": "Y", "language": "en"},
        headers=_h(tok, t.slug),
    )
    assert r.status_code == 400


# ---------- Cross-tenant isolation ----------


def test_cross_tenant_isolation(client: TestClient, db: Session) -> None:
    a = _tenant(db, "mkt-a")
    b = _tenant(db, "mkt-b")
    _biz_user(db, a, email="owner@a.test")
    _customer(db, b, "b@x.com", days_ago=5)

    tok_a = _login(client, a.slug, "owner@a.test")
    r = client.get("/business/api/marketing/segments", headers=_h(tok_a, a.slug))
    assert r.status_code == 200
    assert r.json()["totals"]["customers"] == 0  # A sees no one from B
