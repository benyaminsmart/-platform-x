"""Seed demo services for all tenants.

Run: python -m app.scripts.seed_services
Idempotent: skips if service with same (tenant, name) exists.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.service import Service
from app.models.tenant import Tenant


SERVICES: dict[str, list[dict]] = {
    "trianon-hotel": [
        {"type": "room", "name": "Standard Double", "price": "350.00", "capacity": 2,
         "attributes": {"bed": "double", "size_sqm": 28}, "display_order": 1},
        {"type": "room", "name": "Deluxe Room", "price": "550.00", "capacity": 2,
         "attributes": {"bed": "king", "size_sqm": 38, "view": "sea"}, "display_order": 2},
        {"type": "room", "name": "Executive Suite", "price": "900.00", "capacity": 3,
         "attributes": {"bed": "king", "size_sqm": 55, "view": "skyline"}, "display_order": 3},
        {"type": "room", "name": "Family Room", "price": "750.00", "capacity": 4,
         "attributes": {"beds": "1 king + 2 singles", "size_sqm": 45}, "display_order": 4},
        {"type": "room", "name": "Royal Suite", "price": "1800.00", "capacity": 4,
         "attributes": {"bed": "king", "size_sqm": 90, "view": "panoramic",
                        "butler": True}, "display_order": 5},
    ],
    "saffron-restaurant": [
        {"type": "dish", "name": "Hummus Beiruti", "price": "35.00", "display_order": 1,
         "attributes": {"category": "starter", "vegetarian": True}},
        {"type": "dish", "name": "Mixed Grill Platter", "price": "120.00", "display_order": 2,
         "attributes": {"category": "main", "serves": 2}},
        {"type": "dish", "name": "Lamb Kebab", "price": "75.00", "display_order": 3,
         "attributes": {"category": "main"}},
        {"type": "dish", "name": "Saffron Rice", "price": "30.00", "display_order": 4,
         "attributes": {"category": "side"}},
        {"type": "dish", "name": "Kunafa", "price": "40.00", "display_order": 5,
         "attributes": {"category": "dessert"}},
        {"type": "dish", "name": "Arabic Coffee", "price": "15.00", "display_order": 6,
         "attributes": {"category": "beverage"}},
    ],
    "skyways-travel": [
        {"type": "package", "name": "Dubai Weekend", "price": "1200.00",
         "attributes": {"duration_days": 3, "type": "city"},
         "display_order": 1, "capacity": 20},
        {"type": "package", "name": "Umrah Package", "price": "3500.00",
         "attributes": {"duration_days": 7, "type": "religious"},
         "display_order": 2, "capacity": 15},
        {"type": "package", "name": "Europe Tour 7 Days", "price": "8500.00",
         "attributes": {"duration_days": 7, "type": "multi-city"},
         "display_order": 3, "capacity": 25},
        {"type": "flight", "name": "Business Class Upgrade", "price": "2500.00",
         "attributes": {"type": "upgrade"}, "display_order": 4},
    ],
    "oasis-entertainment": [
        {"type": "ticket", "name": "Aquarium Ticket", "price": "120.00",
         "attributes": {"duration_hours": 3}, "display_order": 1},
        {"type": "ticket", "name": "Kids Play Zone", "price": "80.00",
         "attributes": {"age_range": "3-12", "duration_hours": 2}, "display_order": 2},
        {"type": "ticket", "name": "VR Experience", "price": "150.00",
         "attributes": {"duration_minutes": 45}, "display_order": 3},
        {"type": "ticket", "name": "Bowling Hour", "price": "200.00",
         "attributes": {"duration_hours": 1, "max_players": 6}, "display_order": 4},
    ],
    "desert-tours": [
        {"type": "tour", "name": "Morning Safari", "price": "350.00",
         "attributes": {"duration_hours": 4, "includes": ["pickup", "dune bashing"]},
         "display_order": 1, "capacity": 6},
        {"type": "tour", "name": "Evening Desert BBQ", "price": "550.00",
         "attributes": {"duration_hours": 6, "includes": ["bbq", "belly dance", "henna"]},
         "display_order": 2, "capacity": 10},
        {"type": "tour", "name": "Camel Ride", "price": "120.00",
         "attributes": {"duration_hours": 1}, "display_order": 3, "capacity": 4},
        {"type": "tour", "name": "Overnight Camp", "price": "1200.00",
         "attributes": {"duration_hours": 18, "includes": ["dinner", "tent", "breakfast"]},
         "display_order": 4, "capacity": 8},
    ],
}


def seed(db: Session) -> tuple[int, int]:
    """Insert services per tenant. Returns (created, skipped)."""
    created = 0
    skipped = 0
    for slug, items in SERVICES.items():
        tenant = db.execute(
            select(Tenant).where(Tenant.slug == slug)
        ).scalar_one_or_none()
        if tenant is None:
            print(f"! tenant {slug} not found, skipping")
            continue
        for item in items:
            exists = db.execute(
                select(Service).where(
                    Service.tenant_id == tenant.id,
                    Service.name == item["name"],
                )
            ).scalar_one_or_none()
            if exists:
                skipped += 1
                continue
            db.add(Service(
                tenant_id=tenant.id,
                type=item["type"],
                name=item["name"],
                description=item.get("description"),
                price=Decimal(item["price"]),
                currency="AED",
                capacity=item.get("capacity"),
                attributes=item.get("attributes", {}),
                image_urls=item.get("image_urls", []),
                status="active",
                display_order=item.get("display_order", 0),
            ))
            created += 1
    db.commit()
    return created, skipped


def main() -> None:
    with SessionLocal() as db:
        created, skipped = seed(db)
    print(f"Seed services complete: created={created}, skipped={skipped}")


if __name__ == "__main__":
    main()
