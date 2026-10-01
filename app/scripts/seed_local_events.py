"""Seed mock local events (Phase 65, Step 1)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.models.local_event import LocalEvent


def _seed(db) -> int:
    existing = db.query(LocalEvent).count()
    if existing > 0:
        return 0

    now = datetime.now(timezone.utc)
    rows = [
        # Dubai events
        {"name": "Dubai Shopping Festival", "category": "festival",
         "city": "Dubai", "venue": "Downtown Dubai",
         "lat": 25.1972, "lng": 55.2744,
         "start_at": now + timedelta(days=2),
         "end_at": now + timedelta(days=30),
         "description": "Annual shopping and entertainment festival with fireworks and concerts.",
         "ticket_url": None},
        {"name": "Desert Safari Live", "category": "adventure",
         "city": "Dubai", "venue": "Al Marmoom Desert",
         "lat": 24.8472, "lng": 55.3804,
         "start_at": now + timedelta(days=1),
         "end_at": now + timedelta(days=90),
         "description": "Daily desert safari with dune bashing and BBQ dinner.",
         "ticket_url": None},
        {"name": "Global Village Season", "category": "market",
         "city": "Dubai", "venue": "Global Village",
         "lat": 25.0715, "lng": 55.3072,
         "start_at": now + timedelta(days=5),
         "end_at": now + timedelta(days=120),
         "description": "Multi-cultural pavilion market with shows and food.",
         "ticket_url": None},
        {"name": "Dubai Opera: La Bohème", "category": "concert",
         "city": "Dubai", "venue": "Dubai Opera",
         "lat": 25.1923, "lng": 55.2757,
         "start_at": now + timedelta(days=7),
         "end_at": now + timedelta(days=8),
         "description": "Opera performance in the heart of Downtown.",
         "ticket_url": None},
        # Abu Dhabi events
        {"name": "Abu Dhabi Grand Prix", "category": "sports",
         "city": "Abu Dhabi", "venue": "Yas Marina Circuit",
         "lat": 24.4672, "lng": 54.6031,
         "start_at": now + timedelta(days=21),
         "end_at": now + timedelta(days=23),
         "description": "Formula 1 finale weekend at Yas Marina.",
         "ticket_url": None},
        {"name": "Louvre Abu Dhabi Night Tours", "category": "museum",
         "city": "Abu Dhabi", "venue": "Louvre Abu Dhabi",
         "lat": 24.5334, "lng": 54.3984,
         "start_at": now + timedelta(days=3),
         "end_at": now + timedelta(days=180),
         "description": "Evening guided tours of the museum's collection.",
         "ticket_url": None},
    ]

    for r in rows:
        db.add(LocalEvent(**r))
    db.commit()
    return len(rows)


def main() -> None:
    db = SessionLocal()
    try:
        inserted = _seed(db)
        if inserted == 0:
            print("local_events already seeded — skipping")
        else:
            print(f"Seeded {inserted} local events")
    finally:
        db.close()


if __name__ == "__main__":
    main()
