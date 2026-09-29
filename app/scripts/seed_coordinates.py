"""Seed lat/lng into tenants.config.coordinates.

Usage:
    python -m app.scripts.seed_coordinates

Idempotent: only sets coordinates if missing.
Uses a small built-in map of Dubai-area locations → approximate lat/lng.
"""

from app.db.session import SessionLocal
from app.models.tenant import Tenant


# Approximate coordinates by keyword found in location string
COORD_MAP = [
    # Downtown Dubai
    ("downtown", 25.1972, 55.2744),
    # Marina
    ("marina", 25.0805, 55.1400),
    # Palm Jumeirah
    ("palm", 25.1124, 55.1390),
    # Alserkal / Al Quoz
    ("alserkal", 25.1420, 55.2236),
    ("al quoz", 25.1420, 55.2236),
    # Al Fahidi / Bur Dubai
    ("al fahidi", 25.2637, 55.2972),
    ("bur dubai", 25.2582, 55.2968),
    # JBR / Jumeirah Beach
    ("jbr", 25.0785, 55.1332),
    ("jumeirah", 25.2048, 55.2400),
    # Abu Dhabi
    ("abu dhabi", 24.4539, 54.3773),
    # Sharjah
    ("sharjah", 25.3463, 55.4209),
    # Business Bay
    ("business bay", 25.1857, 55.2761),
    # Deira
    ("deira", 25.2697, 55.3095),
    # Default: Dubai center
    ("uae", 25.2048, 55.2708),
]


def _coord_for(location: str | None) -> tuple[float, float]:
    loc = (location or "").lower()
    for key, lat, lng in COORD_MAP:
        if key in loc:
            return lat, lng
    # Fallback: Dubai center
    return 25.2048, 55.2708


def seed():
    created = 0
    skipped = 0
    with SessionLocal() as db:
        for t in db.query(Tenant).all():
            cfg = dict(t.config or {})
            if "coordinates" in cfg and cfg["coordinates"]:
                skipped += 1
                continue
            lat, lng = _coord_for(cfg.get("location"))
            cfg["coordinates"] = {"lat": lat, "lng": lng}
            t.config = cfg
            created += 1
        db.commit()
    print(f"seeded: {created}, skipped (already had coords): {skipped}")


if __name__ == "__main__":
    seed()
