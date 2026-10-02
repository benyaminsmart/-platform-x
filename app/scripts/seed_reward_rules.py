"""Seed reward rules with the plan's initial category targets.

Phase 75, Step 1. Idempotent.
"""

from __future__ import annotations

from decimal import Decimal

from app.core.rewards_config import CATEGORY_RATES
from app.db.session import SessionLocal
from app.models.reward_rule import RewardRule


def _seed(db) -> int:
    inserted = 0
    for category, cfg in CATEGORY_RATES.items():
        existing = db.query(RewardRule).filter(RewardRule.category == category).one_or_none()
        if existing is not None:
            continue
        db.add(RewardRule(
            category=category,
            platform_reward_rate=Decimal(str(cfg["platform_reward_rate"])),
            max_reward_amount=Decimal(str(cfg["max_reward_amount"])),
            min_transaction_amount=Decimal(str(cfg["min_transaction_amount"])),
            enabled=True,
        ))
        inserted += 1
    if inserted:
        db.commit()
    return inserted


def main() -> None:
    db = SessionLocal()
    try:
        n = _seed(db)
        if n == 0:
            print("reward_rules already seeded — skipping")
        else:
            print(f"Seeded {n} reward rules")
    finally:
        db.close()


if __name__ == "__main__":
    main()
