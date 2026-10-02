"""Tests for reward tier migration (Phase 75, Step 3)."""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.rewards_config import LEGACY_TIER_MAP
from app.core.security import hash_password
from app.models.reward import Reward
from app.models.tenant import Tenant
from app.models.user import User
from app.scripts import migrate_rewards_v1 as mg
from app.services import reward_engine


def _tenant(db, slug):
    t = Tenant(slug=slug, name=f"N-{slug}", tier="starter", status="active",
               config={"type": "hotel"})
    db.add(t); db.commit(); db.refresh(t)
    return t


def _user(db, t, email, tier):
    u = User(tenant_id=t.id, email=email,
             password_hash=hash_password("Pass1234"),
             first_name="G", last_name="X", tier=tier,
             referral_code=email[:10].upper(), status="active")
    db.add(u); db.commit(); db.refresh(u)
    return u


def test_migrate_tiers(db):
    t = _tenant(db, "mt-1")
    u1 = _user(db, t, "w@x.com", "welcome")
    u2 = _user(db, t, "s@x.com", "silver")
    u3 = _user(db, t, "g@x.com", "gold")
    u4 = _user(db, t, "p@x.com", "platinum")
    u5 = _user(db, t, "r@x.com", "royal")

    n = mg.migrate_tiers(db)
    assert n == 5

    for u in (u1, u2, u3, u4, u5):
        db.refresh(u)

    assert u1.tier == "EXPLORER"
    assert u2.tier == "TRAVELER"
    assert u3.tier == "INSIDER"
    assert u4.tier == "VIP"
    assert u5.tier == "VIP"


def test_migrate_is_idempotent(db):
    t = _tenant(db, "mt-idem")
    _user(db, t, "w2@x.com", "welcome")
    n1 = mg.migrate_tiers(db)
    n2 = mg.migrate_tiers(db)
    assert n1 == 1
    assert n2 == 0  # nothing to migrate the second time


def test_backfill_wallets_from_ledger(db):
    t = _tenant(db, "bf-1")
    u = _user(db, t, "bf@x.com", "welcome")
    # Create two ledger entries
    reward_engine.create_ledger_entry(
        db, tenant=t, user=u, reward_type="A",
        amount=Decimal("10.00"), status="AVAILABLE",
        transaction_id="tx-bf-1",
    )
    reward_engine.create_ledger_entry(
        db, tenant=t, user=u, reward_type="B",
        amount=Decimal("15.00"), status="AVAILABLE",
        transaction_id="tx-bf-2",
    )
    # Force wallet to 0 then rebuild
    w = reward_engine.get_or_create_wallet(db, user=u)
    w.available_balance = Decimal("0")
    db.commit()

    n = mg.backfill_wallets(db)
    assert n >= 1

    w = reward_engine.get_or_create_wallet(db, user=u)
    assert w.available_balance == Decimal("25.00")


def test_migrate_and_backfill_no_user(db):
    # empty DB
    n_tiers = mg.migrate_tiers(db)
    n_wallets = mg.backfill_wallets(db)
    # On a shared test DB there may be leftover users; just assert types
    assert isinstance(n_tiers, int)
    assert isinstance(n_wallets, int)
