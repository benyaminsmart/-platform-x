"""Tests for reward engine integration in payment flow (Phase 76, Step 2)."""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.reward import Reward
from app.models.reward_rule import RewardRule
from app.models.tenant import Tenant
from app.models.user import User
from app.services import payment_service, reward_engine


def _tenant(db, slug, typ="hotel"):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": typ})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email="u@x.com", tier="EXPLORER"):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X", tier=tier,
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def _rule(db, category, rate="0.0100", max_amt="200.00", min_amt="100.00"):
    existing = db.query(RewardRule).filter(RewardRule.category == category).one_or_none()
    if existing:
        existing.platform_reward_rate = Decimal(rate)
        existing.max_reward_amount = Decimal(max_amt)
        existing.min_transaction_amount = Decimal(min_amt)
        existing.enabled = True
        db.commit()
        return existing
    r = RewardRule(category=category, platform_reward_rate=Decimal(rate),
                   max_reward_amount=Decimal(max_amt),
                   min_transaction_amount=Decimal(min_amt), enabled=True)
    db.add(r); db.commit(); db.refresh(r)
    return r


def _booking(db, t, u, amount=1000):
    ci = date.today() + timedelta(days=30)
    b = Booking(tenant_id=t.id, user_id=u.id, booking_type="room",
                service_name="Room", check_in=ci,
                check_out=ci + timedelta(days=1), guests=1,
                amount=Decimal(str(amount)), discount=Decimal("0"),
                total_amount=Decimal(str(amount)), currency="AED",
                status="pending", payment_status="pending")
    db.add(b); db.commit(); db.refresh(b)
    return b


def _payment(db, t, u, b, ref="ref-1"):
    p = Payment(tenant_id=t.id, user_id=u.id, booking_id=b.id,
                amount=Decimal("1000"), currency="AED", provider="mock",
                provider_reference=ref, status="pending", method="mock")
    db.add(p); db.commit(); db.refresh(p)
    return p


def test_payment_creates_ledger_entry(db):
    t = _tenant(db, "rp-1")
    u = _user(db, t, "rp1@x.com", tier="EXPLORER")
    _rule(db, "HOTEL", rate="0.0100", max_amt="200.00")
    b = _booking(db, t, u, 1000)
    p = _payment(db, t, u, b, "rp-ref-1")

    payment_service.mark_success(db, provider_reference="rp-ref-1")

    rewards = db.query(Reward).filter(Reward.user_id == u.id).all()
    assert len(rewards) == 1
    assert rewards[0].amount == Decimal("10.00")
    assert rewards[0].status == "AVAILABLE"
    assert rewards[0].transaction_id == b.id

    w = reward_engine.get_or_create_wallet(db, user=u)
    assert w.available_balance == Decimal("10.00")


def test_payment_idempotent_no_double_reward(db):
    t = _tenant(db, "rp-2")
    u = _user(db, t, "rp2@x.com")
    _rule(db, "HOTEL")
    b = _booking(db, t, u, 1000)
    p = _payment(db, t, u, b, "rp-ref-2")

    payment_service.mark_success(db, provider_reference="rp-ref-2")
    payment_service.mark_success(db, provider_reference="rp-ref-2")

    rewards = db.query(Reward).filter(Reward.user_id == u.id).all()
    assert len(rewards) == 1

    w = reward_engine.get_or_create_wallet(db, user=u)
    assert w.available_balance == Decimal("10.00")


def test_vip_gets_multiplied_reward(db):
    t = _tenant(db, "rp-3")
    u = _user(db, t, "rp3@x.com", tier="VIP")
    _rule(db, "HOTEL", rate="0.0100", max_amt="500.00")
    b = _booking(db, t, u, 1000)
    p = _payment(db, t, u, b, "rp-ref-3")

    payment_service.mark_success(db, provider_reference="rp-ref-3")

    rewards = db.query(Reward).filter(Reward.user_id == u.id).all()
    assert len(rewards) == 1
    assert rewards[0].amount == Decimal("20.00")  # 10 base × 2.0 VIP


def test_below_minimum_creates_no_reward(db):
    t = _tenant(db, "rp-4")
    u = _user(db, t, "rp4@x.com")
    _rule(db, "HOTEL", min_amt="5000.00")
    b = _booking(db, t, u, 1000)
    _payment(db, t, u, b, "rp-ref-4")

    payment_service.mark_success(db, provider_reference="rp-ref-4")

    rewards = db.query(Reward).filter(Reward.user_id == u.id).all()
    assert len(rewards) == 0
