"""Phase 77 Step 4 — Referral API E2E tests (new engine)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User


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


def test_referrals_me_creates_default_code(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h = _register(client, sample_tenant, "rapi1@example.com")
    r = client.get("/referrals/me", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["referral_code"]
    assert d["referred_count"] == 0
    assert d["completed_count"] == 0
    assert d["pending_count"] == 0


def test_apply_own_code_rejected(client: TestClient, sample_tenant: Tenant) -> None:
    h = _register(client, sample_tenant, "rapi2@example.com")
    me = client.get("/referrals/me", headers=h).json()
    r = client.post(
        "/referrals/apply",
        json={"referral_code": me["referral_code"]},
        headers=h,
    )
    assert r.status_code == 400
    assert "yourself" in r.json()["detail"].lower()


def test_apply_unknown_code_rejected(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h = _register(client, sample_tenant, "rapi3@example.com")
    r = client.post(
        "/referrals/apply",
        json={"referral_code": "NOPE123456"},
        headers=h,
    )
    assert r.status_code == 400
    assert "not found" in r.json()["detail"].lower()


def test_apply_success_registers_relationship(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h_a = _register(client, sample_tenant, "rapi_a@example.com")
    code_a = client.get("/referrals/me", headers=h_a).json()["referral_code"]

    h_b = _register(client, sample_tenant, "rapi_b@example.com")
    r = client.post(
        "/referrals/apply",
        json={"referral_code": code_a},
        headers=h_b,
    )
    assert r.status_code == 201, r.text
    rel = r.json()
    assert rel["status"] == "REGISTERED"

    # Referrer sees it as pending
    me_a = client.get("/referrals/me", headers=h_a).json()
    assert me_a["referred_count"] == 1
    assert me_a["completed_count"] == 0
    assert me_a["pending_count"] == 1


def test_apply_twice_is_idempotent(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h_a = _register(client, sample_tenant, "rapi_idem_a@example.com")
    code_a = client.get("/referrals/me", headers=h_a).json()["referral_code"]
    h_b = _register(client, sample_tenant, "rapi_idem_b@example.com")

    r1 = client.post("/referrals/apply", json={"referral_code": code_a}, headers=h_b)
    r2 = client.post("/referrals/apply", json={"referral_code": code_a}, headers=h_b)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


def test_generate_returns_existing_code(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h = _register(client, sample_tenant, "rapi_gen@example.com")
    first = client.get("/referrals/me", headers=h).json()["referral_code"]
    r = client.post("/referrals/generate", json={}, headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["code"] == first


def test_history_requires_participation(
    client: TestClient, sample_tenant: Tenant
) -> None:
    h_a = _register(client, sample_tenant, "rapi_h_a@example.com")
    code_a = client.get("/referrals/me", headers=h_a).json()["referral_code"]
    h_b = _register(client, sample_tenant, "rapi_h_b@example.com")
    rel = client.post(
        "/referrals/apply", json={"referral_code": code_a}, headers=h_b
    ).json()

    h_outsider = _register(client, sample_tenant, "rapi_h_outsider@example.com")
    r = client.get(f"/referrals/history/{rel['id']}", headers=h_outsider)
    assert r.status_code == 403

    r = client.get(f"/referrals/history/{rel['id']}", headers=h_b)
    assert r.status_code == 200
    events = r.json()
    assert len(events) >= 1
    assert events[0]["event_type"] == "REGISTERED"


def test_history_unknown_404(client: TestClient, sample_tenant: Tenant) -> None:
    h = _register(client, sample_tenant, "rapi_h404@example.com")
    r = client.get("/referrals/history/does-not-exist", headers=h)
    assert r.status_code == 404


# ---------- wire into payment: qualification happens via payment flow ----------


def test_payment_triggers_referral_award(
    client: TestClient, sample_tenant: Tenant, db: Session
) -> None:
    """Referrer + referred; referred makes a paid booking; award fires."""
    from app.services import payment_provider

    h_a = _register(client, sample_tenant, "pay_a@example.com")
    h_b = _register(client, sample_tenant, "pay_b@example.com")

    code_a = client.get("/referrals/me", headers=h_a).json()["referral_code"]
    client.post("/referrals/apply", json={"referral_code": code_a}, headers=h_b)

    # Mark referred user as verified (in real flow this would be a
    # phone verification step; Phase 77 does not build that UX yet).
    from app.services import referral_engine
    ref_b = (
        db.query(User).filter(User.email == "pay_b@example.com").one()
    )
    rel = referral_engine.get_relationship_for_referred(db, referred_user_id=ref_b.id)
    referral_engine.mark_verified(db, relationship=rel)

    # Create a qualifying booking for the referred user
    booking = Booking(
        tenant_id=sample_tenant.id,
        user_id=ref_b.id,
        booking_type="hotel",
        service_name="Qualifying Room",
        check_in=date.today() + timedelta(days=1),
        amount=Decimal("500.00"),
        total_amount=Decimal("500.00"),
        currency="AED",
        status="pending",
        payment_status="pending",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    # Create payment intent + mark success (bypasses the HTTP provider)
    from app.models.payment import Payment
    prov = payment_provider.get_payment_provider()
    intent = prov.create_intent(
        amount=Decimal("500.00"), currency="AED", method="card",
        description="test",
    )
    payment = Payment(
        tenant_id=sample_tenant.id,
        user_id=ref_b.id,
        booking_id=booking.id,
        amount=Decimal("500.00"),
        currency="AED",
        provider=prov.name,
        provider_reference=intent.provider_reference,
        status="pending",
        method="card",
        metadata_json={},
    )
    db.add(payment)
    db.commit()

    from app.services import payment_service
    payment_service.mark_success(db, provider_reference=intent.provider_reference)

    # Relationship now REWARDED, wallets credited
    db.refresh(rel)
    assert rel.status == "REWARDED"

    from app.models.reward import Reward
    led = db.query(Reward).filter(Reward.referral_id == rel.id).all()
    assert len(led) == 2
    amounts = sorted(float(r.amount) for r in led)
    assert amounts == [15.0, 20.0]
