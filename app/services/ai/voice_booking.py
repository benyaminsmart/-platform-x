"""AI Voice Booking — parse a spoken request into a booking intent.

Phase 64 (Wave 3, Blue-Ocean B1).

Design principles:
- Mock/text-first: the user sends a *transcript* (real voice→text
  integration is deferred to the VPS/payment phase).
- Deterministic layer: parse structured intent from the transcript:
    * category (hotel / restaurant / travel / entertainment)
    * destination / city
    * check-in / check-out dates (or a relative phrase like "next weekend")
    * guests
    * special requests
- AI layer: polish the reply (acknowledgement + next step), grounded
  ONLY in the parsed fields. Never invents dates or prices.
- Deterministic fallback always available.
- Read-only: never creates a Booking.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.services import search_service
from app.services.ai import service as ai_service


SUPPORTED_LANGUAGES = {"en", "ar", "fil", "hi"}
_LANGUAGE_NAMES = {
    "en": "English", "ar": "Arabic (Modern Standard Arabic)",
    "fil": "Filipino (Tagalog)", "hi": "Hindi",
}

_CATEGORY_HINTS = {
    "hotels": ("hotel", "room", "stay", "suite", "resort"),
    "restaurants": ("restaurant", "dinner", "lunch", "table", "eat", "food", "cafe"),
    "travel": ("flight", "tour", "package", "trip", "visa", "travel"),
    "entertainment": ("show", "ticket", "cinema", "spa", "waterpark", "activity", "park"),
}

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Known cities (best-effort — kept small, extensible)
_CITIES = ("dubai", "abu dhabi", "sharjah", "ajman", "fujairah",
           "doha", "riyadh", "jeddah", "muscat", "manama", "kuwait city",
           "istanbul", "cairo", "beirut", "amman", "paris", "london",
           "rome", "barcelona", "new york", "bangkok", "singapore",
           "mumbai", "delhi", "karachi", "lahore", "tehran")


def _round2(x: float) -> float:
    return round(x, 2)


def _detect_category(text: str) -> str | None:
    low = text.lower()
    for cat, hints in _CATEGORY_HINTS.items():
        for h in hints:
            if h in low:
                return cat
    return None


def _detect_city(text: str) -> str | None:
    low = text.lower()
    for c in _CITIES:
        if c in low:
            return c.title()
    return None


def _detect_guests(text: str) -> int | None:
    low = text.lower()
    # "for 4", "4 guests", "party of 3", "we are 5", "5 people"
    m = re.search(r"(?:for|party of|group of|we are|we're)\s+(\d{1,2})", low)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d{1,2})\s+(?:guests|people|persons|adults|pax)", low)
    if m:
        return int(m.group(1))
    return None


def _detect_relative_dates(text: str) -> tuple[date | None, date | None]:
    low = text.lower()
    today = date.today()

    if "tonight" in low or "today" in low:
        return today, today + timedelta(days=1)
    if "tomorrow" in low:
        return today + timedelta(days=1), today + timedelta(days=2)
    if "this weekend" in low:
        # upcoming Saturday → +2 days
        days_ahead = (5 - today.weekday()) % 7 or 7
        ci = today + timedelta(days=days_ahead)
        return ci, ci + timedelta(days=2)
    if "next weekend" in low:
        days_ahead = (5 - today.weekday()) % 7 or 7
        ci = today + timedelta(days=days_ahead + 7)
        return ci, ci + timedelta(days=2)
    if "next week" in low:
        ci = today + timedelta(days=7)
        return ci, ci + timedelta(days=2)
    return None, None


def _detect_explicit_dates(text: str) -> tuple[date | None, date | None]:
    """Find patterns like 'March 15', 'on 2026-04-10', 'from 5 May to 8 May'."""
    low = text.lower()
    today = date.today()
    current_year = today.year

    # ISO date: 2026-04-10
    iso = re.findall(r"(\d{4})-(\d{2})-(\d{2})", low)
    if len(iso) >= 1:
        try:
            ci = date(int(iso[0][0]), int(iso[0][1]), int(iso[0][2]))
            if len(iso) >= 2:
                co = date(int(iso[1][0]), int(iso[1][1]), int(iso[1][2]))
                return ci, co
            return ci, ci + timedelta(days=1)
        except ValueError:
            pass

    # "March 15" or "15 March"
    for name, num in _MONTHS.items():
        m1 = re.search(rf"{name}\s+(\d{{1,2}})", low)
        if m1:
            try:
                ci = date(current_year, num, int(m1.group(1)))
                if ci < today:
                    ci = date(current_year + 1, num, int(m1.group(1)))
                return ci, ci + timedelta(days=1)
            except ValueError:
                pass
        m2 = re.search(rf"(\d{{1,2}})\s+{name}", low)
        if m2:
            try:
                ci = date(current_year, num, int(m2.group(1)))
                if ci < today:
                    ci = date(current_year + 1, num, int(m2.group(1)))
                return ci, ci + timedelta(days=1)
            except ValueError:
                pass

    return None, None


def parse_intent(transcript: str) -> dict[str, Any]:
    """Pure deterministic intent parser (no DB, no AI)."""
    text = (transcript or "").strip()
    if not text:
        return {
            "category": None, "city": None, "check_in": None, "check_out": None,
            "guests": None, "raw": "",
        }
    category = _detect_category(text)
    city = _detect_city(text)
    ci, co = _detect_explicit_dates(text)
    if ci is None:
        ci, co = _detect_relative_dates(text)
    guests = _detect_guests(text)
    return {
        "category": category,
        "city": city,
        "check_in": ci.isoformat() if ci else None,
        "check_out": co.isoformat() if co else None,
        "guests": guests,
        "raw": text,
    }


def _match_services(
    db: DBSession, *, category: str | None, city: str | None, guests: int | None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Best-effort live service matches. Never raises."""
    try:
        res = search_service.search_services(
            db, category=category, location_search=city,
            guests=guests or 1, sort="rating", page=1, page_size=limit,
        )
        return res.get("items", [])[:limit]
    except Exception:
        return []


