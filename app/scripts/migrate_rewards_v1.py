"""Migrate users to the new reward tiers + backfill reward wallets.

Phase 75, Step 3.

Idempotent: safe to run multiple times.

Steps:
1. Map legacy tier names (welcome/silver/gold/platinum/royal) to the
   new names (EXPLORER/TRAVELER/INSIDER/VIP) using LEGACY_TIER_MAP.
2. For each user, rebuild the reward wallet from the existing ledger
   (Reward rows), so balances reflect history.
"""

from __future__ import annotations

from app.core.rewards_config import LEGACY_TIER_MAP
from app.db.session import SessionLocal
from app.models.user import User
from app.services import reward_engine


def migrate_tiers(db) -> int:
    """Rewrite user.tier from legacy to new name. Returns count updated."""
    updated = 0
    users = db.query(User).all()
    for u in users:
        new_tier = LEGACY_TIER_MAP.get(u.tier)
        if new_tier and new_tier != u.tier:
            u.tier = new_tier
            updated += 1
    if updated:
        db.commit()
    return updated


def backfill_wallets(db) -> int:
    """Rebuild every user's wallet from the ledger."""
    rebuilt = 0
    users = db.query(User).all()
    for u in users:
        reward_engine.rebuild_wallet(db, user=u)
        rebuilt += 1
    return rebuilt


def main() -> None:
    db = SessionLocal()
    try:
        n_tiers = migrate_tiers(db)
        print(f"Tier migrations applied: {n_tiers}")
        n_wallets = backfill_wallets(db)
        print(f"Wallets rebuilt: {n_wallets}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
