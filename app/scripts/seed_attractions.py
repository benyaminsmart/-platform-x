"""Seed demo attractions (Dubai area).

Run: python -m app.scripts.seed_attractions
Idempotent: skips if an attraction with the same name exists.
"""

from app.db.session import SessionLocal
from app.models.attraction import Attraction


DEMO = [
    ("Burj Khalifa", "landmark", 25.1972, 55.2744, "Dubai",
     "World's tallest building with observation decks.", None),
    ("Dubai Mall", "mall", 25.1985, 55.2796, "Dubai",
     "One of the world's largest shopping malls.", None),
    ("Dubai Marina Walk", "promenade", 25.0805, 55.1400, "Dubai",
     "Waterfront promenade with cafes and yachts.", None),
    ("Palm Jumeirah", "landmark", 25.1124, 55.1390, "Dubai",
     "Iconic man-made island shaped like a palm.", None),
    ("JBR Beach", "beach", 25.0785, 55.1332, "Dubai",
     "Popular public beach with nightlife.", None),
    ("Al Fahidi Historical District", "museum", 25.2637, 55.2972, "Dubai",
     "Traditional wind-tower architecture.", None),
    ("Dubai Creek", "landmark", 25.2697, 55.3095, "Dubai",
     "Historic waterway with abra rides.", None),
    ("Global Village", "park", 25.0689, 55.3044, "Dubai",
     "Seasonal cultural and entertainment park.", None),
    ("Miracle Garden", "park", 25.0586, 55.2445, "Dubai",
     "World's largest natural flower garden.", None),
    ("Museum of the Future", "museum", 25.2201, 55.2823, "Dubai",
     "Iconic torus-shaped museum of innovation.", None),
    ("Gold Souk", "market", 25.2697, 55.2967, "Dubai",
     "Traditional gold market in Deira.", None),
    ("Ski Dubai", "activity", 25.0983, 55.1494, "Dubai",
     "Indoor ski slope inside Mall of the Emirates.", None),
]


def seed():
    created = 0
    with SessionLocal() as db:
        for name, cat, lat, lng, city, desc, img in DEMO:
            existing = db.query(Attraction).filter(Attraction.name == name).one_or_none()
            if existing:
                continue
            db.add(Attraction(
                name=name, category=cat, lat=lat, lng=lng,
                city=city, description=desc, cover_image=img,
            ))
            created += 1
        db.commit()
    print(f"seeded attractions: {created}")


if __name__ == "__main__":
    seed()
