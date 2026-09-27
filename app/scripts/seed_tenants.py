"""Seed demo tenants for Platform-X demo environment.

Run: python -m app.scripts.seed_tenants
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.tenant import Tenant


DEMO_TENANTS = [
    {
        "slug": "trianon-hotel",
        "name": "Trianon Hotel",
        "tier": "professional",
        "config": {
            "type": "hotel",
            "tagline": "Luxury stay in the heart of the city",
            "branding": {
                "primary_color": "#1B3A5C",
                "secondary_color": "#C9A961",
                "accent_color": "#F5F1EA",
                "font_heading": "Playfair Display",
                "font_body": "Inter",
                "logo_url": "/static/logos/trianon.svg",
            },
            "languages": ["en", "ar", "fil", "hi"],
            "default_language": "en",
            "currency": "AED",
            "contact": {
                "phone": "+971-4-000-0000",
                "email": "info@trianon.example",
                "address": "Downtown, Dubai, UAE",
            },
        },
    },
    {
        "slug": "saffron-restaurant",
        "name": "Saffron Restaurant",
        "tier": "professional",
        "config": {
            "type": "restaurant",
            "tagline": "Modern Middle Eastern cuisine",
            "branding": {
                "primary_color": "#7A1E1E",
                "secondary_color": "#E8B44C",
                "accent_color": "#FFF8EC",
                "font_heading": "Cormorant Garamond",
                "font_body": "Inter",
                "logo_url": "/static/logos/saffron.svg",
            },
            "languages": ["en", "ar"],
            "default_language": "en",
            "currency": "AED",
            "contact": {
                "phone": "+971-4-111-1111",
                "email": "hello@saffron.example",
                "address": "Marina Walk, Dubai, UAE",
            },
        },
    },
    {
        "slug": "skyways-travel",
        "name": "Skyways Travel",
        "tier": "professional",
        "config": {
            "type": "travel_agency",
            "tagline": "Your journey, our expertise",
            "branding": {
                "primary_color": "#0A4D8C",
                "secondary_color": "#00B4D8",
                "accent_color": "#F0F8FF",
                "font_heading": "Poppins",
                "font_body": "Inter",
                "logo_url": "/static/logos/skyways.svg",
            },
            "languages": ["en", "ar", "fil", "hi"],
            "default_language": "en",
            "currency": "AED",
            "contact": {
                "phone": "+971-4-222-2222",
                "email": "book@skyways.example",
                "address": "Business Bay, Dubai, UAE",
            },
        },
    },
    {
        "slug": "oasis-entertainment",
        "name": "Oasis Entertainment",
        "tier": "starter",
        "config": {
            "type": "entertainment",
            "tagline": "Fun for the whole family",
            "branding": {
                "primary_color": "#2E7D32",
                "secondary_color": "#FFB300",
                "accent_color": "#F1F8E9",
                "font_heading": "Nunito",
                "font_body": "Inter",
                "logo_url": "/static/logos/oasis.svg",
            },
            "languages": ["en", "ar"],
            "default_language": "en",
            "currency": "AED",
            "contact": {
                "phone": "+971-4-333-3333",
                "email": "play@oasis.example",
                "address": "JBR, Dubai, UAE",
            },
        },
    },
    {
        "slug": "desert-tours",
        "name": "Desert Tours",
        "tier": "starter",
        "config": {
            "type": "travel_agency",
            "tagline": "Adventure in the dunes",
            "branding": {
                "primary_color": "#D97706",
                "secondary_color": "#92400E",
                "accent_color": "#FEF3C7",
                "font_heading": "Merriweather",
                "font_body": "Inter",
                "logo_url": "/static/logos/desert.svg",
            },
            "languages": ["en", "ar", "fil"],
            "default_language": "en",
            "currency": "AED",
            "contact": {
                "phone": "+971-4-444-4444",
                "email": "go@desert.example",
                "address": "Al Quoz, Dubai, UAE",
            },
        },
    },
]


def seed(db: Session) -> tuple[int, int]:
    """Insert demo tenants. Returns (created, skipped)."""
    created = 0
    skipped = 0
    for data in DEMO_TENANTS:
        exists = db.execute(
            select(Tenant).where(Tenant.slug == data["slug"])
        ).scalar_one_or_none()
        if exists:
            skipped += 1
            continue
        db.add(Tenant(**data, status="active"))
        created += 1
    db.commit()
    return created, skipped


def main() -> None:
    with SessionLocal() as db:
        created, skipped = seed(db)
    print(f"Seed complete: created={created}, skipped={skipped}")


if __name__ == "__main__":
    main()
