"""Seed default redeem options (TEMPORARY POLICY).

Phase 44 note: This catalog is temporary. The final catalog will be
defined by the user's Rewards + Referral business plan (Phase 24).
Changing values here + re-running is safe and idempotent.
"""

from decimal import Decimal

from app.db.session import SessionLocal
from app.models.redeem_option import RedeemOption


DEMO = [
    {
        "name": "25 AED booking credit",
        "description": "Get 25 AED off your next booking.",
        "points_cost": 500,
        "reward_type": "credit",
        "reward_value": Decimal("25.00"),
        "display_order": 10,
    },
    {
        "name": "50 AED booking credit",
        "description": "Get 50 AED off your next booking.",
        "points_cost": 1000,
        "reward_type": "credit",
        "reward_value": Decimal("50.00"),
        "display_order": 20,
    },
    {
        "name": "100 AED booking credit",
        "description": "Get 100 AED off your next booking.",
        "points_cost": 2000,
        "reward_type": "credit",
        "reward_value": Decimal("100.00"),
        "display_order": 30,
    },
]


def seed():
    created = 0
    with SessionLocal() as db:
        for data in DEMO:
            existing = (
                db.query(RedeemOption)
                .filter(RedeemOption.name == data["name"])
                .one_or_none()
            )
            if existing:
                continue
            db.add(RedeemOption(**data, active=True))
            created += 1
        db.commit()
    print(f"seeded redeem options: {created}")


if __name__ == "__main__":
    seed()
