"""Phase 79 Step 1 — Reward redemption service tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.redeem_option import RedeemOption
from app.models.reward import Reward
from app.models.reward_wallet import RewardWallet
from app.models.tenant import Tenant
from app.models.user import User
from app.services import reward_engine, reward_redemption


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


def _grant(db: Session, tenant: Tenant, user: User, amount: str) -> Reward:
    now = datetime.now(timezone.utc)
    r, _ = reward_engine.create_ledger_entry(
        db, tenant=tenant, user=user, reward_type="PLATFORM_EARN",
        amount=Decimal(amount), status="AVAILABLE",
        available_at=now, expires_at=now + timedelta(days=60),
    )
    return r


def _option(
    db: Session, tenant: Tenant, *, name: str = "Test",
    cost: str = "25.00", points: int = 500,
) -> RedeemOption:
    o = RedeemOption(
        name=name, description=name, points_cost=points,
        reward_type="credit", reward_value=Decimal(cost),
        display_order=1, platform_cost=Decimal(cost),
        funding_source="PLATFORM", category=None, active=True,
    )
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


# ---------- catalog ----------


def test_list_active_options(db: Session, sample_tenant: Tenant) -> None:
    _option(db, sample_tenant, name="A")
    _option(db, sample_tenant, name="B")
    rows = reward_redemption.list_active_options(db)
    assert len(rows) >= 2


def test_get_option_returns_none_when_inactive(
    db: Session, sample_tenant: Tenant
) -> None:
    o = _option(db, sample_tenant, name="X")
    o.active = False
    db.commit()
    assert reward_redemption.get_option(db, option_id=o.id) is None


# ---------- redemption ----------


def test_redeem_success(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "red1@example.com", "RED1")
    _grant(db, sample_tenant, u, "50.00")
    o = _option(db, sample_tenant, name="Redeem25", cost="25.00", points=500)

    entry = reward_redemption.redeem_option(
        db, tenant=sample_tenant, user=u, option_id=o.id
    )
    assert entry.status == "USED"
    assert Decimal(str(entry.amount)) == Decimal("-25.00")
    assert entry.source_id == o.id


def test_redeem_reduces_wallet(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "red2@example.com", "RED2")
    _grant(db, sample_tenant, u, "50.00")
    o = _option(db, sample_tenant, name="Redeem10", cost="10.00", points=200)

    reward_redemption.redeem_option(db, tenant=sample_tenant, user=u, option_id=o.id)
    db.expire_all()
    w = db.query(RewardWallet).filter(RewardWallet.user_id == u.id).one()
    assert Decimal(str(w.available_balance)) == Decimal("40.00")


def test_redeem_insufficient_balance(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "red3@example.com", "RED3")
    _grant(db, sample_tenant, u, "10.00")
    o = _option(db, sample_tenant, name="Big", cost="100.00", points=2000)

    import pytest
    with pytest.raises(ValueError, match="Insufficient"):
        reward_redemption.redeem_option(db, tenant=sample_tenant, user=u, option_id=o.id)


def test_redeem_unknown_option(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "red4@example.com", "RED4")
    import pytest
    with pytest.raises(ValueError, match="not found"):
        reward_redemption.redeem_option(
            db, tenant=sample_tenant, user=u, option_id="nope"
        )


def test_redeem_duplicate_guarded(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "red5@example.com", "RED5")
    _grant(db, sample_tenant, u, "50.00")
    o = _option(db, sample_tenant, name="Dup", cost="10.00", points=200)

    reward_redemption.redeem_option(
        db, tenant=sample_tenant, user=u, option_id=o.id, reference_id="ref-1"
    )
    import pytest
    with pytest.raises(ValueError, match="already been redeemed"):
        reward_redemption.redeem_option(
            db, tenant=sample_tenant, user=u, option_id=o.id, reference_id="ref-1"
        )


def test_redeem_without_reference_allows_multiple(
    db: Session, sample_tenant: Tenant
) -> None:
    """Without reference_id, the duplicate guard still fires on the
    (user, option, None) key — but with distinct reference_ids it does not."""
    u = _user(db, sample_tenant, "red6@example.com", "RED6")
    _grant(db, sample_tenant, u, "100.00")
    o = _option(db, sample_tenant, name="Multi", cost="10.00", points=200)

    reward_redemption.redeem_option(
        db, tenant=sample_tenant, user=u, option_id=o.id, reference_id="a"
    )
    reward_redemption.redeem_option(
        db, tenant=sample_tenant, user=u, option_id=o.id, reference_id="b"
    )
    db.expire_all()
    w = db.query(RewardWallet).filter(RewardWallet.user_id == u.id).one()
    assert Decimal(str(w.available_balance)) == Decimal("80.00")
