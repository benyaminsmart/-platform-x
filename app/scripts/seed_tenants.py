"""Seed demo tenants with rich, image-backed data.

Idempotent — existing tenants are updated with new config if missing keys.

Run: python -m app.scripts.seed_tenants
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.tenant import Tenant


# Free image URLs from Unsplash (hotlink-friendly, e.g. source.unsplash.com or images.unsplash.com)
IMG = "https://images.unsplash.com/photo-{id}?w=1200&q=80&auto=format&fit=crop"


DEMO_TENANTS = [
    # ---------------- HOTELS ----------------
    {
        "slug": "trianon-hotel",
        "name": "Trianon Royal Hotel",
        "tier": "professional",
        "config": {
            "type": "hotel",
            "tagline": "Luxury stay in the heart of the city",
            "location": "Downtown Dubai, UAE",
            "rating": 4.8,
            "reviews_count": 342,
            "price_from": 350,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=1200&q=80&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=1200&q=80&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1582719508461-905c673771fd?w=1200&q=80&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Pool", "Spa", "Free WiFi", "Restaurant", "Gym", "Airport shuttle"],
            "branding": {
                "primary_color": "#1B3A5C",
                "secondary_color": "#C9A961",
                "accent_color": "#F5F1EA",
            },
            "languages": ["en", "ar", "fil", "hi"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-000-0000",
                "email": "info@trianon.example",
                "address": "Downtown, Dubai, UAE",
            },
        },
    },
    {
        "slug": "azure-palm-resort",
        "name": "Azure Palm Resort",
        "tier": "professional",
        "config": {
            "type": "hotel",
            "tagline": "Beachfront escape with private pools",
            "location": "Palm Jumeirah, Dubai",
            "rating": 4.9,
            "reviews_count": 528,
            "price_from": 780,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=1200&q=80&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1540541338287-41700207dee6?w=1200&q=80&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Private Beach", "Spa", "5 Restaurants", "Kids Club", "Tennis", "Free WiFi"],
            "branding": {
                "primary_color": "#0E7490",
                "secondary_color": "#67E8F9",
                "accent_color": "#ECFEFF",
            },
            "languages": ["en", "ar", "fil", "hi"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-111-1111",
                "email": "stay@azurepalm.example",
                "address": "Palm Jumeirah, Dubai, UAE",
            },
        },
    },
    {
        "slug": "aurora-boutique",
        "name": "Aurora Boutique Hotel",
        "tier": "professional",
        "config": {
            "type": "hotel",
            "tagline": "Design-led rooms in the arts district",
            "location": "Alserkal Avenue, Dubai",
            "rating": 4.7,
            "reviews_count": 189,
            "price_from": 420,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1445019980597-93fa8acb246c?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1611048268330-53de574cae3b?w=1200&q=80&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Rooftop Bar", "Art Gallery", "Free WiFi", "Bike Rental"],
            "branding": {
                "primary_color": "#7C3AED",
                "secondary_color": "#A78BFA",
                "accent_color": "#F5F3FF",
            },
            "languages": ["en", "ar"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-222-2222",
                "email": "hello@aurora.example",
                "address": "Alserkal Avenue, Dubai",
            },
        },
    },
    {
        "slug": "marina-skylines",
        "name": "Marina Skylines Hotel",
        "tier": "professional",
        "config": {
            "type": "hotel",
            "tagline": "Sky-high suites with panoramic views",
            "location": "Dubai Marina, UAE",
            "rating": 4.6,
            "reviews_count": 412,
            "price_from": 620,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=1200&q=80&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1540518614846-7eded433c457?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Infinity Pool", "Sky Bar", "Free WiFi", "Gym", "Business Center"],
            "branding": {
                "primary_color": "#0F172A",
                "secondary_color": "#64748B",
                "accent_color": "#F1F5F9",
            },
            "languages": ["en", "ar", "fil"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-333-3333",
                "email": "book@marinaskylines.example",
                "address": "Dubai Marina, UAE",
            },
        },
    },
    {
        "slug": "desert-rose-hotel",
        "name": "Desert Rose Hotel",
        "tier": "starter",
        "config": {
            "type": "hotel",
            "tagline": "Traditional Arabian hospitality",
            "location": "Al Fahidi, Dubai",
            "rating": 4.5,
            "reviews_count": 156,
            "price_from": 280,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1582719508461-905c673771fd?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1541971875076-8f970d573be6?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Courtyard", "Traditional Breakfast", "Free WiFi"],
            "branding": {
                "primary_color": "#B45309",
                "secondary_color": "#F59E0B",
                "accent_color": "#FEF3C7",
            },
            "languages": ["en", "ar"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-444-4444",
                "email": "salam@desertrose.example",
                "address": "Al Fahidi, Dubai",
            },
        },
    },

    # ---------------- RESTAURANTS ----------------
    {
        "slug": "saffron-restaurant",
        "name": "Saffron Restaurant",
        "tier": "professional",
        "config": {
            "type": "restaurant",
            "tagline": "Modern Middle Eastern cuisine",
            "location": "Marina Walk, Dubai",
            "rating": 4.8,
            "reviews_count": 623,
            "price_from": 35,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1544025162-d76694265947?w=1200&q=80&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Outdoor seating", "Vegetarian options", "Reservations", "Delivery"],
            "branding": {
                "primary_color": "#7A1E1E",
                "secondary_color": "#E8B44C",
                "accent_color": "#FFF8EC",
            },
            "languages": ["en", "ar"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-111-1111",
                "email": "hello@saffron.example",
                "address": "Marina Walk, Dubai",
            },
        },
    },
    {
        "slug": "olive-grove",
        "name": "Olive Grove",
        "tier": "professional",
        "config": {
            "type": "restaurant",
            "tagline": "Mediterranean classics, fresh daily",
            "location": "JBR, Dubai",
            "rating": 4.7,
            "reviews_count": 445,
            "price_from": 45,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1552566626-52f8b828add9?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Sea view", "Wine list", "Vegan options", "Reservations"],
            "branding": {
                "primary_color": "#166534",
                "secondary_color": "#84CC16",
                "accent_color": "#F7FEE7",
            },
            "languages": ["en", "ar", "fil"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-222-2222",
                "email": "eat@olivegrove.example",
                "address": "JBR, Dubai",
            },
        },
    },
    {
        "slug": "sakura-sushi",
        "name": "Sakura Sushi",
        "tier": "professional",
        "config": {
            "type": "restaurant",
            "tagline": "Authentic Japanese omakase",
            "location": "DIFC, Dubai",
            "rating": 4.9,
            "reviews_count": 312,
            "price_from": 120,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1579027989536-b7b1f875659b?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1553621042-f6e147245754?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Omakase counter", "Sake selection", "Reservations only"],
            "branding": {
                "primary_color": "#9F1239",
                "secondary_color": "#FB7185",
                "accent_color": "#FFF1F2",
            },
            "languages": ["en", "ar"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-333-3333",
                "email": "reserve@sakura.example",
                "address": "DIFC, Dubai",
            },
        },
    },
    {
        "slug": "the-copper-kitchen",
        "name": "The Copper Kitchen",
        "tier": "professional",
        "config": {
            "type": "restaurant",
            "tagline": "Farm-to-table modern European",
            "location": "City Walk, Dubai",
            "rating": 4.6,
            "reviews_count": 287,
            "price_from": 90,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Tasting menu", "Sommelier", "Reservations"],
            "branding": {
                "primary_color": "#7C2D12",
                "secondary_color": "#F97316",
                "accent_color": "#FFF7ED",
            },
            "languages": ["en", "ar"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-555-5555",
                "email": "table@copperkitchen.example",
                "address": "City Walk, Dubai",
            },
        },
    },
    {
        "slug": "spice-route-indian",
        "name": "Spice Route Indian",
        "tier": "starter",
        "config": {
            "type": "restaurant",
            "tagline": "Regional Indian flavours, slow-cooked",
            "location": "Karama, Dubai",
            "rating": 4.5,
            "reviews_count": 512,
            "price_from": 30,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Vegetarian menu", "Delivery", "Family style"],
            "branding": {
                "primary_color": "#92400E",
                "secondary_color": "#FBBF24",
                "accent_color": "#FEF3C7",
            },
            "languages": ["en", "ar", "hi"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-666-6666",
                "email": "hello@spiceroute.example",
                "address": "Karama, Dubai",
            },
        },
    },

    # ---------------- TRAVEL AGENCIES ----------------
    {
        "slug": "skyways-travel",
        "name": "Skyways Travel",
        "tier": "professional",
        "config": {
            "type": "travel_agency",
            "tagline": "Your journey, our expertise",
            "location": "Business Bay, Dubai",
            "rating": 4.7,
            "reviews_count": 234,
            "price_from": 1200,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Flight booking", "Visa assistance", "Travel insurance", "24/7 support"],
            "branding": {
                "primary_color": "#0A4D8C",
                "secondary_color": "#00B4D8",
                "accent_color": "#F0F8FF",
            },
            "languages": ["en", "ar", "fil", "hi"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-222-2222",
                "email": "book@skyways.example",
                "address": "Business Bay, Dubai",
            },
        },
    },
    {
        "slug": "horizon-voyages",
        "name": "Horizon Voyages",
        "tier": "professional",
        "config": {
            "type": "travel_agency",
            "tagline": "Luxury and bespoke itineraries",
            "location": "Downtown Dubai",
            "rating": 4.9,
            "reviews_count": 178,
            "price_from": 3500,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1503220317375-aaad61436b1b?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Private jet", "Concierge", "Custom itineraries", "VIP support"],
            "branding": {
                "primary_color": "#1E3A8A",
                "secondary_color": "#60A5FA",
                "accent_color": "#EFF6FF",
            },
            "languages": ["en", "ar"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-777-7777",
                "email": "concierge@horizonvoyages.example",
                "address": "Downtown, Dubai",
            },
        },
    },
    {
        "slug": "caravan-tours",
        "name": "Caravan Tours",
        "tier": "starter",
        "config": {
            "type": "travel_agency",
            "tagline": "Desert adventures and cultural journeys",
            "location": "Al Quoz, Dubai",
            "rating": 4.6,
            "reviews_count": 289,
            "price_from": 350,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1451337516015-6b6e9a44a8a3?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1519677100203-a0e668c92439?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Desert safari", "Camel rides", "Overnight camps", "BBQ dinners"],
            "branding": {
                "primary_color": "#D97706",
                "secondary_color": "#92400E",
                "accent_color": "#FEF3C7",
            },
            "languages": ["en", "ar", "fil"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-888-8888",
                "email": "go@caravantours.example",
                "address": "Al Quoz, Dubai",
            },
        },
    },
    {
        "slug": "euro-explorer",
        "name": "Euro Explorer",
        "tier": "professional",
        "config": {
            "type": "travel_agency",
            "tagline": "European city breaks and rail tours",
            "location": "JLT, Dubai",
            "rating": 4.7,
            "reviews_count": 198,
            "price_from": 5800,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1499856871958-5b9627545d1a?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Rail passes", "Small groups", "Local guides", "Hotels included"],
            "branding": {
                "primary_color": "#1E40AF",
                "secondary_color": "#3B82F6",
                "accent_color": "#EFF6FF",
            },
            "languages": ["en", "ar", "fil"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-999-9999",
                "email": "tour@euroexplorer.example",
                "address": "JLT, Dubai",
            },
        },
    },
    {
        "slug": "blue-ocean-cruises",
        "name": "Blue Ocean Cruises",
        "tier": "starter",
        "config": {
            "type": "travel_agency",
            "tagline": "Luxury cruises across the Gulf",
            "location": "Dubai Marina",
            "rating": 4.5,
            "reviews_count": 143,
            "price_from": 1500,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1548574505-5e239809ee19?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1559599238-308793637427?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["All-inclusive", "Spa onboard", "Entertainment", "Shore excursions"],
            "branding": {
                "primary_color": "#0369A1",
                "secondary_color": "#38BDF8",
                "accent_color": "#F0F9FF",
            },
            "languages": ["en", "ar"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-101-1010",
                "email": "sail@blueocean.example",
                "address": "Dubai Marina, UAE",
            },
        },
    },

    # ---------------- ENTERTAINMENT ----------------
    {
        "slug": "oasis-entertainment",
        "name": "Oasis Entertainment Park",
        "tier": "professional",
        "config": {
            "type": "entertainment",
            "tagline": "Fun for the whole family",
            "location": "JBR, Dubai",
            "rating": 4.6,
            "reviews_count": 876,
            "price_from": 80,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1513889961551-628c1e5e2ee9?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1560269507-d1f0a1f5b8c6?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Aquarium", "VR Zone", "Kids Play", "Bowling", "Food court"],
            "branding": {
                "primary_color": "#2E7D32",
                "secondary_color": "#FFB300",
                "accent_color": "#F1F8E9",
            },
            "languages": ["en", "ar"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-333-3333",
                "email": "play@oasis.example",
                "address": "JBR, Dubai, UAE",
            },
        },
    },
    {
        "slug": "skypark-adventures",
        "name": "SkyPark Adventures",
        "tier": "professional",
        "config": {
            "type": "entertainment",
            "tagline": "Ziplines, rope courses and more",
            "location": "Dubai Marina",
            "rating": 4.8,
            "reviews_count": 412,
            "price_from": 150,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1520045653281-86dbc0c7e4c4?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1533130061792-64b345e4a833?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Zipline", "Rope course", "Climbing wall", "Kids zone"],
            "branding": {
                "primary_color": "#047857",
                "secondary_color": "#34D399",
                "accent_color": "#ECFDF5",
            },
            "languages": ["en", "ar", "fil"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-666-6666",
                "email": "fly@skypark.example",
                "address": "Dubai Marina, UAE",
            },
        },
    },
    {
        "slug": "aqua-world",
        "name": "Aqua World Waterpark",
        "tier": "professional",
        "config": {
            "type": "entertainment",
            "tagline": "The biggest waterpark in the region",
            "location": "Jumeirah, Dubai",
            "rating": 4.7,
            "reviews_count": 1560,
            "price_from": 220,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1530549387789-4c1017266635?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1597466765990-64ad1c35dafc?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["40+ slides", "Wave pool", "Kids area", "Cabanas", "Restaurants"],
            "branding": {
                "primary_color": "#0EA5E9",
                "secondary_color": "#FDE047",
                "accent_color": "#F0F9FF",
            },
            "languages": ["en", "ar", "fil", "hi"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-707-7070",
                "email": "splash@aquaworld.example",
                "address": "Jumeirah, Dubai",
            },
        },
    },
    {
        "slug": "virtual-realm",
        "name": "Virtual Realm VR Park",
        "tier": "starter",
        "config": {
            "type": "entertainment",
            "tagline": "Immersive VR experiences for all ages",
            "location": "Mall of the Emirates",
            "rating": 4.5,
            "reviews_count": 234,
            "price_from": 90,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1622979135225-d2ba269cf1ac?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1592478411213-6153e4ebc07d?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["VR games", "Escape rooms", "Racing simulators", "Group bookings"],
            "branding": {
                "primary_color": "#6D28D9",
                "secondary_color": "#A78BFA",
                "accent_color": "#F5F3FF",
            },
            "languages": ["en", "ar"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-808-8080",
                "email": "play@virtualrealm.example",
                "address": "Mall of the Emirates, Dubai",
            },
        },
    },
    {
        "slug": "cinema-royale",
        "name": "Cinema Royale",
        "tier": "starter",
        "config": {
            "type": "entertainment",
            "tagline": "Premium cinema with fine dining",
            "location": "Dubai Mall",
            "rating": 4.6,
            "reviews_count": 512,
            "price_from": 65,
            "currency": "AED",
            "cover_image": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=1600&q=80&auto=format&fit=crop",
            "gallery": [
                "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=1200&q=80&auto=format&fit=crop",
            ],
            "amenities": ["Recliner seats", "Full menu", "Dolby Atmos", "VIP rooms"],
            "branding": {
                "primary_color": "#111827",
                "secondary_color": "#F59E0B",
                "accent_color": "#FEF3C7",
            },
            "languages": ["en", "ar"],
            "default_language": "en",
            "contact": {
                "phone": "+971-4-909-9090",
                "email": "watch@cinemaroyale.example",
                "address": "Dubai Mall, UAE",
            },
        },
    },
]


def seed(db: Session) -> tuple[int, int]:
    """Insert or update demo tenants. Returns (created, updated)."""
    created = 0
    updated = 0
    for data in DEMO_TENANTS:
        existing = db.execute(
            select(Tenant).where(Tenant.slug == data["slug"])
        ).scalar_one_or_none()
        if existing:
            # Update config, keep id
            existing.name = data["name"]
            existing.tier = data["tier"]
            existing.config = data["config"]
            existing.status = "active"
            updated += 1
            continue
        db.add(Tenant(**data, status="active"))
        created += 1
    db.commit()
    return created, updated


def main() -> None:
    with SessionLocal() as db:
        created, updated = seed(db)
    print(f"Seed tenants complete: created={created}, updated={updated}")


if __name__ == "__main__":
    main()
