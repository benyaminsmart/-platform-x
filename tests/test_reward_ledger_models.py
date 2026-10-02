"""Tests for reward ledger + wallet + rules models (Phase 75, Step 1)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.rewards_config import (
    CATEGORY_RATES, DEFAULT_TIER, LEGACY_TIER_MAP, TIERS,
    multiplier_for_tier, tier_for_transactions,
)
from app.core.security import hash_password
from app.models.reward import Reward, FUNDING_SOURCES, REWARD_STATUSES
from app.models.reward_rule import RewardRule
from app.models.reward_wallet import RewardWallet
from app.models.tenant import Tenant
from app.models.user import User


def _tenant(db, slug="rw-1"):
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


def test_enums_present():
    assert "PLATFORM" in FUNDING_SOURCES
    assert "AVAILABLE" in REWARD_STATUSES
    assert "EXPIRED" in REWARD_STATUSES


def test_reward_ledger_row(db):
    t = _tenant(db, "rw-ledger")
    u = _user(db, t)
    r = Reward(
        tenant_id=t.id, user_id=u.id, reward_type="PLATFORM_EARN",
        amount=Decimal("25.00"), currency="AED",
        funding_source="PLATFORM", platform_cost=Decimal("25.00"),
        status="AVAILABLE", points=25,
        available_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=60),
    )
    db.add(r); db.commit(); db.refresh(r)
    assert r.status == "AVAILABLE"
    assert r.funding_source == "PLATFORM"
    assert r.amount == Decimal("25.00")
    assert r.points == 25


def test_reward_wallet_defaults(db):
    t = _tenant(db, "rw-wallet")
    u = _user(db, t, "wallet@x.com")
    w = RewardWallet(tenant_id=t.id, user_id=u.id)
    db.add(w); db.commit(); db.refresh(w)
    assert w.available_balance == Decimal("0.00")
    assert w.currency == "AED"


def test_reward_rule_seed_present(db):
    # seed script was already run (or tests run on empty DB)
    db.query(RewardRule).delete()
    db.commit()
    from app.scripts import seed_reward_rules as srr
    n = srr._seed(db)
    assert n == 4
    rules = db.query(RewardRule).all()
    cats = {r.category for r in rules}
    assert {"HOTEL", "FLIGHT", "EXPERIENCE", "DINING"} <= cats


def test_tier_for_transactions():
    assert tier_for_transactions(0) == "EXPLORER"
    assert tier_for_transactions(2) == "EXPLORER"
    assert tier_for_transactions(3) == "TRAVELER"
    assert tier_for_transactions(5) == "TRAVELER"
    assert tier_for_transactions(6) == "INSIDER"
    assert tier_for_transactions(9) == "INSIDER"
    assert tier_for_transactions(10) == "VIP"
    assert tier_for_transactions(50) == "VIP"


def test_multiplier_for_tier():
    assert multiplier_for_tier("EXPLORER") == Decimal("1.00")
    assert multiplier_for_tier("TRAVELER") == Decimal("1.25")
    assert multiplier_for_tier("INSIDER") == Decimal("1.50")
    assert multiplier_for_tier("VIP") == Decimal("2.00")
    assert multiplier_for_tier("UNKNOWN") == Decimal("1.00")


def test_legacy_tier_migration_map():
    assert LEGACY_TIER_MAP["welcome"] == "EXPLORER"
    assert LEGACY_TIER_MAP["silver"] == "TRAVELER"
    assert LEGACY_TIER_MAP["gold"] == "INSIDER"
    assert LEGACY_TIER_MAP["platinum"] == "VIP"
    assert LEGACY_TIER_MAP["royal"] == "VIP"


def test_category_rates_are_configured():
    for cat in ("HOTEL", "FLIGHT", "EXPERIENCE", "DINING"):
        assert cat in CATEGORY_RATES
        assert CATEGORY_RATES[cat]["platform_reward_rate"] > 0
        assert CATEGORY_RATES[cat]["max_reward_amount"] > 0


def test_tiers_are_ordered():
    mins = [t["min_transactions"] for t in TIERS]
    assert mins == sorted(mins)
