"""AI Location Recommender — suggest nearby places with reasoning.

Design:
- Deterministic layer: nearby attractions + nearby services (via Haversine).
- AI layer: write a short recommendation grounded in the deterministic list.
- If user_id provided: use their bookings to infer preference (top category).
- Fallback text if AI fails.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.tenant import Tenant
from app.services import attraction_service, search_service
from app.services.ai import service as ai_service


SUPPORTED_LANGUAGES = {"en", "ar", "fil", "hi"}
_LANGUAGE_NAMES = {
    "en": "English", "ar": "Arabic (Modern Standard Arabic)",
    "fil": "Filipino (Tagalog)", "hi": "Hindi",
}


def _user_pref_category(db: DBSession, user_id: str) -> str | None:
    """Infer user's preferred category from their past bookings."""
    rows = (
        db.query(Booking.booking_type, Booking.tenant_id)
        .filter(Booking.user_id == user_id)
        .all()
    )
    if not rows:
        return None
    counts: dict[str, int] = {}
    for _bt, tid in rows:
        t = db.query(Tenant).filter(Tenant.id == tid).one_or_none()
        if t is None:
            continue
        cfg = t.config or {}
        typ = (cfg.get("type") or "").lower()
        cat_map = {"hotel": "hotels", "restaurant": "restaurants",
                   "travel_agency": "travel", "entertainment": "entertainment"}
        cat = cat_map.get(typ)
        if cat:
            counts[cat] = counts.get(cat, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _safe_ai(prompt: str) -> str | None:
    try:
        result = ai_service.chat(prompt, history=[])
        return (result or {}).get("content", "").strip() or None
    except Exception:
        return None


def _fallback_advice(attractions: list[dict], services: list[dict], pref: str | None) -> str:
    parts: list[str] = []
    if attractions:
        parts.append("Nearby attractions: " + ", ".join(a["name"] for a in attractions[:3]) + ".")
    if services:
        parts.append("Nearby businesses: " + ", ".join(s["tenant_name"] for s in services[:3]) + ".")
    if pref:
        parts.append(f"Based on your history, we suggest more {pref}.")
    if not parts:
        return "No nearby options found within the chosen radius."
    return " ".join(parts)


def recommend(
    db: DBSession,
    *,
    lat: float,
    lng: float,
    radius_km: float = 10.0,
    category: str | None = None,
    user_id: str | None = None,
    language: str = "en",
) -> dict[str, Any]:
    """Return deterministic lists + AI advice string."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")

    pref = _user_pref_category(db, user_id) if user_id else None
    eff_category = category or pref

    attractions = attraction_service.nearby(db, lat=lat, lng=lng, radius_km=radius_km, limit=6)
    services_result = search_service.search_services(
        db, lat=lat, lng=lng, radius_km=radius_km,
        category=eff_category, sort="rating", page=1, page_size=6,
    )
    services = services_result.get("items", [])

    if not attractions and not services:
        return {
            "attractions": [],
            "services": [],
            "advice": _fallback_advice([], [], pref),
            "provider": "fallback",
        }

    lines: list[str] = ["LOCATION:", f"  lat={lat}, lng={lng}, radius_km={radius_km}"]
    if pref:
        lines.append(f"USER_PREFERRED_CATEGORY: {pref}")
    if eff_category:
        lines.append(f"EFFECTIVE_CATEGORY: {eff_category}")

    lines.append("")
    lines.append("ATTRACTIONS_NEARBY:")
    for a in attractions:
        lines.append(f"  - {a['name']} ({a['category']}, {a['distance_km']} km)")

    lines.append("")
    lines.append("SERVICES_NEARBY:")
    for s in services:
        lines.append(
            f"  - {s['service_name']} at {s['tenant_name']} "
            f"({s['category']}, {s.get('distance_km')} km, {s['price']} {s['currency']})"
        )

    lang = _LANGUAGE_NAMES.get(language, "English")
    prompt = (
        "You are a local travel advisor for Platform-X. Based on the "
        "attractions and services listed below, write a short, personal "
        "recommendation (max 4 short paragraphs) in " + lang + ".\n\n"
        "RULES:\n"
        "- Only mention places already listed; do not invent.\n"
        "- If a preferred category is given, prioritize it.\n"
        "- Be concrete: mention 2-3 specific names from the lists.\n"
        "- Do not add discounts or prices not present.\n\n"
        + "\n".join(lines)
    )
    advice = _safe_ai(prompt)
    provider = "ai"
    if not advice:
        advice = _fallback_advice(attractions, services, pref)
        provider = "fallback"

    return {
        "attractions": attractions,
        "services": services,
        "advice": advice,
        "provider": provider,
    }
