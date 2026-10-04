"""Phase 78 Step 2 — Reward reversal + notifications tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.reward import Reward
from app.models.reward_wallet import RewardWallet
from app.models.tenant import Tenant
from app.models.user import User
from app.services import reward_engine, reward_expiration, reward_notifications, reward_reversal


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


def _available_reward(
    db: Session,
    tenant: Tenant,
    user: User,
    *,
    amount: str = "10.00",
    expires_in_days: int = 30,
    transaction_id: str | None = None,
) -> Reward:
    now = datetime.now(timezone.utc)
    r, _ = reward_engine.create_ledger_entry(
        db,
        tenant=tenant,
        user=user,
        reward_type="PLATFORM_EARN",
        amount=Decimal(amount),
        currency="AED",
        funding_source="PLATFORM",
        status="AVAILABLE",
        available_at=now,
        expires_at=now + timedelta(days=expires_in_days),
        transaction_id=transaction_id,
        description="test reward",
    )
    return r


# ---------- reversal ----------


def test_reverse_available_reward(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "rev1@example.com", "REV1")
    r = _available_reward(db, sample_tenant, u, amount="10.00")

    out = reward_reversal.reverse_reward(db, reward=r, reason="test")
    assert out is not None
    assert out.status == "REVERSED"
    assert Decimal(str(out.amount)) == Decimal("-10.00")
    assert out.source_id == r.id

    db.refresh(r)
    assert r.extra.get("_reversed") is True


def test_reverse_updates_wallet(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "rev2@example.com", "REV2")
    r = _available_reward(db, sample_tenant, u, amount="10.00")

    w = db.query(RewardWallet).filter(RewardWallet.user_id == u.id).one()
    assert Decimal(str(w.available_balance)) == Decimal("10.00")

    reward_reversal.reverse_reward(db, reward=r, reason="test")
    db.expire_all()
    w = db.query(RewardWallet).filter(RewardWallet.user_id == u.id).one()
    assert Decimal(str(w.available_balance)) == Decimal("0.00")


def test_reverse_idempotent(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "rev3@example.com", "REV3")
    r = _available_reward(db, sample_tenant, u, amount="5.00")

    first = reward_reversal.reverse_reward(db, reward=r, reason="test")
    second = reward_reversal.reverse_reward(db, reward=r, reason="test")
    assert first is not None
    assert second is None

    entries = (
        db.query(Reward)
        .filter(Reward.user_id == u.id, Reward.reward_type == "REVERSAL")
        .all()
    )
    assert len(entries) == 1


def test_reverse_pending_reward_voids(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "rev4@example.com", "REV4")
    now = datetime.now(timezone.utc)
    r, _ = reward_engine.create_ledger_entry(
        db,
        tenant=sample_tenant,
        user=u,
        reward_type="PENDING_EARN",
        amount=Decimal("5.00"),
        status="PENDING",
        available_at=now,
        expires_at=now + timedelta(days=30),
    )
    out = reward_reversal.reverse_reward(db, reward=r, reason="cancellation")
    assert out is not None
    assert out.status == "CANCELLED"
    assert out.extra.get("voided") is True


def test_reverse_for_booking(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "rev5@example.com", "REV5")
    booking_id = "booking-abc"
    # Two distinct reward types on the same booking (idempotency key is
    # (user_id, transaction_id, reward_type), so a duplicate type would
    # be deduplicated by design).
    now = datetime.now(timezone.utc)
    reward_engine.create_ledger_entry(
        db, tenant=sample_tenant, user=u, reward_type="PLATFORM_EARN",
        amount=Decimal("10.00"), status="AVAILABLE",
        available_at=now, expires_at=now + timedelta(days=30),
        transaction_id=booking_id,
    )
    reward_engine.create_ledger_entry(
        db, tenant=sample_tenant, user=u, reward_type="REFERRAL_BONUS",
        amount=Decimal("5.00"), status="AVAILABLE",
        available_at=now, expires_at=now + timedelta(days=30),
        transaction_id=booking_id, funding_source="REFERRAL",
    )
    _available_reward(db, sample_tenant, u, amount="7.00")  # unrelated

    result = reward_reversal.reverse_rewards_for_booking(
        db, booking_id=booking_id, reason="cancellation"
    )
    assert result["scanned"] == 2
    assert result["reversed"] == 2
    assert result["errors"] == 0

    # Wallet: 10+5+7 - 10 - 5 = 7
    db.expire_all()
    w = db.query(RewardWallet).filter(RewardWallet.user_id == u.id).one()
    assert Decimal(str(w.available_balance)) == Decimal("7.00")


def test_reverse_referral_rewards(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "rev6@example.com", "REV6")
    now = datetime.now(timezone.utc)
    rel_id = "referral-xyz"
    reward_engine.create_ledger_entry(
        db,
        tenant=sample_tenant,
        user=u,
        reward_type="REFERRAL_BONUS",
        amount=Decimal("20.00"),
        funding_source="REFERRAL",
        status="AVAILABLE",
        available_at=now,
        expires_at=now + timedelta(days=60),
        referral_id=rel_id,
    )
    result = reward_reversal.reverse_referral_rewards(db, referral_id=rel_id)
    assert result["reversed"] == 1


# ---------- notifications ----------


def test_notify_expiring_soon(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "not1@example.com", "NOT1")
    _available_reward(db, sample_tenant, u, expires_in_days=3, amount="10.00")

    out = reward_notifications.notify_expiring_soon(db, tenant_id=sample_tenant.id)
    assert out["sent"] >= 1

    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == u.id)
        .all()
    )
    assert len(notifs) >= 1


def test_notify_expiring_soon_idempotent(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "not2@example.com", "NOT2")
    _available_reward(db, sample_tenant, u, expires_in_days=3, amount="10.00")

    first = reward_notifications.notify_expiring_soon(db, tenant_id=sample_tenant.id)
    second = reward_notifications.notify_expiring_soon(db, tenant_id=sample_tenant.id)
    assert first["sent"] >= 1
    assert second["sent"] == 0
    assert second["skipped"] >= 1


def test_notify_expired_after_expiration(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "not3@example.com", "NOT3")
    r = _available_reward(db, sample_tenant, u, expires_in_days=-1, amount="10.00")

    reward_expiration.expire_reward(db, reward=r)
    db.expire_all()
    out = reward_notifications.notify_expired(db, tenant_id=sample_tenant.id)
    assert out["sent"] >= 1
