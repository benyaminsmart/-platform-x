"""Local Experiences service — nearby events + AI recommendation.

Phase 65, Step 1.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.local_event import LocalEvent
from app.services.ai import service as ai_service


SUPPORTED_LANGUAGES = {"en", "ar", "fil", "hi"}
_LANGUAGE_NAMES = {
    "en": "English", "ar": "Arabic (Modern Standard Arabic)",
    "fil": "Filipino (Tagalog)", "hi": "Hindi",
}


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _fmt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    d = _as_utc(dt)
    return d.isoformat() if d else None


def _ser(e: LocalEvent, *, distance_km: float | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": e.id,
        "name": e.name,
        "category": e.category,
        "description": e.description,
        "city": e.city,
        "venue": e.venue,
        "lat": e.lat,
        "lng": e.lng,
        "start_at": _fmt(e.start_at),
        "end_at": _fmt(e.end_at),
        "cover_image": e.cover_image,
        "ticket_url": e.ticket_url,
    }
    if distance_km is not None:
        out["distance_km"] = distance_km
    return out


def list_events(
    db: DBSession,
    *,
    city: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    q = db.query(LocalEvent)
    if city:
        q = q.filter(LocalEvent.city == city)
    if date_from is not None:
        q = q.filter(LocalEvent.start_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to is not None:
        end = datetime.combine(date_to, datetime.max.time())
        q = q.filter(LocalEvent.start_at <= end)
    q = q.order_by(LocalEvent.start_at.asc()).limit(max(1, min(int(limit), 200)))
    return [_ser(e) for e in q.all()]


def nearby(
    db: DBSession,
    *,
    lat: float,
    lng: float,
    radius_km: float = 15.0,
    on_date: date | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    rows = db.query(LocalEvent).all()
    if on_date is not None:
        day_start = datetime.combine(on_date, datetime.min.time(), tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        filtered = []
        for e in rows:
            start = _as_utc(e.start_at)
            end = _as_utc(e.end_at) or start
            if start is None:
                continue
            if start < day_end and end >= day_start:
                filtered.append(e)
        rows = filtered

    out: list[dict[str, Any]] = []
    for e in rows:
        d = _haversine_km(float(lat), float(lng), float(e.lat), float(e.lng))
        if d <= float(radius_km):
            out.append(_ser(e, distance_km=round(d, 2)))
    out.sort(key=lambda x: x["distance_km"])
    return out[: max(1, min(int(limit), 100))]


def _fallback_summary(
    events: list[dict[str, Any]], *, city: str | None, on_date: date | None
) -> str:
    if not events:
        return "No local events found for this window."
    parts: list[str] = []
    if city:
        parts.append(f"In {city}")
    if on_date:
        parts.append(f"on {on_date.isoformat()}")
    prefix = " ".join(parts) + ":" if parts else "Nearby:"
    names = ", ".join(e["name"] for e in events[:3])
    return f"{prefix} {names}."


def recommend(
    db: DBSession,
    *,
    lat: float,
    lng: float,
    radius_km: float = 15.0,
    on_date: date | None = None,
    language: str = "en",
) -> dict[str, Any]:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")

    events = nearby(db, lat=lat, lng=lng, radius_km=radius_km, on_date=on_date, limit=6)
    city = events[0]["city"] if events and events[0].get("city") else None

    if not events:
        return {
            "events": [],
            "advice": _fallback_summary([], city=city, on_date=on_date),
            "provider": "fallback",
        }

    lines = [
        f"LOCATION: lat={lat}, lng={lng}, radius_km={radius_km}",
        f"ON_DATE: {on_date.isoformat() if on_date else 'any'}",
        "",
        "EVENTS_NEARBY:",
    ]
    for e in events:
        lines.append(
            f"  - {e['name']} ({e['category']}, {e.get('distance_km')} km) "
            f"at {e.get('venue') or e.get('city') or 'venue TBD'}"
        )

    lang = _LANGUAGE_NAMES.get(language, "English")
    prompt = (
        "You are a local experiences curator for Platform-X. Based ONLY on "
        "the events listed below, write a short, warm recommendation (max 3 "
        "short paragraphs) that picks 1-2 events and says why they're worth "
        "attending. Do NOT invent venues, prices, or dates. Write in "
        + lang + ".\n\n" + "\n".join(lines)
    )

    advice = None
    provider = "fallback"
    try:
        result = ai_service.chat(prompt, history=[])
        advice = (result or {}).get("content", "").strip() or None
        if advice:
            provider = "ai"
    except Exception:
        advice = None

    if not advice:
        advice = _fallback_summary(events, city=city, on_date=on_date)
        provider = "fallback"

    return {"events": events, "advice": advice, "provider": provider}