def _fallback_reply(intent: dict[str, Any], matches: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    if intent["category"]:
        parts.append(f"Understood — you'd like a {intent['category']} booking.")
    if intent["city"]:
        parts.append(f"Destination: {intent['city']}.")
    if intent["check_in"] and intent["check_out"]:
        parts.append(f"Dates: {intent['check_in']} → {intent['check_out']}.")
    if intent["guests"]:
        parts.append(f"Guests: {intent['guests']}.")
    if matches:
        names = ", ".join(m.get("service_name", "?") for m in matches)
        parts.append(f"Top matches on Platform-X: {names}.")
    parts.append("Say 'book' to proceed, or add dates and guest count if I missed anything.")
    return " ".join(parts)


def voice_request(
    db: DBSession,
    *,
    transcript: str,
    language: str = "en",
) -> dict[str, Any]:
    """Parse a spoken booking request and return a reply + live matches.

    status: 'ok' | 'empty' | 'unrecognized'.
    """
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")

    if not (transcript or "").strip():
        return {
            "status": "empty",
            "intent": {"raw": ""},
            "matches": [],
            "reply": "",
            "provider": "fallback",
        }

    intent = parse_intent(transcript)
    has_signal = any([
        intent["category"], intent["city"], intent["check_in"], intent["guests"]
    ])
    if not has_signal:
        return {
            "status": "unrecognized",
            "intent": intent,
            "matches": [],
            "reply": "Sorry, I couldn't catch that. Try: 'Book a hotel in Dubai next weekend for 2'.",
            "provider": "fallback",
        }

    matches = _match_services(
        db, category=intent["category"], city=intent["city"], guests=intent["guests"],
    )

    # Build AI prompt (grounded)
    lines = [
        f"RAW_TRANSCRIPT: {intent['raw']}",
        "PARSED_INTENT:",
        f"  category={intent['category']}",
        f"  city={intent['city']}",
        f"  check_in={intent['check_in']}",
        f"  check_out={intent['check_out']}",
        f"  guests={intent['guests']}",
        "",
        "LIVE_MATCHES:",
    ]
    for m in matches:
        lines.append(
            f"  - {m.get('service_name')} at {m.get('tenant_name')} "
            f"({m.get('price')} {m.get('currency')})"
        )

    lang = _LANGUAGE_NAMES.get(language, "English")
    prompt = (
        "You are the AI voice assistant for Platform-X. A guest spoke the "
        "request below (transcribed). Reply briefly and conversationally, "
        "as if speaking back. Confirm what you understood using ONLY the "
        "parsed fields, and mention at most two live matches by name. Do NOT "
        "invent prices, dates, or availability. Invite the guest to say "
        "'book' to proceed. Write in " + lang + ".\n\n"
        + "\n".join(lines)
    )

    reply = None
    provider = "fallback"
    try:
        result = ai_service.chat(prompt, history=[])
        reply = (result or {}).get("content", "").strip() or None
        if reply:
            provider = "ai"
    except Exception:
        reply = None

    if not reply:
        reply = _fallback_reply(intent, matches)
        provider = "fallback"

    return {
        "status": "ok",
        "intent": intent,
        "matches": matches,
        "reply": reply,
        "provider": provider,
    }
