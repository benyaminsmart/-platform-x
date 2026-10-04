"""Phase 77 Step 3 — fraud checks + monthly limits tests.

Note on DB constraints: `users` has a UNIQUE(tenant_id, phone) constraint,
so two users with the same phone cannot live in the same tenant. For the
same-phone scenario we therefore put the two users in different tenants
and create the relationship explicitly.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import rewards_config
from app.models.booking import Booking
from app.models.referral_code import ReferralCode
from app.models.referral_event import ReferralEvent
from app.models.referral_relationship import ReferralRelationship
from app.models.referral_reward import ReferralReward
from app.models.reward import Reward
from app.models.tenant import Tenant
from app.models.user import User
from app.services import referral_engine, referral_fraud, referral_limits


def _user(
    db: Session, tenant: Tenant, email: str, code: str, phone: str | None = None
) -> User:
    u = User(
        tenant_id=tenant.id,
        email=email,
        password_hash="x",
        first_name="A",
        last_name="B",
        referral_code=code,
        phone=phone,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _booking(
    db: Session, tenant: Tenant, user: User, *, amount: str = "400.00"
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
        status="confirmed",
        payment_status="paid",
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


# ---------- individual checks ----------


def test_same_phone_flagged(db: Session, sample_tenant: Tenant) -> None:
    """Same phone across tenants is possible; the check itself only
    compares phone strings, so we build two User objects in memory."""
    r = User(
        tenant_id=sample_tenant.id, email="p1@example.com", password_hash="x",
        first_name="A", last_name="B", referral_code="P1", phone="+971500000001",
    )
    a = User(
        tenant_id=sample_tenant.id, email="p2@example.com", password_hash="x",
        first_name="A", last_name="B", referral_code="P2", phone="+971500000001",
    )
    assert referral_fraud.check_same_phone(r, a) == "same_phone"


def test_different_phone_not_flagged(db: Session, sample_tenant: Tenant) -> None:
    r = _user(db, sample_tenant, "p3@example.com", "P3", phone="+971500000002")
    a = _user(db, sample_tenant, "p4@example.com", "P4", phone="+971500000003")
    assert referral_fraud.check_same_phone(r, a) is None


def test_circular_detected(db: Session, sample_tenant: Tenant) -> None:
    a = _user(db, sample_tenant, "c1@example.com", "C1")
    b = _user(db, sample_tenant, "c2@example.com", "C2")
    rc_a = referral_engine.generate_code(db, tenant=sample_tenant, user=a)
    rc_b = referral_engine.generate_code(db, tenant=sample_tenant, user=b)

    referral_engine.apply_code(db, tenant=sample_tenant, current_user=b, code=rc_a.code)
    referral_engine.apply_code(db, tenant=sample_tenant, current_user=a, code=rc_b.code)

    assert referral_fraud.check_circular(db, referrer=a, referred=b) == "circular_referral"


def test_velocity_flagged(db: Session, sample_tenant: Tenant) -> None:
    referrer = _user(db, sample_tenant, "v1@example.com", "V1")
    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=referrer)
    n = rewards_config.REFERRAL_VELOCITY_MAX_PER_24H + 2
    for i in range(n):
        refd = _user(db, sample_tenant, f"v_{i}@example.com", f"V{i+2}")
        referral_engine.apply_code(db, tenant=sample_tenant, current_user=refd, code=rc.code)
    assert referral_fraud.check_velocity(db, referrer) == "velocity_24h"


# ---------- orchestrator (PASS path) ----------


def test_evaluate_pass_clean(db: Session, sample_tenant: Tenant) -> None:
    referrer = _user(db, sample_tenant, "ok1@example.com", "OK1")
    referred = _user(db, sample_tenant, "ok2@example.com", "OK2")
    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=referrer)
    rel = referral_engine.apply_code(db, tenant=sample_tenant, current_user=referred, code=rc.code)
    referral_engine.mark_verified(db, relationship=rel)
    b = _booking(db, sample_tenant, referred)
    referral_engine.mark_qualified(db, relationship=rel, booking=b)

    res = referral_fraud.evaluate(db, relationship=rel, booking=b)
    # The test user was just created and immediately booked, so
    # `new_account_fast_booking` (a weak, 15-point flag) may appear.
    # The threshold is 30, so the decision must still be PASS.
    assert res.decision == "PASS"
    assert res.score < rewards_config.REFERRAL_FRAUD_REVIEW_THRESHOLD


# ---------- orchestrator (REVIEW path) — via circular, which we can
# easily construct without violating the phone constraint ----------


def test_evaluate_review_circular(db: Session, sample_tenant: Tenant) -> None:
    a = _user(db, sample_tenant, "rv1@example.com", "RV1")
    b = _user(db, sample_tenant, "rv2@example.com", "RV2")
    rc_a = referral_engine.generate_code(db, tenant=sample_tenant, user=a)
    rc_b = referral_engine.generate_code(db, tenant=sample_tenant, user=b)

    rel = referral_engine.apply_code(db, tenant=sample_tenant, current_user=b, code=rc_a.code)
    referral_engine.apply_code(db, tenant=sample_tenant, current_user=a, code=rc_b.code)
    referral_engine.mark_verified(db, relationship=rel)
    bk = _booking(db, sample_tenant, b)
    referral_engine.mark_qualified(db, relationship=rel, booking=bk)

    res = referral_fraud.evaluate(db, relationship=rel, booking=bk)
    assert res.decision == "REVIEW"
    assert "circular_referral" in res.flags


def test_award_flags_review_on_circular(db: Session, sample_tenant: Tenant) -> None:
    a = _user(db, sample_tenant, "fg1@example.com", "FG1")
    b = _user(db, sample_tenant, "fg2@example.com", "FG2")
    rc_a = referral_engine.generate_code(db, tenant=sample_tenant, user=a)
    rc_b = referral_engine.generate_code(db, tenant=sample_tenant, user=b)

    rel = referral_engine.apply_code(db, tenant=sample_tenant, current_user=b, code=rc_a.code)
    referral_engine.apply_code(db, tenant=sample_tenant, current_user=a, code=rc_b.code)
    referral_engine.mark_verified(db, relationship=rel)
    bk = _booking(db, sample_tenant, b)
    referral_engine.mark_qualified(db, relationship=rel, booking=bk)

    result = referral_engine.award_referral(db, relationship=rel)
    assert result is None
    db.refresh(rel)
    assert rel.status == "REVIEW"
    assert rel.review_reason and "circular_referral" in rel.review_reason
    led = db.query(Reward).filter(Reward.referral_id == rel.id).all()
    assert led == []


# ---------- monthly limits ----------


def test_monthly_credit_used_zero_initially(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "m1@example.com", "M1")
    assert referral_limits.monthly_credit_used(db, user_id=u.id) == Decimal("0")


def test_can_credit_within_limit(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "m2@example.com", "M2")
    ok, head = referral_limits.can_credit(db, user_id=u.id, amount=Decimal("20"))
    assert ok is True
    assert head == Decimal("80")


def test_can_credit_at_limit(db: Session, sample_tenant: Tenant) -> None:
    u = _user(db, sample_tenant, "m3@example.com", "M3")
    rw = ReferralReward(
        tenant_id=sample_tenant.id,
        relationship_id="x",
        user_id=u.id,
        side="REFERRER",
        amount=Decimal("90"),
        status="ISSUED",
        issued_at=datetime.now(timezone.utc),
    )
    db.add(rw)
    db.commit()

    ok, head = referral_limits.can_credit(db, user_id=u.id, amount=Decimal("20"))
    assert ok is False
    assert head == Decimal("10")


def test_award_defers_when_limit_hit(db: Session, sample_tenant: Tenant) -> None:
    referrer = _user(db, sample_tenant, "lm1@example.com", "LM1")
    referred = _user(db, sample_tenant, "lm2@example.com", "LM2")

    db.add(ReferralReward(
        tenant_id=sample_tenant.id,
        relationship_id="prior",
        user_id=referrer.id,
        side="REFERRER",
        amount=Decimal("90"),
        status="ISSUED",
        issued_at=datetime.now(timezone.utc),
    ))
    db.commit()

    rc = referral_engine.generate_code(db, tenant=sample_tenant, user=referrer)
    rel = referral_engine.apply_code(db, tenant=sample_tenant, current_user=referred, code=rc.code)
    referral_engine.mark_verified(db, relationship=rel)
    b = _booking(db, sample_tenant, referred)
    referral_engine.mark_qualified(db, relationship=rel, booking=b)

    result = referral_engine.award_referral(db, relationship=rel)
    assert result is None
    db.refresh(rel)
    assert rel.status == "QUALIFIED"

    events = (
        db.query(ReferralEvent)
        .filter(ReferralEvent.relationship_id == rel.id)
        .order_by(ReferralEvent.created_at.asc())
        .all()
    )
    assert any(e.event_type == "REWARD_DEFERRED" for e in events)

    led = db.query(Reward).filter(Reward.referral_id == rel.id).all()
    assert led == []
