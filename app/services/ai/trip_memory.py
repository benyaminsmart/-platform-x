"""AI Trip Memory — personalized travel profile from past bookings.

Design:
- Deterministic layer: analyze user's bookings -> structured profile
  (favorite category, cities, price band, group size, preferred months).
- AI layer: write a short personalized recap + suggestion grounded
  in that profile.
- Fallback text if AI fails.
- No cross-user data leaks (only aggregates the target user's bookings).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.tenant import Tenant
from app.services.ai import service as ai_service


SUPPORTED_LANGUAGES = {"en", "ar", "fil", "hi"}
_LANGUAGE_NAMES = {
    "en": "English", "ar": "Arabic (Modern Standard Arabic)",
    "fil": "Filipino (Tagalog)", "hi": "Hindi",
}

_MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

_TYPE_TO_CATEGORY = {
    "hotel": "hotels", "restaurant": "restaurants",
    "travel_agency": "travel", "entertainment": "entertainment",
}

# Exclude bookings in these statuses from "memory"
_EXCLUDED_STATUSES = {"cancelled"}


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"))


def build_profile(db: DBSession, user_id: str) -> dict[str, Any]:
    """Aggregate a user's bookings into a structured travel profile."""
    bookings = (
        db.query(Booking)
        .filter(Booking.user_id == user_id)
        .filter(~Booking.status.in_(_EXCLUDED_STATUSES))
        .order_by(Booking.check_in.desc())
        .all()
    )
    total = len(bookings)
    if total == 0:
        return {
            "total_bookings": 0,
            "favorite_category": None,
            "cities": [],
            "avg_price": None,
            "price_band": None,
            "currency": None,
            "avg_guests": None,
            "preferred_months": [],
            "top_tenants": [],
        }

    # Category counts (via tenant type)
    tid_cache: dict[str, Tenant] = {}
    cat_counts: dict[str, int] = {}
    city_counts: dict[str, int] = {}
    tenant_counts: dict[str, int] = {}
    tenant_names: dict[str, str] = {}
    prices: list[Decimal] = []
    guests: list[int] = []
    month_counts: dict[int, int] = {}
    currency_counts: dict[str, int] = {}

    for b in bookings:
        if b.tenant_id not in tid_cache:
            t = db.query(Tenant).filter(Tenant.id == b.tenant_id).one_or_none()
            if t is not None:
                tid_cache[b.tenant_id] = t
        t = tid_cache.get(b.tenant_id)
        if t is not None:
            cfg = t.config or {}
            typ = (cfg.get("type") or "").lower()
            cat = _TYPE_TO_CATEGORY.get(typ)
            if cat:
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
            loc = cfg.get("location")
            if isinstance(loc, str) and loc.strip():
                city_counts[loc.strip()] = city_counts.get(loc.strip(), 0) + 1
            tenant_counts[b.tenant_id] = tenant_counts.get(b.tenant_id, 0) + 1
            tenant_names[b.tenant_id] = t.name

        if b.total_amount is not None:
            prices.append(Decimal(str(b.total_amount)))
        if b.guests:
            guests.append(int(b.guests))
        if b.check_in:
            month_counts[b.check_in.month] = month_counts.get(b.check_in.month, 0) + 1
        if b.currency:
            currency_counts[b.currency] = currency_counts.get(b.currency, 0) + 1

    favorite_category = (
        max(cat_counts.items(), key=lambda kv: kv[1])[0] if cat_counts else None
    )
    cities = [c for c, _ in sorted(city_counts.items(),
                                    key=lambda kv: kv[1], reverse=True)][:3]
    avg_price = (
        _round2(sum(prices) / Decimal(len(prices))) if prices else None
    )
    price_band = None
    if avg_price is not None:
        lo = _round2(avg_price * Decimal("0.7"))
        hi = _round2(avg_price * Decimal("1.3"))
        price_band = [str(lo), str(hi)]

    avg_guests = (
        round(sum(guests) / len(guests), 1) if guests else None
    )
    preferred_months = [
        _MONTH_NAMES[m - 1]
        for m, _ in sorted(month_counts.items(), key=lambda kv: kv[1], reverse=True)
    ][:3]

    top_tenants = [
        {"tenant_id": tid, "name": tenant_names.get(tid, "—"), "count": cnt}
        for tid, cnt in sorted(tenant_counts.items(), key=lambda kv: kv[1], reverse=True)
    ][:5]

    currency = (
        max(currency_counts.items(), key=lambda kv: kv[1])[0]
        if currency_counts else None
    )

    return {
        "total_bookings": total,
        "favorite_category": favorite_category,
        "cities": cities,
        "avg_price": str(avg_price) if avg_price is not None else None,
        "price_band": price_band,
        "currency": currency,
        "avg_guests": avg_guests,
        "preferred_months": preferred_months,
        "top_tenants": top_tenants,
    }


