"""Phase 77 Step 2 — Referral lifecycle service tests.

Covers:
- generate_code (idempotent default)
- apply_code (self-referral rejection, unknown code, duplicate)
- mark_verified (idempotent)
- evaluate_qualification + mark_qualified (min amount, paid/confirmed)
- award_referral (ledger writes, idempotent, amounts match plan §10)
- list_my_referrals + count_by_status
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core import rewards_config
from app.models.booking import Booking
from app.models.referral_code import ReferralCode
from app.models.referral_event import ReferralEvent
from app.models.referral_relationship import ReferralRelationship
from app.models.referral_reward import ReferralReward
from app.models.reward import Reward
from app.models.reward_wallet import RewardWallet
from app.models.tenant import Tenant
from app.models.user import User
from app.services import referral_engine


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
    amount: str = "400.00",
    payment_status: str = "paid",
    status: str = "confirmed",
) -> Booking:
    b = Booking(
        tenant_id=tenant.id,
        user_id=user.id,
        booking_type="hotel",
        service_name="Test Room",
        check_in=date.today() + timedelta(days=1),
        amount=Decimal(amount),
        total_amount=Decimal(amount),
        currency="AED",
        status=status,
        payment_status=payment_status,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


# ---------- generate_code ----------


def test_generate_code_creates_default(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "g1@example.com", "OLD_G1")
    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=u)
    assert rc.id
    assert rc.code
    assert rc.is_default is True
    assert rc.is_active is True
    assert rc.user_id == u.id


def test_generate_code_is_idempotent(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "g2@example.com", "OLD_G2")
    rc1 = referral_engine.generate_code(db, tenant=sample_tenant, user=u)
    rc2 = referral_engine.generate_code(db, tenant=sample_tenant, user=u)
    assert rc1.id == rc2.id


# ---------- apply_code ----------


def test_apply_code_creates_relationship(db: Session, sample_tenant: Tenant) -> None:
    referrer = _user(db, sample_tenant, "a1@example.com", "REF_A1")
    referred = _user(db, sample_tenant, "a2@example.com", "REF_A2")
    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=referrer)

    rel = referral_engine.apply_code(
        db, tenant=sample_tenant, current_user=referred, code=rc.code
    )
    assert rel.status == "REGISTERED"
    assert rel.referrer_user_id == referrer.id
    assert rel.referred_user_id == referred.id


def test_apply_code_self_referral_rejected(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "s1@example.com", "REF_S1")
    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=u)
    with pytest.raises(ValueError, match="refer yourself"):
        referral_engine.apply_code(db, tenant=sample_tenant, current_user=u, code=rc.code)


def test_apply_code_unknown_rejected(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "u1@example.com", "REF_U1")
    with pytest.raises(ValueError, match="not found"):
        referral_engine.apply_code(db, tenant=sample_tenant, current_user=u, code="NOPE123")


def test_apply_code_twice_is_idempotent(db: Session, sample_tenant: Tenant) -> None:
    referrer = _user(db, sample_tenant, "d1@example.com", "REF_D1")
    referred = _user(db, sample_tenant, "d2@example.com", "REF_D2")
    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=referrer)

    r1 = referral_engine.apply_code(db, tenant=sample_tenant, current_user=referred, code=rc.code)
    r2 = referral_engine.apply_code(db, tenant=sample_tenant, current_user=referred, code=rc.code)
    assert r1.id == r2.id


# ---------- verify ----------


def test_mark_verified(db: Session, sample_tenant: Tenant) -> None:
    referrer = _user(db, sample_tenant, "v1@example.com", "REF_V1")
    referred = _user(db, sample_tenant, "v2@example.com", "REF_V2")
    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=referrer)
    rel = referral_engine.apply_code(db, tenant=sample_tenant, current_user=referred, code=rc.code)

    rel2 = referral_engine.mark_verified(db, relationship=rel)
    assert rel2.status == "VERIFIED"
    assert rel2.verified_at is not None


def test_mark_verified_idempotent(db: Session, sample_tenant: Tenant) -> None:
    referrer = _user(db, sample_tenant, "v3@example.com", "REF_V3")
    referred = _user(db, sample_tenant, "v4@example.com", "REF_V4")
    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=referrer)
    rel = referral_engine.apply_code(db, tenant=sample_tenant, current_user=referred, code=rc.code)

    referral_engine.mark_verified(db, relationship=rel)
    rel2 = referral_engine.mark_verified(db, relationship=rel)
    assert rel2.status == "VERIFIED"


# ---------- qualification ----------


def test_qualification_below_minimum(db: Session, sample_tenant: Tenant) -> None:
    referrer = _user(db, sample_tenant, "q1@example.com", "REF_Q1")
    referred = _user(db, sample_tenant, "q2@example.com", "REF_Q2")
    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=referrer)
    rel = referral_engine.apply_code(db, tenant=sample_tenant, current_user=referred, code=rc.code)
    referral_engine.mark_verified(db, relationship=rel)

    b = _booking(db, sample_tenant, referred, amount="100.00")
    ok, reason = referral_engine.evaluate_qualification(db, relationship=rel, booking=b)
    assert ok is False
    assert reason == "below_minimum"


def test_qualification_not_paid(db: Session, sample_tenant: Tenant) -> None:
    referrer = _user(db, sample_tenant, "q3@example.com", "REF_Q3")
    referred = _user(db, sample_tenant, "q4@example.com", "REF_Q4")
    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=referrer)
    rel = referral_engine.apply_code(db, tenant=sample_tenant, current_user=referred, code=rc.code)
    referral_engine.mark_verified(db, relationship=rel)

    b = _booking(db, sample_tenant, referred, amount="500.00", payment_status="pending")
    ok, reason = referral_engine.evaluate_qualification(db, relationship=rel, booking=b)
    assert ok is False
    assert reason == "not_paid"


def test_qualification_ok(db: Session, sample_tenant: Tenant) -> None:
    referrer = _user(db, sample_tenant, "q5@example.com", "REF_Q5")
    referred = _user(db, sample_tenant, "q6@example.com", "REF_Q6")
    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=referrer)
    rel = referral_engine.apply_code(db, tenant=sample_tenant, current_user=referred, code=rc.code)
    referral_engine.mark_verified(db, relationship=rel)

    b = _booking(db, sample_tenant, referred, amount="400.00")
    ok, reason = referral_engine.evaluate_qualification(db, relationship=rel, booking=b)
    assert ok is True
    assert reason == "ok"

    rel2 = referral_engine.mark_qualified(db, relationship=rel, booking=b)
    assert rel2.status == "QUALIFIED"
    assert rel2.qualifying_booking_id == b.id


# ---------- award ----------


def test_award_referral_writes_ledger(db: Session, sample_tenant: Tenant) -> None:
    referrer = _user(db, sample_tenant, "w1@example.com", "REF_W1")
    referred = _user(db, sample_tenant, "w2@example.com", "REF_W2")
    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=referrer)
    rel = referral_engine.apply_code(db, tenant=sample_tenant, current_user=referred, code=rc.code)
    referral_engine.mark_verified(db, relationship=rel)
    b = _booking(db, sample_tenant, referred, amount="400.00")
    referral_engine.mark_qualified(db, relationship=rel, booking=b)

    result = referral_engine.award_referral(db, relationship=rel)
    assert result is not None
    rw_ref, rw_refd = result
    assert rw_ref.side == "REFERRER"
    assert rw_refd.side == "REFERRED"
    assert rw_ref.amount == Decimal(str(rewards_config.REFERRAL_REFERRER_CREDIT))
    assert rw_refd.amount == Decimal(str(rewards_config.REFERRAL_REFERRED_CREDIT))

    # Ledger entries exist
    led = db.query(Reward).filter(Reward.referral_id == rel.id).all()
    assert len(led) == 2
    assert all(r.funding_source == "REFERRAL" for r in led)
    assert all(r.status == "AVAILABLE" for r in led)

    # Wallet projections updated
    w_ref = db.query(RewardWallet).filter(RewardWallet.user_id == referrer.id).one_or_none()
    w_refd = db.query(RewardWallet).filter(RewardWallet.user_id == referred.id).one_or_none()
    assert w_ref is not None and w_ref.referral_balance == Decimal("20.00")
    assert w_refd is not None and w_refd.referral_balance == Decimal("15.00")

    db.refresh(rel)
    assert rel.status == "REWARDED"


def test_award_referral_idempotent(db: Session, sample_tenant: Tenant) -> None:
    referrer = _user(db, sample_tenant, "i1@example.com", "REF_I1")
    referred = _user(db, sample_tenant, "i2@example.com", "REF_I2")
    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=referrer)
    rel = referral_engine.apply_code(db, tenant=sample_tenant, current_user=referred, code=rc.code)
    referral_engine.mark_verified(db, relationship=rel)
    b = _booking(db, sample_tenant, referred, amount="400.00")
    referral_engine.mark_qualified(db, relationship=rel, booking=b)

    referral_engine.award_referral(db, relationship=rel)
    second = referral_engine.award_referral(db, relationship=rel)
    assert second is None

    led = db.query(Reward).filter(Reward.referral_id == rel.id).all()
    assert len(led) == 2  # not 4


def test_award_referral_from_non_qualified_raises(db: Session, sample_tenant: Tenant) -> None:
    referrer = _user(db, sample_tenant, "n1@example.com", "REF_N1")
    referred = _user(db, sample_tenant, "n2@example.com", "REF_N2")
    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=referrer)
    rel = referral_engine.apply_code(db, tenant=sample_tenant, current_user=referred, code=rc.code)
    # still REGISTERED
    with pytest.raises(ValueError, match="cannot award"):
        referral_engine.award_referral(db, relationship=rel)


# ---------- queries ----------


def test_list_and_count(db: Session, sample_tenant: Tenant) -> None:
    referrer = _user(db, sample_tenant, "l1@example.com", "REF_L1")
    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=referrer)

    for i in range(3):
        refd = _user(db, sample_tenant, f"l_{i}@example.com", f"REF_L{i+2}")
        referral_engine.apply_code(db, tenant=sample_tenant, current_user=refd, code=rc.code)

    rows = referral_engine.list_my_referrals(db, referrer_user_id=referrer.id)
    assert len(rows) == 3
    counts = referral_engine.count_by_status(db, referrer_user_id=referrer.id)
    assert counts.get("REGISTERED") == 3


# ---------- events ----------


def test_events_emitted_for_lifecycle(db: Session, sample_tenant: Tenant) -> None:
    referrer = _user(db, sample_tenant, "e1@example.com", "REF_E1")
    referred = _user(db, sample_tenant, "e2@example.com", "REF_E2")
    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=referrer)
    rel = referral_engine.apply_code(db, tenant=sample_tenant, current_user=referred, code=rc.code)
    referral_engine.mark_verified(db, relationship=rel)
    b = _booking(db, sample_tenant, referred, amount="400.00")
    referral_engine.mark_qualified(db, relationship=rel, booking=b)
    referral_engine.award_referral(db, relationship=rel)

    events = (
        db.query(ReferralEvent)
        .filter(ReferralEvent.relationship_id == rel.id)
        .order_by(ReferralEvent.created_at.asc())
        .all()
    )
    types = [e.event_type for e in events]
    assert types == ["REGISTERED", "VERIFIED", "QUALIFIED", "REWARDED"]
