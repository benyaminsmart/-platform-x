"""AI Multi-Business Bundle Deals — propose cross-category packages.

Phase 51 (Wave 2, Blue-Ocean B3).

Design:
- Deterministic layer: for a given city, pick a cross-category combo
  (1 hotel + up to 2 restaurants + 1 entertainment or travel) from live
  Platform-X services.
- Bundle discount tiers (platform policy, transparent):
      3 items  → 10%
      4 items  → 15%
      5+ items → 20%
  Discount applies to the bundle SUBTOTAL (sum of estimated totals).
- AI writes a short marketing-style rationale.
- Deterministic fallback if AI fails.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.services import search_service
from app.services.ai import service as ai_service


SUPPORTED_LANGUAGES = {"en", "ar", "fil", "hi"}
_LANGUAGE_NAMES = {
    "en": "English", "ar": "Arabic (Modern Standard Arabic)",
    "fil": "Filipino (Tagalog)", "hi": "Hindi",
}

# Bundle discount tiers by item count
DISCOUNT_TIERS = {3: 0.10, 4: 0.15, 5: 0.20}

# Composition policy (fixed)
COMPOSITION = {
    "hotels": 1,
    "restaurants": 2,
    "entertainment": 1,
    "travel": 1,
}
MAX_ITEMS = 5


def _round2(x: float) -> float:
    return round(x, 2)


def _discount_for(count: int) -> float:
    if count >= 5:
        return 0.20
    if count == 4:
        return 0.15
    if count == 3:
        return 0.10
    return 0.0


def _pick_top(items: list[dict], category: str, n: int) -> list[dict]:
    pool = [it for it in items if it.get("category") == category]
    pool.sort(key=lambda it: (-(float(it.get("rating") or 0)), float(it.get("price") or 0)))
    return pool[:n]


def build(
    db: DBSession,
    *,
    city: str | None = None,
    days: int = 3,
    guests: int = 2,
    language: str = "en",
) -> dict[str, Any]:
    """Return a bundle + AI rationale."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")
    if days < 1 or days > 30:
        raise ValueError("days must be between 1 and 30")
    if guests < 1 or guests > 50:
        raise ValueError("guests must be between 1 and 50")

    # Gather candidates from each category
    candidates: list[dict] = []
    for cat in COMPOSITION.keys():
        res = search_service.search_services(
            db, category=cat, sort="rating", page=1, page_size=30,
            location_search=city, guests=guests if cat == "hotels" else 1,
        )
        candidates.extend(res.get("items", []))

    # Pick items per composition policy
    picked: list[dict] = []
    for cat, n in COMPOSITION.items():
        picked.extend(_pick_top(candidates, cat, n))
        if len(picked) >= MAX_ITEMS:
            break
    picked = picked[:MAX_ITEMS]

    if not picked:
        return {
            "items": [],
            "subtotal": 0.0,
            "discount_percent": 0.0,
            "discount_amount": 0.0,
            "total": 0.0,
            "currency": "AED",
            "advice": "No matching businesses were found for this city and party size.",
            "provider": "fallback",
        }

    # Estimate per-item totals
    bundle_items: list[dict] = []
    subtotal = 0.0
    currency = picked[0].get("currency") or "AED"
    for it in picked:
        cat = it.get("category")
        mult = days if cat == "hotels" else min(days, 3)
        guest_mult = guests if cat == "hotels" else 1
        est = float(it.get("price") or 0) * mult * guest_mult
        subtotal += est
        bundle_items.append({
            "category": cat,
            "service_id": it.get("service_id"),
            "service_name": it.get("service_name"),
            "tenant_slug": it.get("tenant_slug"),
            "tenant_name": it.get("tenant_name"),
            "price": float(it.get("price") or 0),
            "currency": it.get("currency") or currency,
            "rating": it.get("rating"),
            "estimated_total": _round2(est),
            "location": it.get("location"),
        })

    discount_pct = _discount_for(len(bundle_items))
    discount_amount = _round2(subtotal * discount_pct)
    total = _round2(subtotal - discount_amount)

    # AI rationale grounded in the bundle
    lines = [
        f"CITY: {city or 'any'}",
        f"DAYS: {days}, GUESTS: {guests}",
        f"ITEM_COUNT: {len(bundle_items)}",
        f"SUBTOTAL: {_round2(subtotal)} {currency}",
        f"DISCOUNT: {int(discount_pct * 100)}%",
        f"TOTAL: {total} {currency}",
        "",
        "ITEMS:",
    ]
    for it in bundle_items:
        lines.append(
            f"  - {it['category']}: {it['service_name']} at {it['tenant_name']} "
            f"({it['price']} {it['currency']}, est={it['estimated_total']})"
        )

    lang = _LANGUAGE_NAMES.get(language, "English")
    prompt = (
        "You are a marketing copywriter for Platform-X. Write a short, "
        "warm pitch (max 3 short paragraphs) for the multi-business bundle "
        "below. Do NOT invent prices or places. Mention the bundle discount "
        "tier only once. Write everything in " + lang + ".\n\n"
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
        names = ", ".join(it["service_name"] for it in bundle_items)
        advice = (
            f"Bundle of {len(bundle_items)}: {names}. "
            f"Save {int(discount_pct * 100)}% — total {total} {currency} "
            f"(was {_round2(subtotal)} {currency})."
        )

    return {
        "items": bundle_items,
        "subtotal": _round2(subtotal),
        "discount_percent": int(discount_pct * 100),
        "discount_amount": discount_amount,
        "total": total,
        "currency": currency,
        "advice": advice,
        "provider": provider,
    }
