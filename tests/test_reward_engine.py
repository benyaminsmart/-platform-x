"""Tests for Reward Engine service (Phase 75, Step 2)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.reward import Reward
from app.models.reward_wallet import RewardWallet
from app.models.tenant import Tenant
from app.models.user import User
from app.services import reward_engine as re


def _tenant(db, slug="re-1"):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="u@x.com"):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X",
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def test_create_ledger_entry_available(db):
    t = _tenant(db)
    u = _user(db, t)
    r, st = re.create_ledger_entry(
        db, tenant=t, user=u, reward_type="PLATFORM_EARN",
        amount=Decimal("25.00"), status="AVAILABLE",
        transaction_id="tx-1",
    )
    assert st == "created"
    assert r.amount == Decimal("25.00")
    assert r.platform_cost == Decimal("25.00")

    w = re.get_or_create_wallet(db, user=u)
    assert w.available_balance == Decimal("25.00")


def test_idempotency_same_transaction(db):
    t = _tenant(db, "re-idem")
    u = _user(db, t, "idem@x.com")
    r1, st1 = re.create_ledger_entry(
        db, tenant=t, user=u, reward_type="PLATFORM_EARN",
        amount=Decimal("25.00"), status="AVAILABLE",
        transaction_id="tx-dup",
    )
    r2, st2 = re.create_ledger_entry(
        db, tenant=t, user=u, reward_type="PLATFORM_EARN",
        amount=Decimal("25.00"), status="AVAILABLE",
        transaction_id="tx-dup",
    )
    assert st1 == "created"
    assert st2 == "exists"
    assert r1.id == r2.id
    w = re.get_or_create_wallet(db, user=u)
    assert w.available_balance == Decimal("25.00")


def test_different_reward_types_same_tx(db):
    t = _tenant(db, "re-types")
    u = _user(db, t, "types@x.com")
    r1, _ = re.create_ledger_entry(
        db, tenant=t, user=u, reward_type="PLATFORM_EARN",
        amount=Decimal("10.00"), status="AVAILABLE",
        transaction_id="tx-multi",
    )
    r2, st = re.create_ledger_entry(
        db, tenant=t, user=u, reward_type="CAMPAIGN_BONUS",
        amount=Decimal("5.00"), status="AVAILABLE",
        transaction_id="tx-multi",
    )
    assert r1.id != r2.id
    assert st == "created"


def test_zero_amount_rejected(db):
    t = _tenant(db, "re-zero")
    u = _user(db, t, "zero@x.com")
    with pytest.raises(ValueError):
        re.create_ledger_entry(
            db, tenant=t, user=u, reward_type="X", amount=Decimal("0"),
        )


def test_locked_reward_into_wallet(db):
    t = _tenant(db, "re-locked")
    u = _user(db, t, "locked@x.com")
    re.create_ledger_entry(
        db, tenant=t, user=u, reward_type="PLATFORM_EARN",
        amount=Decimal("50.00"), status="LOCKED",
        transaction_id="tx-locked",
    )
    w = re.get_or_create_wallet(db, user=u)
    assert w.locked_balance == Decimal("50.00")
    assert w.available_balance == Decimal("0.00")


def test_referral_credit_goes_to_referral_balance(db):
    t = _tenant(db, "re-ref")
    u = _user(db, t, "ref@x.com")
    re.create_ledger_entry(
        db, tenant=t, user=u, reward_type="REFERRAL_REWARD",
        amount=Decimal("20.00"), funding_source="REFERRAL",
        status="AVAILABLE",
    )
    w = re.get_or_create_wallet(db, user=u)
    assert w.referral_balance == Decimal("20.00")
    assert w.available_balance == Decimal("20.00")


def test_experience_credit_separate(db):
    t = _tenant(db, "re-exp")
    u = _user(db, t, "exp@x.com")
    re.create_ledger_entry(
        db, tenant=t, user=u, reward_type="EXPERIENCE_CREDIT",
        amount=Decimal("30.00"), status="AVAILABLE",
    )
    w = re.get_or_create_wallet(db, user=u)
    assert w.experience_balance == Decimal("30.00")


def test_campaign_bonus_separate(db):
    t = _tenant(db, "re-camp")
    u = _user(db, t, "camp@x.com")
    re.create_ledger_entry(
        db, tenant=t, user=u, reward_type="CAMPAIGN_BONUS",
        amount=Decimal("15.00"), funding_source="CAMPAIGN",
        status="AVAILABLE",
    )
    w = re.get_or_create_wallet(db, user=u)
    assert w.bonus_balance == Decimal("15.00")


def test_rebuild_wallet_matches_ledger(db):
    t = _tenant(db, "re-rebuild")
    u = _user(db, t, "rebuild@x.com")
    re.create_ledger_entry(db, tenant=t, user=u, reward_type="A",
                            amount=Decimal("10.00"), status="AVAILABLE",
                            transaction_id="tx-a")
    re.create_ledger_entry(db, tenant=t, user=u, reward_type="B",
                            amount=Decimal("20.00"), status="AVAILABLE",
                            transaction_id="tx-b")
    re.create_ledger_entry(db, tenant=t, user=u, reward_type="C",
                            amount=Decimal("5.00"), status="LOCKED",
                            transaction_id="tx-c")
    w = re.rebuild_wallet(db, user=u)
    assert w.available_balance == Decimal("30.00")
    assert w.locked_balance == Decimal("5.00")


def test_wallet_summary(db):
    t = _tenant(db, "re-sum")
    u = _user(db, t, "sum@x.com")
    re.create_ledger_entry(db, tenant=t, user=u, reward_type="A",
                            amount=Decimal("40.00"), status="AVAILABLE",
                            transaction_id="tx-sum")
    s = re.wallet_summary(db, user=u)
    assert s["available_balance"] == 40.0
    assert s["currency"] == "AED"


def test_list_ledger(db):
    t = _tenant(db, "re-list")
    u = _user(db, t, "list@x.com")
    re.create_ledger_entry(db, tenant=t, user=u, reward_type="A",
                            amount=Decimal("10.00"), status="AVAILABLE")
    rows = re.list_ledger(db, user_id=u.id)
    assert len(rows) == 1
    assert rows[0]["amount"] == 10.0


def test_list_ledger_filtered_by_status(db):
    t = _tenant(db, "re-lf")
    u = _user(db, t, "lf@x.com")
    re.create_ledger_entry(db, tenant=t, user=u, reward_type="A",
                            amount=Decimal("10.00"), status="AVAILABLE")
    re.create_ledger_entry(db, tenant=t, user=u, reward_type="B",
                            amount=Decimal("5.00"), status="LOCKED")
    rows = re.list_ledger(db, user_id=u.id, status="LOCKED")
    assert len(rows) == 1
    assert rows[0]["status"] == "LOCKED"
