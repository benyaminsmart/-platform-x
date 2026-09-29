"""Tests for Business AI API endpoints (Phase 21, Step 3).

Endpoints:
  POST /business/api/ai/chat
  POST /business/api/ai/pricing/analyze
  POST /business/api/ai/pricing/suggest
  POST /business/api/ai/demand/forecast
  POST /business/api/ai/insights

Numbers are deterministic; AI is stubbed globally via conftest.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User


# ---------- Helpers ----------


def _make_business_user(
    db: Session, tenant: Tenant, *, email: str = "owner@biz.test", role: str = "owner"
) -> User:
    u = User(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password("OwnerPass123"),
        first_name="Owner",
        last_name="One",
        business_role=role,
        status="active",
        referral_code=email[:10].upper(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _login(client: TestClient, slug: str, email: str = "owner@biz.test") -> str:
    r = client.post(
        "/business/api/auth/login",
        json={"email": email, "password": "OwnerPass123"},
        headers={"X-Tenant-Slug": slug},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(token: str, slug: str) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Tenant-Slug": slug}


def _svc(db: Session, tenant: Tenant, *, typ: str = "room", name: str = "R", price: float = 500) -> Service:
    s = Service(
        tenant_id=tenant.id,
        type=typ,
        name=name,
        price=Decimal(str(price)),
        currency="AED",
        capacity=2,
        attributes={},
        image_urls=[],
        status="active",
        display_order=0,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _peer(db: Session, slug: str, price: float) -> Tenant:
    t = Tenant(slug=slug, name=slug, tier="starter", status="active", config={})
    db.add(t)
    db.commit()
    db.refresh(t)
    _svc(db, t, typ="room", name=slug, price=price)
    return t


# ---------- Auth guards ----------


@pytest.mark.parametrize(
    "path",
    [
        "/business/api/ai/chat",
        "/business/api/ai/pricing/analyze",
        "/business/api/ai/pricing/suggest",
        "/business/api/ai/demand/forecast",
        "/business/api/ai/insights",
    ],
)
def test_ai_endpoints_require_auth(client: TestClient, sample_tenant: Tenant, path: str) -> None:
    r = client.post(path, json={"message": "hi"}, headers={"X-Tenant-Slug": sample_tenant.slug})
    assert r.status_code == 401


def test_ai_endpoints_regular_user_forbidden(
    client: TestClient, sample_tenant: Tenant, db: Session
) -> None:
    reg = client.post(
        "/auth/register",
        json={
            "email": "guest@x.com",
            "password": "GuestPass123",
            "first_name": "G",
            "last_name": "U",
        },
        headers={"X-Tenant-Slug": sample_tenant.slug},
    )
    token = reg.json()["access_token"]
    r = client.post(
        "/business/api/ai/pricing/analyze",
        json={},
        headers=_h(token, sample_tenant.slug),
    )
    assert r.status_code == 403


# ---------- Chat (grounded) ----------


def test_business_ai_chat_returns_response(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _make_business_user(db, sample_tenant)
    _svc(db, sample_tenant, name="Room A", price=400)
    token = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/ai/chat",
        json={"message": "How is my pricing?"},
        headers=_h(token, sample_tenant.slug),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "content" in body
    assert "provider" in body


# ---------- Pricing analyze ----------


def test_pricing_analyze_empty(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _make_business_user(db, sample_tenant)
    token = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/ai/pricing/analyze",
        json={},
        headers=_h(token, sample_tenant.slug),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "metrics" in body
    assert "advice" in body
    assert body["metrics"]["dominant_type"] is None
    assert body["advice"]


def test_pricing_analyze_with_peers(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _make_business_user(db, sample_tenant)
    _svc(db, sample_tenant, typ="room", name="Mine", price=200)
    _peer(db, "p1", 500)
    _peer(db, "p2", 500)

    token = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/ai/pricing/analyze",
        json={},
        headers=_h(token, sample_tenant.slug),
    )
    assert r.status_code == 200
    m = r.json()["metrics"]
    assert m["dominant_type"] == "room"
    assert m["benchmark"]["cohort_size"] == 2
    assert m["position_by_type"]["room"] == "below_market"


# ---------- Pricing suggest ----------


def test_pricing_suggest_below_market(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _make_business_user(db, sample_tenant)
    _svc(db, sample_tenant, typ="room", name="Mine", price=200)
    _peer(db, "p1", 500)
    _peer(db, "p2", 500)

    token = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/ai/pricing/suggest",
        json={},
        headers=_h(token, sample_tenant.slug),
    )
    assert r.status_code == 200
    sugg = r.json()["metrics"]["suggestions"]
    assert sugg[0]["type"] == "room"
    assert sugg[0]["suggested_change_pct"] > 0


def test_pricing_suggest_no_peers(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _make_business_user(db, sample_tenant)
    _svc(db, sample_tenant, typ="room", name="Mine", price=300)

    token = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/ai/pricing/suggest",
        json={},
        headers=_h(token, sample_tenant.slug),
    )
    assert r.status_code == 200
    sugg = r.json()["metrics"]["suggestions"]
    assert sugg[0]["type"] is None
    assert "not enough peer data" in sugg[0]["note"].lower()


# ---------- Demand forecast ----------


def test_demand_forecast_default_days(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _make_business_user(db, sample_tenant)
    token = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/ai/demand/forecast",
        json={},
        headers=_h(token, sample_tenant.slug),
    )
    assert r.status_code == 200
    assert r.json()["metrics"]["days"] == 30


@pytest.mark.parametrize("days,expected", [(1, 7), (500, 90), (45, 45)])
def test_demand_forecast_days_clamp(
    client: TestClient, sample_tenant: Tenant, db: Session, days: int, expected: int
) -> None:
    _make_business_user(db, sample_tenant)
    token = _login(client, sample_tenant.slug)
    r = client.post(
        f"/business/api/ai/demand/forecast?days={days}",
        json={},
        headers=_h(token, sample_tenant.slug),
    )
    assert r.status_code == 200
    assert r.json()["metrics"]["days"] == expected


# ---------- Market insights ----------


def test_market_insights_empty(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _make_business_user(db, sample_tenant)
    token = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/ai/insights",
        json={},
        headers=_h(token, sample_tenant.slug),
    )
    assert r.status_code == 200
    m = r.json()["metrics"]
    assert m["dominant_type"] is None
    assert m["cohort_size"] == 0


def test_market_insights_with_peers(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    _make_business_user(db, sample_tenant)
    _svc(db, sample_tenant, typ="room", name="Mine", price=300)
    _peer(db, "p1", 500)
    _peer(db, "p2", 500)

    token = _login(client, sample_tenant.slug)
    r = client.post(
        "/business/api/ai/insights",
        json={},
        headers=_h(token, sample_tenant.slug),
    )
    assert r.status_code == 200
    m = r.json()["metrics"]
    assert m["dominant_type"] == "room"
    assert m["cohort_avg_price_aed"] == 500.0
    assert m["your_avg_price_aed"] == 300.0
    assert m["your_position_pct"] == -40.0
    # No peer identity leak
    text = str(r.json())
    assert "p1" not in text
    assert "p2" not in text


# ---------- Cross-tenant isolation ----------


def test_ai_endpoints_cross_tenant_isolation(client: TestClient, sample_tenant: Tenant, db: Session) -> None:
    # Tenant A: owner + a cheap service
    _make_business_user(db, sample_tenant, email="owner@a.test")
    _svc(db, sample_tenant, typ="room", name="A", price=100)

    # Tenant B
    tb = Tenant(slug="other-b", name="Other B", tier="starter", status="active", config={})
    db.add(tb)
    db.commit()
    db.refresh(tb)
    _make_business_user(db, tb, email="owner@b.test")
    _svc(db, tb, typ="room", name="B", price=900)

    token_b = _login(client, tb.slug, "owner@b.test")
    r = client.post(
        "/business/api/ai/pricing/analyze",
        json={},
        headers=_h(token_b, tb.slug),
    )
    assert r.status_code == 200
    m = r.json()["metrics"]
    # B's dominant type avg must reflect only B's services, not A's
    assert m["pricing_by_type"]["room"]["avg"] == 900.0
    assert m["active_services"] == 1
