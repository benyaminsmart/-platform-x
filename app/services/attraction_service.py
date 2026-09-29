"""Attraction service — list + nearby (Haversine) + CRUD."""

from __future__ import annotations

import math

from sqlalchemy.orm import Session as DBSession

from app.models.attraction import Attraction


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def list_all(db: DBSession) -> list[Attraction]:
    return db.query(Attraction).order_by(Attraction.name).all()


def get(db: DBSession, attraction_id: str) -> Attraction | None:
    return db.query(Attraction).filter(Attraction.id == attraction_id).one_or_none()


def nearby(
    db: DBSession,
    *,
    lat: float,
    lng: float,
    radius_km: float = 10.0,
    limit: int = 20,
) -> list[dict]:
    rows = db.query(Attraction).all()
    out: list[dict] = []
    for a in rows:
        d = _haversine_km(float(lat), float(lng), float(a.lat), float(a.lng))
        if d <= float(radius_km):
            out.append({
                "id": a.id,
                "name": a.name,
                "category": a.category,
                "description": a.description,
                "lat": a.lat,
                "lng": a.lng,
                "city": a.city,
                "cover_image": a.cover_image,
                "distance_km": round(d, 2),
            })
    out.sort(key=lambda x: x["distance_km"])
    return out[: max(1, min(int(limit), 100))]
