"""Phase 80 Step 1 — Campaign engine + economics tests."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.reward_campaign import RewardCampaign, RewardCampaignUse
from app.models.tenant import Tenant
from app.models.user import User
from app.services import reward_campaign, reward_economics


def _user(db: Session, tenant: Tenant, email: str, code: str) -> User:
    u = User(
        tenant_id=tenant.id,
        email=email,
        password_hash="x",
        first_name="A",
        last_name="B",
        referral_code=code,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _booking(
    db: Session,
    tenant: Tenant,
    user: User,
    *,
    amount: str = "500.00",
    payment_status: str = "paid",
) -> Booking:
    b = Booking(
        tenant_id=tenant.id,
        user_id=user.id,
        booking_type="hotel",
        service_name="Test",
        check_in=date.today() + timedelta(days=1),
        amount=Decimal(amount),
        total_amount=Decimal(amount),
        currency="AED",
        status="confirmed",
        payment_status=payment_status,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def _campaign(
    db: Session,
    tenant: Tenant,
    *,
    name: str = "Test",
    reward_type: str = "fixed",
    value: str = "10.00",
    conditions: dict | None = None,
    budget_total: str | None = None,
    usage_limit: int | None = None,
    user_limit: int | None = None,
    economic_cap_pct: str = "0.50",
) -> RewardCampaign:
    c = RewardCampaign(
        tenant_id=tenant.id,
        name=name,
        description=name,
        active=True,
        conditions=conditions or {},
        reward_type=reward_type,
        reward_value=Decimal(value),
        funding_source="CAMPAIGN",
        budget_total=Decimal(budget_total) if budget_total else None,
        usage_limit=usage_limit,
        user_limit=user_limit,
        economic_cap_pct=Decimal(economic_cap_pct),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ---------- find ----------


def test_find_fixed_campaign(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "c1@example.com", "C1")
    b = _booking(db, sample_tenant, u)
    _campaign(db, sample_tenant, name="Fixed10", value="10.00")

    m = reward_campaign.find_best_campaign(
        db, tenant=sample_tenant, user=u, booking=b, category="HOTEL"
    )
    assert m is not None
    assert m.amount == Decimal("10.00")


def test_category_condition_blocks(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "c2@example.com", "C2")
    b = _booking(db, sample_tenant, u)
    _campaign(db, sample_tenant, name="Only DINING",
              conditions={"category": "DINING"}, value="10.00")

    m = reward_campaign.find_best_campaign(
        db, tenant=sample_tenant, user=u, booking=b, category="HOTEL"
    )
    assert m is None


def test_category_condition_matches(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "c3@example.com", "C3")
    b = _booking(db, sample_tenant, u)
    _campaign(db, sample_tenant, name="Only HOTEL",
              conditions={"category": "HOTEL"}, value="10.00")

    m = reward_campaign.find_best_campaign(
        db, tenant=sample_tenant, user=u, booking=b, category="HOTEL"
    )
    assert m is not None


def test_min_transaction_blocks(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "c4@example.com", "C4")
    b = _booking(db, sample_tenant, u, amount="100.00")
    _campaign(db, sample_tenant, name="Min500",
              conditions={"min_transaction": 500}, value="10.00")

    m = reward_campaign.find_best_campaign(
        db, tenant=sample_tenant, user=u, booking=b, category="HOTEL"
    )
    assert m is None


def test_first_booking_condition(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "c5@example.com", "C5")
    # Old paid booking exists
    _booking(db, sample_tenant, u, amount="100.00")
    b2 = _booking(db, sample_tenant, u, amount="500.00")
    _campaign(db, sample_tenant, name="FirstOnly",
              conditions={"first_booking": True}, value="10.00")

    m = reward_campaign.find_best_campaign(
        db, tenant=sample_tenant, user=u, booking=b2, category="HOTEL"
    )
    assert m is None


def test_economic_cap_limits_amount(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "c6@example.com", "C6")
    # 100 AED booking → 6 AED commission → 50% cap = 3 AED
    b = _booking(db, sample_tenant, u, amount="100.00")
    _campaign(db, sample_tenant, name="Huge", value="1000.00",
              economic_cap_pct="0.50")

    m = reward_campaign.find_best_campaign(
        db, tenant=sample_tenant, user=u, booking=b, category="HOTEL"
    )
    assert m is not None
    assert m.amount == Decimal("3.00")
    assert m.capped_by_economic is True


def test_budget_total_caps_amount(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "c7@example.com", "C7")
    b = _booking(db, sample_tenant, u, amount="500.00")
    c = _campaign(db, sample_tenant, name="Budget", value="50.00",
                  budget_total="20.00")
    c.budget_used = Decimal("5.00")
    db.commit()

    m = reward_campaign.find_best_campaign(
        db, tenant=sample_tenant, user=u, booking=b, category="HOTEL"
    )
    assert m is not None
    # remaining = 15, requested 50, economic cap = 500*0.06*0.5 = 15 → min(15,15) = 15
    assert m.amount == Decimal("15.00")


def test_usage_limit_blocks(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "c8@example.com", "C8")
    b = _booking(db, sample_tenant, u, amount="500.00")
    c = _campaign(db, sample_tenant, name="Limited", value="10.00", usage_limit=1)
    c.usage_count = 1
    db.commit()

    m = reward_campaign.find_best_campaign(
        db, tenant=sample_tenant, user=u, booking=b, category="HOTEL"
    )
    assert m is None


def test_record_campaign_use_updates_counters(
    db: Session, sample_tenant: Tenant
) -> None:
    u = _user(db, sample_tenant, "c9@example.com", "C9")
    b = _booking(db, sample_tenant, u, amount="500.00")
    c = _campaign(db, sample_tenant, name="Usage", value="10.00", budget_total="100.00")

    use = reward_campaign.record_campaign_use(
        db, tenant=sample_tenant, user=u, campaign=c,
        booking=b, amount=Decimal("10.00"), ledger_reward_id="l-1",
    )
    assert use.id
    db.refresh(c)
    assert c.usage_count == 1
    assert Decimal(str(c.budget_used)) == Decimal("10.00")


# ---------- economics ----------


def test_economics_snapshot_empty(db: Session, sample_tenant: Tenant) -> None:
    snap = reward_economics.snapshot(db, tenant_id=sample_tenant.id)
    assert snap["gross_booking_value"] == "0.00"
    assert snap["platform_commission"] == "0.00"
    assert snap["net_platform_value"] == "0.00"


def test_economics_snapshot_with_bookings(
    db: Session, sample_tenant: Tenant
) -> None:
    u = _user(db, sample_tenant, "e1@example.com", "E1")
    _booking(db, sample_tenant, u, amount="1000.00")

    snap = reward_economics.snapshot(db, tenant_id=sample_tenant.id)
    assert snap["gross_booking_value"] == "1000.00"
    assert snap["platform_commission"] == "60.00"
    assert snap["booking_count"] == 1


def test_economics_cost_ratio(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "e2@example.com", "E2")
    _booking(db, sample_tenant, u, amount="1000.00")
    ratio = reward_economics.reward_cost_ratio(db, tenant_id=sample_tenant.id)
    assert ratio == 0.0  # no rewards yet
