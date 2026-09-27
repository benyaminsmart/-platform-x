"""Auto-generate services per tenant based on config.type.

Idempotent — skips existing (tenant_id, name) pairs.
Run: python -m app.scripts.seed_services_auto
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.service import Service
from app.models.tenant import Tenant


TEMPLATES: dict[str, list[dict]] = {
    "hotel": [
        {"name": "Standard Double", "price_mult": 1.0, "capacity": 2,
         "attributes": {"bed": "double", "size_sqm": 28},
         "image": "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&q=80&auto=format&fit=crop"},
        {"name": "Deluxe Room", "price_mult": 1.5, "capacity": 2,
         "attributes": {"bed": "king", "size_sqm": 38, "view": "sea"},
         "image": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=800&q=80&auto=format&fit=crop"},
        {"name": "Executive Suite", "price_mult": 2.5, "capacity": 3,
         "attributes": {"bed": "king", "size_sqm": 55},
         "image": "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800&q=80&auto=format&fit=crop"},
        {"name": "Family Room", "price_mult": 2.0, "capacity": 4,
         "attributes": {"beds": "1 king + 2 singles", "size_sqm": 45},
         "image": "https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=800&q=80&auto=format&fit=crop"},
        {"name": "Royal Suite", "price_mult": 5.0, "capacity": 4,
         "attributes": {"bed": "king", "size_sqm": 90, "butler": True},
         "image": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800&q=80&auto=format&fit=crop"},
    ],
    "restaurant": [
        {"name": "Signature Starter", "price_mult": 1.0, "attributes": {"category": "starter"},
         "image": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&q=80&auto=format&fit=crop"},
        {"name": "Chef's Main", "price_mult": 3.5, "attributes": {"category": "main"},
         "image": "https://images.unsplash.com/photo-1544025162-d76694265947?w=800&q=80&auto=format&fit=crop"},
        {"name": "Signature Dessert", "price_mult": 1.2, "attributes": {"category": "dessert"},
         "image": "https://images.unsplash.com/photo-1551024506-0bccd828d307?w=800&q=80&auto=format&fit=crop"},
        {"name": "House Beverage", "price_mult": 0.5, "attributes": {"category": "beverage"},
         "image": "https://images.unsplash.com/photo-1544145945-f90425340c7e?w=800&q=80&auto=format&fit=crop"},
        {"name": "Tasting Menu", "price_mult": 5.0, "attributes": {"category": "menu", "courses": 7},
         "image": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800&q=80&auto=format&fit=crop"},
        {"name": "Vegetarian Plate", "price_mult": 2.5, "attributes": {"category": "main", "vegetarian": True},
         "image": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&q=80&auto=format&fit=crop"},
    ],
    "travel_agency": [
        {"name": "Weekend Getaway", "price_mult": 1.0, "capacity": 20,
         "attributes": {"duration_days": 3, "type": "city"},
         "image": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800&q=80&auto=format&fit=crop"},
        {"name": "7-Day Adventure", "price_mult": 3.0, "capacity": 15,
         "attributes": {"duration_days": 7, "type": "adventure"},
         "image": "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=800&q=80&auto=format&fit=crop"},
        {"name": "Luxury Escape", "price_mult": 5.5, "capacity": 8,
         "attributes": {"duration_days": 5, "type": "luxury"},
         "image": "https://images.unsplash.com/photo-1503220317375-aaad61436b1b?w=800&q=80&auto=format&fit=crop"},
        {"name": "Family Package", "price_mult": 2.5, "capacity": 25,
         "attributes": {"duration_days": 6, "type": "family", "kids_friendly": True},
         "image": "https://images.unsplash.com/photo-1519677100203-a0e668c92439?w=800&q=80&auto=format&fit=crop"},
        {"name": "Business Class Upgrade", "price_mult": 4.0, "capacity": 1,
         "attributes": {"type": "addon"},
         "image": "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=800&q=80&auto=format&fit=crop"},
    ],
    "entertainment": [
        {"name": "Day Pass", "price_mult": 1.0, "attributes": {"duration_hours": 8},
         "image": "https://images.unsplash.com/photo-1513889961551-628c1e5e2ee9?w=800&q=80&auto=format&fit=crop"},
        {"name": "Family Ticket (4)", "price_mult": 3.2, "attributes": {"group_size": 4},
         "image": "https://images.unsplash.com/photo-1560269507-d1f0a1f5b8c6?w=800&q=80&auto=format&fit=crop"},
        {"name": "VIP Experience", "price_mult": 3.5, "attributes": {"includes": ["fast track", "lounge"]},
         "image": "https://images.unsplash.com/photo-1520045653281-86dbc0c7e4c4?w=800&q=80&auto=format&fit=crop"},
        {"name": "Group Booking (10+)", "price_mult": 7.0, "attributes": {"group_size": 10, "discount": 0.15},
         "image": "https://images.unsplash.com/photo-1533130061792-64b345e4a833?w=800&q=80&auto=format&fit=crop"},
        {"name": "Annual Membership", "price_mult": 25.0, "attributes": {"duration_days": 365},
         "image": "https://images.unsplash.com/photo-1622979135225-d2ba269cf1ac?w=800&q=80&auto=format&fit=crop"},
    ],
}


def seed(db: Session) -> tuple[int, int]:
    created = 0
    skipped = 0
    for tenant in db.execute(select(Tenant)).scalars().all():
        cfg = tenant.config if isinstance(tenant.config, dict) else {}
        ttype = cfg.get("type", "")
        templates = TEMPLATES.get(ttype)
        if not templates:
            continue

        price_from = Decimal(str(cfg.get("price_from", 100)))
        currency = cfg.get("currency", "AED")
        service_type_legacy = {
            "hotel": "room",
            "restaurant": "dish",
            "travel_agency": "package",
            "entertainment": "ticket",
        }.get(ttype, "service")

        for idx, tmpl in enumerate(templates):
            exists = db.execute(
                select(Service).where(
                    Service.tenant_id == tenant.id,
                    Service.name == tmpl["name"],
                )
            ).scalar_one_or_none()
            if exists:
                skipped += 1
                continue

            price = (price_from * Decimal(str(tmpl["price_mult"]))).quantize(Decimal("0.01"))
            db.add(Service(
                tenant_id=tenant.id,
                type=service_type_legacy,
                name=tmpl["name"],
                description=tmpl.get("description"),
                price=price,
                currency=currency,
                capacity=tmpl.get("capacity"),
                attributes=tmpl.get("attributes", {}),
                image_urls=[tmpl["image"]] if tmpl.get("image") else [],
                status="active",
                display_order=idx + 1,
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
