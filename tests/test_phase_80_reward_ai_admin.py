"""Phase 80 Step 2 — AI + Analytics + Admin + E2E wiring."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.reward import Reward
from app.models.reward_campaign import RewardCampaign
from app.models.tenant import Tenant
from app.models.user import User
from app.services import reward_ai, reward_analytics, reward_campaign


def _user(db: Session, tenant: Tenant, email: str, code: str) -> User:
    u = User(
        tenant_id=tenant.id, email=email, password_hash="x",
        first_name="A", last_name="B", referral_code=code,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _booking(db: Session, tenant: Tenant, user: User, amount: str = "500.00") -> Booking:
    b = Booking(
        tenant_id=tenant.id, user_id=user.id, booking_type="hotel",
        service_name="T", check_in=date.today() + timedelta(days=1),
        amount=Decimal(amount), total_amount=Decimal(amount), currency="AED",
        status="confirmed", payment_status="paid",
    )
    db.add(b); db.commit(); db.refresh(b)
    return b


def _campaign(db: Session, tenant: Tenant, value: str = "10.00", name: str = "C") -> RewardCampaign:
    c = RewardCampaign(
        tenant_id=tenant.id, name=name, description=name, active=True,
        conditions={}, reward_type="fixed", reward_value=Decimal(value),
        funding_source="CAMPAIGN", economic_cap_pct=Decimal("0.50"),
    )
    db.add(c); db.commit(); db.refresh(c)
    return c


# ---------- AI ----------


def test_ai_returns_no_match_when_no_campaign(
    db: Session, sample_tenant: Tenant
) -> None:
    u = _user(db, sample_tenant, "ai1@example.com", "AI1")
    b = _booking(db, sample_tenant, u)
    rec = reward_ai.recommend_reward(
        db, tenant=sample_tenant, user=u, booking=b, category="HOTEL"
    )
    assert rec.recommended_campaign_id is None
    assert rec.recommended_amount == Decimal("0")


def test_ai_recommends_matching_campaign(
    db: Session, sample_tenant: Tenant
) -> None:
    u = _user(db, sample_tenant, "ai2@example.com", "AI2")
    b = _booking(db, sample_tenant, u)
    c = _campaign(db, sample_tenant, value="15.00")
    rec = reward_ai.recommend_reward(
        db, tenant=sample_tenant, user=u, booking=b, category="HOTEL"
    )
    assert rec.recommended_campaign_id == c.id
    assert rec.recommended_amount == Decimal("15.00")


# ---------- Analytics ----------


def test_analytics_user_metrics_empty(
    db: Session, sample_tenant: Tenant
) -> None:
    m = reward_analytics.user_metrics(db, tenant_id=sample_tenant.id)
    assert m["rewards_earned"] == 0
    assert m["redemption_rate"] == 0.0


def test_analytics_financial_metrics(
    db: Session, sample_tenant: Tenant
) -> None:
    u = _user(db, sample_tenant, "an1@example.com", "AN1")
    _booking(db, sample_tenant, u, amount="1000.00")
    m = reward_analytics.financial_metrics(db, tenant_id=sample_tenant.id)
    assert m["gross_booking_value"] == "1000.00"
    assert m["platform_commission"] == "60.00"


def test_analytics_campaign_metrics(
    db: Session, sample_tenant: Tenant
) -> None:
    _campaign(db, sample_tenant, value="10.00", name="MetricsTest")
    rows = reward_analytics.campaign_metrics(db, tenant_id=sample_tenant.id)
    assert len(rows) >= 1
    assert any(r["name"] == "MetricsTest" for r in rows)


def test_analytics_snapshot(
    db: Session, sample_tenant: Tenant
) -> None:
    snap = reward_analytics.snapshot(db, tenant_id=sample_tenant.id)
    assert "user" in snap
    assert "financial" in snap
    assert "campaigns" in snap


# ---------- E2E: campaign awarded on payment ----------


def test_payment_awards_campaign_bonus(
    db: Session, sample_tenant: Tenant
) -> None:
    """Payment flow: base reward + campaign bonus written to ledger."""
    from app.services import payment_provider, payment_service

    u = _user(db, sample_tenant, "e2e1@example.com", "E2E1")
    _campaign(db, sample_tenant, value="12.00", name="E2E Campaign")

    b = Booking(
        tenant_id=sample_tenant.id, user_id=u.id, booking_type="hotel",
        service_name="E2E Room", check_in=date.today() + timedelta(days=1),
        amount=Decimal("500.00"), total_amount=Decimal("500.00"), currency="AED",
        status="pending", payment_status="pending",
    )
    db.add(b); db.commit(); db.refresh(b)

    from app.models.payment import Payment
    prov = payment_provider.get_payment_provider()
    intent = prov.create_intent(amount=Decimal("500.00"), currency="AED",
                                 method="card", description="test")
    payment = Payment(
        tenant_id=sample_tenant.id, user_id=u.id, booking_id=b.id,
        amount=Decimal("500.00"), currency="AED", provider=prov.name,
        provider_reference=intent.provider_reference, status="pending",
        method="card", metadata_json={},
    )
    db.add(payment); db.commit()

    payment_service.mark_success(db, provider_reference=intent.provider_reference)

    # Ledger must contain a CAMPAIGN_BONUS entry written through the
    # immutable ledger, funded by CAMPAIGN, and capped by the engine.
    led = db.query(Reward).filter(Reward.user_id == u.id).all()
    types = {r.reward_type for r in led}
    assert "CAMPAIGN_BONUS" in types

    bonus = [r for r in led if r.reward_type == "CAMPAIGN_BONUS"][0]
    assert Decimal(str(bonus.amount)) == Decimal("12.00")
    assert bonus.funding_source == "CAMPAIGN"
    assert bonus.campaign_id is not None
