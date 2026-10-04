"""Phase 79 Step 2 — Wallet + Catalog + Ledger API tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.redeem_option import RedeemOption
from app.models.tenant import Tenant
from app.models.user import User
from app.services import reward_engine


def _register(client: TestClient, tenant: Tenant, email: str) -> dict:
    r = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "Pass1234",
            "first_name": "U",
            "last_name": "X",
        },
        headers={"X-Tenant-Slug": tenant.slug},
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    return {
        "X-Tenant-Slug": tenant.slug,
        "Authorization": f"Bearer {token}",
        "X-Email": email,
    }


def _option(db: Session, name: str = "Test Option") -> RedeemOption:
    o = RedeemOption(
        name=name,
        description=name,
        points_cost=500,
        reward_type="credit",
        reward_value=Decimal("25.00"),
        display_order=1,
        platform_cost=Decimal("25.00"),
        funding_source="PLATFORM",
        category=None,
        active=True,
    )
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


def _grant(db: Session, tenant: Tenant, email: str, amount: str) -> None:
    u = db.query(User).filter(User.email == email).one()
    now = datetime.now(timezone.utc)
    reward_engine.create_ledger_entry(
        db,
        tenant=tenant,
        user=u,
        reward_type="PLATFORM_EARN",
        amount=Decimal(amount),
        status="AVAILABLE",
        available_at=now,
        expires_at=now + timedelta(days=60),
    )


# ---------- wallet ----------


def test_wallet_initial_zero(client: TestClient, sample_tenant: Tenant) -> None:
    h = _register(client, sample_tenant, "wal1@example.com")
    r = client.get("/rewards/wallet", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert Decimal(str(d["available_balance"])) == Decimal("0")
    assert d["currency"] == "AED"


def test_wallet_reflects_grant(
    client: TestClient, sample_tenant: Tenant, db: Session
) -> None:
    h = _register(client, sample_tenant, "wal2@example.com")
    _grant(db, sample_tenant, "wal2@example.com", "50.00")

    r = client.get("/rewards/wallet", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert Decimal(str(d["available_balance"])) == Decimal("50.00")


# ---------- catalog ----------


def test_catalog_lists_active(
    client: TestClient, sample_tenant: Tenant, db: Session
) -> None:
    h = _register(client, sample_tenant, "cat1@example.com")
    _option(db, "Phase79 A")
    _option(db, "Phase79 B")

    r = client.get("/rewards/catalog", headers=h)
    assert r.status_code == 200
    names = [o["name"] for o in r.json()]
    assert "Phase79 A" in names
    assert "Phase79 B" in names


def test_catalog_excludes_inactive(
    client: TestClient, sample_tenant: Tenant, db: Session
) -> None:
    h = _register(client, sample_tenant, "cat2@example.com")
    o = _option(db, "Inactive Option")
    o.active = False
    db.commit()

    r = client.get("/rewards/catalog", headers=h)
    assert r.status_code == 200
    names = [x["name"] for x in r.json()]
    assert "Inactive Option" not in names


# ---------- redeem-option ----------


def test_redeem_option_success(
    client: TestClient, sample_tenant: Tenant, db: Session
) -> None:
    h = _register(client, sample_tenant, "rdm1@example.com")
    _grant(db, sample_tenant, "rdm1@example.com", "50.00")
    o = _option(db, "Redeemable")

    r = client.post(
        "/rewards/redeem-option",
        json={"option_id": o.id, "reference_id": "ref-x"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["status"] == "USED"
    assert Decimal(str(d["amount"])) == Decimal("-25.00")


def test_redeem_option_insufficient(
    client: TestClient, sample_tenant: Tenant, db: Session
) -> None:
    h = _register(client, sample_tenant, "rdm2@example.com")
    _grant(db, sample_tenant, "rdm2@example.com", "10.00")
    o = _option(db, "Big")

    r = client.post(
        "/rewards/redeem-option", json={"option_id": o.id}, headers=h
    )
    assert r.status_code == 400
    assert "insufficient" in r.json()["detail"].lower()


def test_redeem_option_unknown(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h = _register(client, sample_tenant, "rdm3@example.com")
    r = client.post(
        "/rewards/redeem-option", json={"option_id": "nope"}, headers=h
    )
    assert r.status_code == 400


# ---------- ledger ----------


def test_ledger_lists_entries(
    client: TestClient, sample_tenant: Tenant, db: Session
) -> None:
    h = _register(client, sample_tenant, "led1@example.com")
    _grant(db, sample_tenant, "led1@example.com", "30.00")
    _grant(db, sample_tenant, "led1@example.com", "20.00")

    r = client.get("/rewards/ledger", headers=h)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 2


# ---------- wallet page ----------


def test_wallet_page_renders_without_user(
    client: TestClient, sample_tenant: Tenant
) -> None:
    """The page always renders, even without a user context."""
    r = client.get("/account/wallet", headers={"X-Tenant-Slug": sample_tenant.slug})
    assert r.status_code == 200
    assert "My Rewards Wallet" in r.text
    assert "Available Balance" in r.text
