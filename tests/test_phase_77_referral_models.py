"""Phase 77 Step 1 — Referral models tests.

Verifies:
- the four new tables exist and are usable
- constants (statuses, event types) are exported
- a ReferralCode can be created for a user
- a ReferralRelationship can move through the lifecycle
- a ReferralEvent can be appended
- a ReferralReward can be created and linked to a ledger Reward
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.referral_code import ReferralCode
from app.models.referral_event import ReferralEvent, REFERRAL_EVENT_TYPES
from app.models.referral_relationship import (
    ReferralRelationship,
    REFERRAL_STATUSES,
)
from app.models.referral_reward import ReferralReward, REFERRAL_REWARD_STATUSES
from app.models.reward import Reward
from app.models.tenant import Tenant
from app.models.user import User


def test_referral_statuses_exported() -> None:
    assert "INVITED" in REFERRAL_STATUSES
    assert "REGISTERED" in REFERRAL_STATUSES
    assert "VERIFIED" in REFERRAL_STATUSES
    assert "QUALIFIED" in REFERRAL_STATUSES
    assert "REWARDED" in REFERRAL_STATUSES
    assert "REVERSED" in REFERRAL_STATUSES
    assert "EXPIRED" in REFERRAL_STATUSES
    assert "REVIEW" in REFERRAL_STATUSES


def test_referral_event_types_exported() -> None:
    assert "CODE_GENERATED" in REFERRAL_EVENT_TYPES
    assert "QUALIFIED" in REFERRAL_EVENT_TYPES
    assert "REWARDED" in REFERRAL_EVENT_TYPES
    assert "REVIEW_FLAGGED" in REFERRAL_EVENT_TYPES


def test_referral_reward_statuses_exported() -> None:
    assert set(REFERRAL_REWARD_STATUSES) == {"PENDING", "ISSUED", "REVERSED", "CANCELLED"}


def _make_user(db: Session, tenant: Tenant, email: str, code: str) -> User:
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


def test_referral_code_created_for_user(db: Session, sample_tenant: Tenant) -> None:
    u = _make_user(db, sample_tenant, "rc1@example.com", "CODE_RC1")

    rc = ReferralCode(
        tenant_id=sample_tenant.id,
        user_id=u.id,
        code="CODE_RC1",
        is_default=True,
    )
    db.add(rc)
    db.commit()
    db.refresh(rc)

    assert rc.id
    assert rc.code == "CODE_RC1"
    assert rc.is_default is True
    assert rc.is_active is True


def test_referral_relationship_lifecycle(db: Session, sample_tenant: Tenant) -> None:
    referrer = _make_user(db, sample_tenant, "r1@example.com", "CODE_R1")
    referred = _make_user(db, sample_tenant, "r2@example.com", "CODE_R2")

    rc = ReferralCode(
        tenant_id=sample_tenant.id, user_id=referrer.id, code="CODE_R1", is_default=True
    )
    db.add(rc)
    db.commit()
    db.refresh(rc)

    rel = ReferralRelationship(
        tenant_id=sample_tenant.id,
        referral_code_id=rc.id,
        referrer_user_id=referrer.id,
        referred_user_id=referred.id,
        status="INVITED",
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)

    assert rel.status == "INVITED"

    rel.status = "REGISTERED"
    db.commit()
    db.refresh(rel)
    assert rel.status == "REGISTERED"


def test_referral_event_append(db: Session, sample_tenant: Tenant) -> None:
    referrer = _make_user(db, sample_tenant, "e1@example.com", "CODE_E1")
    referred = _make_user(db, sample_tenant, "e2@example.com", "CODE_E2")
    rc = ReferralCode(tenant_id=sample_tenant.id, user_id=referrer.id, code="CODE_E1")
    db.add(rc)
    db.commit()
    db.refresh(rc)
    rel = ReferralRelationship(
        tenant_id=sample_tenant.id,
        referral_code_id=rc.id,
        referrer_user_id=referrer.id,
        referred_user_id=referred.id,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)

    ev = ReferralEvent(
        tenant_id=sample_tenant.id,
        relationship_id=rel.id,
        event_type="REGISTERED",
        from_status="INVITED",
        to_status="REGISTERED",
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    assert ev.id
    assert ev.event_type == "REGISTERED"
    assert ev.extra == {}


def test_referral_reward_links_ledger(db: Session, sample_tenant: Tenant) -> None:
    referrer = _make_user(db, sample_tenant, "rr1@example.com", "CODE_RR1")
    referred = _make_user(db, sample_tenant, "rr2@example.com", "CODE_RR2")
    rc = ReferralCode(tenant_id=sample_tenant.id, user_id=referrer.id, code="CODE_RR1")
    db.add(rc)
    db.commit()
    db.refresh(rc)
    rel = ReferralRelationship(
        tenant_id=sample_tenant.id,
        referral_code_id=rc.id,
        referrer_user_id=referrer.id,
        referred_user_id=referred.id,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)

    ledger = Reward(
        tenant_id=sample_tenant.id,
        user_id=referrer.id,
        reward_type="REFERRAL_BONUS",
        amount=Decimal("20.00"),
        funding_source="REFERRAL",
        status="AVAILABLE",
    )
    db.add(ledger)
    db.commit()
    db.refresh(ledger)

    rw = ReferralReward(
        tenant_id=sample_tenant.id,
        relationship_id=rel.id,
        user_id=referrer.id,
        side="REFERRER",
        amount=Decimal("20.00"),
        status="ISSUED",
        ledger_reward_id=ledger.id,
    )
    db.add(rw)
    db.commit()
    db.refresh(rw)

    assert rw.id
    assert rw.side == "REFERRER"
    assert rw.amount == Decimal("20.00")
    assert rw.ledger_reward_id == ledger.id
