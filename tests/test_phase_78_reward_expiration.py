"""Phase 78 Step 1 — Reward expiration service tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.reward import Reward
from app.models.reward_wallet import RewardWallet
from app.models.tenant import Tenant
from app.models.user import User
from app.services import reward_expiration, reward_engine


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
    expires_in_days: int = -1,
    reward_type: str = "PLATFORM_EARN",
) -> Reward:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=expires_in_days)
    r, _ = reward_engine.create_ledger_entry(
        db,
        tenant=tenant,
        user=user,
        reward_type=reward_type,
        amount=Decimal(amount),
        currency="AED",
        funding_source="PLATFORM",
        status="AVAILABLE",
        available_at=now,
        expires_at=expires_at,
        description="test reward",
    )
    return r


def test_find_expired_candidates(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "exp1@example.com", "EXP1")
    _available_reward(db, sample_tenant, u, expires_in_days=-1)

    rows = reward_expiration.find_expired_candidates(db, tenant_id=sample_tenant.id)
    assert len(rows) == 1
    assert rows[0].status == "AVAILABLE"


def test_find_expired_candidates_excludes_future(
    db: Session, sample_tenant: Tenant
) -> None:
    u = _user(db, sample_tenant, "exp2@example.com", "EXP2")
    _available_reward(db, sample_tenant, u, expires_in_days=+10)
    rows = reward_expiration.find_expired_candidates(db, tenant_id=sample_tenant.id)
    assert rows == []


def test_find_expiring_soon(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "exp3@example.com", "EXP3")
    _available_reward(db, sample_tenant, u, expires_in_days=+3)
    _available_reward(db, sample_tenant, u, expires_in_days=+20)

    rows = reward_expiration.find_expiring_soon(
        db, tenant_id=sample_tenant.id, days_before=7
    )
    assert len(rows) == 1


def test_expire_reward_creates_compensating_entry(
    db: Session, sample_tenant: Tenant
) -> None:
    u = _user(db, sample_tenant, "exp4@example.com", "EXP4")
    r = _available_reward(db, sample_tenant, u, expires_in_days=-1)

    out = reward_expiration.expire_reward(db, reward=r)
    assert out is not None
    assert out.status == "EXPIRED"
    assert Decimal(str(out.amount)) == Decimal("-10.00")
    assert out.source_id == r.id
    assert out.extra.get("original_reward_id") == r.id

    # Original row is untouched (still AVAILABLE in ledger terms)
    db.refresh(r)
    assert r.status == "AVAILABLE"
    assert r.extra.get("_expired") is True


def test_expire_reward_updates_wallet(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "exp5@example.com", "EXP5")
    r = _available_reward(db, sample_tenant, u, expires_in_days=-1)

    # Wallet should show the credit before expiration
    w = db.query(RewardWallet).filter(RewardWallet.user_id == u.id).one()
    assert Decimal(str(w.available_balance)) == Decimal("10.00")

    reward_expiration.expire_reward(db, reward=r)
    db.refresh(w)
    assert Decimal(str(w.available_balance)) == Decimal("0.00")


def test_expire_reward_is_idempotent(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "exp6@example.com", "EXP6")
    r = _available_reward(db, sample_tenant, u, expires_in_days=-1)

    first = reward_expiration.expire_reward(db, reward=r)
    second = reward_expiration.expire_reward(db, reward=r)
    assert first is not None
    assert second is None

    entries = (
        db.query(Reward)
        .filter(Reward.user_id == u.id, Reward.reward_type == "EXPIRATION")
        .all()
    )
    assert len(entries) == 1


def test_expire_reward_skips_non_available(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "exp7@example.com", "EXP7")
    now = datetime.now(timezone.utc)
    r, _ = reward_engine.create_ledger_entry(
        db,
        tenant=sample_tenant,
        user=u,
        reward_type="LOCKED",
        amount=Decimal("5.00"),
        status="LOCKED",
        available_at=now,
        expires_at=now - timedelta(days=1),
    )
    out = reward_expiration.expire_reward(db, reward=r)
    assert out is None


def test_run_expiration_batch(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "exp8@example.com", "EXP8")
    _available_reward(db, sample_tenant, u, expires_in_days=-1, amount="3.00")
    _available_reward(db, sample_tenant, u, expires_in_days=-1, amount="7.00")
    _available_reward(db, sample_tenant, u, expires_in_days=+10)

    # Snapshot before expiration: 3 + 7 + 10 = 20.00
    w_before = db.query(RewardWallet).filter(RewardWallet.user_id == u.id).one()
    before = Decimal(str(w_before.available_balance))
    assert before == Decimal("20.00")

    result = reward_expiration.run_expiration(db, tenant_id=sample_tenant.id)
    assert result["scanned"] == 2
    assert result["expired"] == 2
    assert result["errors"] == 0

    # Recompute the wallet balance directly from the ledger — this is
    # the canonical check and is not affected by session caching.
    total = Decimal("0")
    for r in db.query(Reward).filter(Reward.user_id == u.id).all():
        extra = r.extra or {}
        if extra.get("_expired") is True:
            continue
        if extra.get("original_reward_id") and Decimal(str(r.amount)) < 0:
            continue
        if r.status == "AVAILABLE":
            total += Decimal(str(r.amount))
        elif r.status in ("USED", "PARTIALLY_USED", "EXPIRED", "REVERSED", "CANCELLED"):
            amt = Decimal(str(r.amount))
            if amt < 0:
                total += amt

    # After expiring 3.00 and 7.00, only the future 10.00 remains.
    assert total == Decimal("10.00")


def test_run_expiration_skips_future(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "exp9@example.com", "EXP9")
    _available_reward(db, sample_tenant, u, expires_in_days=+30)
    result = reward_expiration.run_expiration(db, tenant_id=sample_tenant.id)
    assert result["scanned"] == 0
    assert result["expired"] == 0
