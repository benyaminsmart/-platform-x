"""AI Budget Optimizer — find an optimal mix of services within a budget.

Phase 50 (Wave 2, AI depth).

Design:
- Deterministic layer: given a city, days, guests, and budget, pick a
  balanced package from live Platform-X services across categories
  (hotels, restaurants, entertainment, travel).
- Allocation policy (fixed, transparent):
    hotels          50% of budget
    restaurants     25%
    entertainment   15%
    travel          10%
  Only categories with at least one matching service are used; the
  remaining allocation is redistributed proportionally.
- The AI writes the rationale ONLY. It never invents numbers.
- Fallback text if AI fails.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.services import search_service
from app.services.ai import service as ai_service


SUPPORTED_LANGUAGES = {"en", "ar", "fil", "hi"}
_LANGUAGE_NAMES = {
    "en": "English", "ar": "Arabic (Modern Standard Arabic)",
    "fil": "Filipino (Tagalog)", "hi": "Hindi",
}

# Allocation policy (percent of budget)
ALLOCATION = {
    "hotels": 0.50,
    "restaurants": 0.25,
    "entertainment": 0.15,
    "travel": 0.10,
}
CATEGORY_ORDER = ["hotels", "restaurants", "entertainment", "travel"]


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"))


def _pick_for_category(
    items: list[dict], *, category: str, allocation: float, days: int, guests: int
) -> dict | None:
    """Pick the best service in a category that fits the allocation.

    Heuristic: prefer the highest-rated service whose estimated total
    cost (price * days * (guests if hotel, else 1)) fits in allocation.
    Falls back to the cheapest option if none fit.
    """
    cat_items = [it for it in items if it.get("category") == category]
    if not cat_items:
        return None

    def est_total(it: dict) -> float:
        # hotels multiply by days; others by a modest days factor
        mult = days if category == "hotels" else min(days, 3)
        guest_mult = guests if category == "hotels" else 1
        return float(it.get("price") or 0) * mult * guest_mult

    fitting = [it for it in cat_items if est_total(it) <= allocation]
    pool = fitting if fitting else cat_items
    # sort by rating desc, then price asc
    pool.sort(key=lambda it: (-(float(it.get("rating") or 0)), float(it.get("price") or 0)))
    best = pool[0]
    return {
        "category": category,
        "service_id": best.get("service_id"),
        "service_name": best.get("service_name"),
        "tenant_slug": best.get("tenant_slug"),
        "tenant_name": best.get("tenant_name"),
        "price": float(best.get("price") or 0),
        "currency": best.get("currency") or "AED",
        "rating": best.get("rating"),
        "estimated_total": round(est_total(best), 2),
        "location": best.get("location"),
    }


def optimize(
    db: DBSession,
    *,
    city: str | None = None,
    days: int = 3,
    guests: int = 2,
    budget: float,
    currency: str = "AED",
    language: str = "en",
) -> dict[str, Any]:
    """Return an optimal package + AI rationale."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")
    if days < 1 or days > 30:
        raise ValueError("days must be between 1 and 30")
    if guests < 1 or guests > 50:
        raise ValueError("guests must be between 1 and 50")
    if budget <= 0:
        raise ValueError("budget must be positive")

    # Gather candidates from search_service for each relevant category
    candidates: list[dict] = []
    for cat in CATEGORY_ORDER:
        res = search_service.search_services(
            db, category=cat, sort="rating", page=1, page_size=30,
            location_search=city, guests=guests if cat == "hotels" else 1,
        )
        for it in res.get("items", []):
            candidates.append(it)

    # Figure out which categories actually have candidates
    present = [c for c in CATEGORY_ORDER if any(it.get("category") == c for it in candidates)]
    if not present:
        return {
            "package": [],
            "total_estimated": 0.0,
            "budget": budget,
            "currency": currency,
            "remaining": budget,
            "advice": "No matching services were found for this city and party size.",
            "provider": "fallback",
        }

    # Redistribute allocation proportionally among present categories
    total_weight = sum(ALLOCATION[c] for c in present)
    effective = {c: (ALLOCATION[c] / total_weight) * budget for c in present}

    package: list[dict] = []
    total_estimated = 0.0
    for c in present:
        chosen = _pick_for_category(
            candidates, category=c, allocation=effective[c], days=days, guests=guests,
        )
        if chosen is not None:
            package.append(chosen)
            total_estimated += chosen["estimated_total"]

    remaining = max(0.0, budget - total_estimated)

    # AI rationale — grounded ONLY in chosen package
    lines = [
        f"BUDGET: {budget} {currency}",
        f"CITY: {city or 'any'}",
        f"DAYS: {days}, GUESTS: {guests}",
        f"TOTAL_ESTIMATED: {round(total_estimated, 2)} {currency}",
        f"REMAINING: {round(remaining, 2)} {currency}",
        "",
        "CHOSEN_PACKAGE:",
    ]
    for it in package:
        lines.append(
            f"  - {it['category']}: {it['service_name']} at {it['tenant_name']} "
            f"({it['price']} {it['currency']}, est_total={it['estimated_total']})"
        )

    lang = _LANGUAGE_NAMES.get(language, "English")
    prompt = (
        "You are a travel budget advisor for Platform-X. Based ONLY on the "
        "package below, write a short, friendly rationale (max 3 short "
        "paragraphs) explaining why this mix is good value for the user's "
        "budget. Do NOT invent prices or places. Mention at most one number "
        "already present in the package. Write everything in " + lang + ".\n\n"
        + "\n".join(lines)
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
        parts = []
        if package:
            parts.append(
                "Recommended mix: "
                + ", ".join(f"{it['service_name']} ({it['category']})" for it in package)
                + "."
            )
            parts.append(
                f"Estimated total: {round(total_estimated, 2)} {currency} of "
                f"{budget} {currency} budget — remaining {round(remaining, 2)} {currency}."
            )
        else:
            parts.append("No suitable package found within this budget.")
        advice = " ".join(parts)

    return {
        "package": package,
        "total_estimated": round(total_estimated, 2),
        "budget": budget,
        "currency": currency,
        "remaining": round(remaining, 2),
        "advice": advice,
        "provider": provider,
    }