def _fallback_recap(profile: dict[str, Any]) -> str:
    if profile["total_bookings"] == 0:
        return ("No trips recorded yet — book your first experience to "
                "start building your travel memory.")
    parts: list[str] = []
    parts.append(f"You have {profile['total_bookings']} trips so far.")
    if profile["favorite_category"]:
        parts.append(f"Your favorite category is {profile['favorite_category']}.")
    if profile["cities"]:
        parts.append("You often visit " + ", ".join(profile["cities"]) + ".")
    if profile["preferred_months"]:
        parts.append("You usually travel in " + ", ".join(profile["preferred_months"]) + ".")
    if profile["avg_guests"]:
        parts.append(f"Average group size: {profile['avg_guests']}.")
    return " ".join(parts)


def _safe_ai(prompt: str) -> str | None:
    try:
        result = ai_service.chat(prompt, history=[])
        return (result or {}).get("content", "").strip() or None
    except Exception:
        return None


def summarize(
    db: DBSession,
    *,
    user_id: str,
    language: str = "en",
) -> dict[str, Any]:
    """Return the user's travel profile + a personalized AI recap."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")

    profile = build_profile(db, user_id)

    if profile["total_bookings"] == 0:
        return {
            "profile": profile,
            "recap": _fallback_recap(profile),
            "suggestions": [],
            "provider": "fallback",
        }

    lines: list[str] = ["USER_PROFILE:"]
    lines.append(f"  total_bookings={profile['total_bookings']}")
    if profile["favorite_category"]:
        lines.append(f"  favorite_category={profile['favorite_category']}")
    if profile["cities"]:
        lines.append(f"  cities={', '.join(profile['cities'])}")
    if profile["avg_price"]:
        cur = profile["currency"] or ""
        lines.append(f"  avg_price={profile['avg_price']} {cur}")
    if profile["avg_guests"]:
        lines.append(f"  avg_guests={profile['avg_guests']}")
    if profile["preferred_months"]:
        lines.append(f"  preferred_months={', '.join(profile['preferred_months'])}")
    if profile["top_tenants"]:
        names = ", ".join(t["name"] for t in profile["top_tenants"])
        lines.append(f"  top_tenants={names}")

    lang = _LANGUAGE_NAMES.get(language, "English")
    prompt = (
        "You are a personal travel assistant for Platform-X. Based ONLY on "
        "the user profile below, write:\n"
        "1) A short warm recap (2-3 sentences) of who they are as a traveler.\n"
        "2) Two concrete suggestion lines (each one sentence) for their next trip.\n\n"
        "RULES:\n"
        "- Do NOT invent places, prices, or bookings not present in the profile.\n"
        "- Be concrete: reference at least one real city or category from the profile.\n"
        "- Write everything in " + lang + ".\n\n"
        + "\n".join(lines)
    )
    recap = _safe_ai(prompt)
    provider = "ai"
    if not recap:
        recap = _fallback_recap(profile)
        provider = "fallback"

    return {
        "profile": profile,
        "recap": recap,
        "suggestions": [],
        "provider": provider,
    }
