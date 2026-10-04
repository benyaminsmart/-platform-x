"""Seed the real redeem catalog (Phase 79, plan §15).

Replaces the Phase 44 TEMP catalog with a structured catalog that
carries platform_cost, funding_source, and category metadata.

Idempotent: existing options are updated in place (matched by name),
not duplicated.
"""

from __future__ import annotations

from decimal import Decimal

from app.db.session import SessionLocal
from app.models.redeem_option import RedeemOption


CATALOG = [
    # --- Booking credits (platform-funded) ---
    {
        "name": "AED 25 booking credit",
        "description": "Get AED 25 off your next booking.",
        "points_cost": 500,
        "reward_type": "credit",
        "reward_value": Decimal("25.00"),
        "display_order": 10,
        "platform_cost": Decimal("25.00"),
        "funding_source": "PLATFORM",
        "category": None,
    },
    {
        "name": "AED 50 booking credit",
        "description": "Get AED 50 off your next booking.",
        "points_cost": 1000,
        "reward_type": "credit",
        "reward_value": Decimal("50.00"),
        "display_order": 20,
        "platform_cost": Decimal("50.00"),
        "funding_source": "PLATFORM",
        "category": None,
    },
    {
        "name": "AED 100 booking credit",
        "description": "Get AED 100 off your next booking.",
        "points_cost": 2000,
        "reward_type": "credit",
        "reward_value": Decimal("100.00"),
        "display_order": 30,
        "platform_cost": Decimal("100.00"),
        "funding_source": "PLATFORM",
        "category": None,
    },
    # --- Experience credits (restricted category) ---
    {
        "name": "AED 30 experience credit",
        "description": "AED 30 off any experience booking (tours, tickets).",
        "points_cost": 600,
        "reward_type": "credit",
        "reward_value": Decimal("30.00"),
        "display_order": 40,
        "platform_cost": Decimal("30.00"),
        "funding_source": "PLATFORM",
        "category": "EXPERIENCE",
    },
    {
        "name": "AED 60 experience credit",
        "description": "AED 60 off any experience booking.",
        "points_cost": 1200,
        "reward_type": "credit",
        "reward_value": Decimal("60.00"),
        "display_order": 50,
        "platform_cost": Decimal("60.00"),
        "funding_source": "PLATFORM",
        "category": "EXPERIENCE",
    },
    # --- Dining credits ---
    {
        "name": "AED 20 dining credit",
        "description": "AED 20 off your next dining booking.",
        "points_cost": 400,
        "reward_type": "credit",
        "reward_value": Decimal("20.00"),
        "display_order": 60,
        "platform_cost": Decimal("20.00"),
        "funding_source": "PLATFORM",
        "category": "DINING",
    },
    # --- Hotel partner-funded perk (demonstrates partner funding) ---
    {
        "name": "Free room upgrade (partner)",
        "description": "Complimentary room upgrade on your next hotel stay.",
        "points_cost": 2500,
        "reward_type": "perk",
        "reward_value": Decimal("150.00"),
        "display_order": 70,
        "platform_cost": Decimal("0.00"),
        "funding_source": "PARTNER",
        "category": "HOTEL",
    },
]


LEGACY_NAMES = (
    "25 AED booking credit",
    "50 AED booking credit",
    "100 AED booking credit",
)


def seed() -> int:
    created = 0
    updated = 0
    with SessionLocal() as db:
        # Deactivate any legacy options from the Phase 44 TEMP catalog.
        for legacy_name in LEGACY_NAMES:
            row = (
                db.query(RedeemOption)
                .filter(RedeemOption.name == legacy_name)
                .one_or_none()
            )
            if row is not None and row.active:
                row.active = False

        for data in CATALOG:
            existing = (
                db.query(RedeemOption)
                .filter(RedeemOption.name == data["name"])
                .one_or_none()
            )
            if existing is None:
                db.add(RedeemOption(
                    name=data["name"],
                    description=data["description"],
                    points_cost=data["points_cost"],
                    reward_type=data["reward_type"],
                    reward_value=data["reward_value"],
                    display_order=data["display_order"],
                    platform_cost=data["platform_cost"],
                    funding_source=data["funding_source"],
                    category=data["category"],
                    active=True,
                ))
                created += 1
            else:
                existing.description = data["description"]
                existing.points_cost = data["points_cost"]
                existing.reward_type = data["reward_type"]
                existing.reward_value = data["reward_value"]
                existing.display_order = data["display_order"]
                existing.platform_cost = data["platform_cost"]
                existing.funding_source = data["funding_source"]
                existing.category = data["category"]
                existing.active = True
                updated += 1
        db.commit()
    print(f"Redeem catalog seeded: {created} created, {updated} updated")
    return created + updated


def main() -> None:
    seed()


if __name__ == "__main__":
    main()
