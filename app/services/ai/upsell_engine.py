"""AI Upsell Engine — propose add-ons for an in-progress booking.

Phase 56 (Wave 3, Blue-Ocean B13).

Design principles:
- Deterministic layer: given the base service being booked, find other
  active services from the SAME tenant that are complementary add-ons:
    * higher-priced same type (e.g. upgrade room → suite)
    * ancillary types (spa, breakfast, transfer, tour, entertainment)
- Max 3 suggestions. AI writes a short rationale.
- Never invents services or prices. Only what exists in the DB.
- Deterministic fallback rationale always available.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.service import Service
from app.models.tenant import Tenant
from app.services.ai import service as ai_service


SUPPORTED_LANGUAGES = {"en", "ar", "fil", "hi"}
_LANGUAGE_NAMES = {
    "en": "English", "ar": "Arabic (Modern Standard Arabic)",
    "fil": "Filipino (Tagalog)", "hi": "Hindi",
}

# Ancillary service types that make natural add-ons (matched loosely)
_ANCILLARY_KEYWORDS = (
    "spa", "breakfast", "meal", "dinner", "lunch", "transfer",
    "airport", "tour", "activity", "addon", "add-on", "package",
    "upgrade", "ticket", "experience",
)

MAX_SUGGESTIONS = 3
MAX_UPGRADE_MULTIPLIER = Decimal("3.0")  # upgrade price ≤ base × 3


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"))


def _is_ancillary(s: Service) -> bool:
    haystack = " ".join(filter(None, [
        (s.name or "").lower(),
        (s.type or "").lower(),
        (s.description or "").lower(),
    ]))
    return any(k in haystack for k in _ANCILLARY_KEYWORDS)


def _candidates(db: DBSession, *, tenant_id: str, base_service_id: str) -> dict[str, list[Service]]:
    rows = (
        db.query(Service)
        .filter(Service.tenant_id == tenant_id, Service.status == "active")
        .all()
    )
    base = None
    for s in rows:
        if s.id == base_service_id:
            base = s
            break
    if base is None:
        return {"upgrades": [], "ancillaries": []}

    base_price = Decimal(str(base.price))
    upgrades: list[Service] = []
    ancillaries: list[Service] = []
    for s in rows:
        if s.id == base.id:
            continue
        if s.type == base.type:
            p = Decimal(str(s.price))
            if base_price < p <= base_price * MAX_UPGRADE_MULTIPLIER:
                upgrades.append(s)
        elif _is_ancillary(s):
            ancillaries.append(s)

    upgrades.sort(key=lambda s: Decimal(str(s.price)))
    ancillaries.sort(key=lambda s: -(float(s.price)))
    return {"upgrades": upgrades, "ancillaries": ancillaries}


def _ser(s: Service, *, kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "service_id": s.id,
        "service_name": s.name,
        "service_type": s.type,
        "price": float(s.price),
        "currency": s.currency,
        "description": (s.description or "")[:200] or None,
    }


def suggest(
    db: DBSession,
    *,
    tenant: Tenant,
    base_service_id: str,
    language: str = "en",
) -> dict[str, Any]:
    """Return up to 3 upsell suggestions + AI rationale.

    status: 'ok' | 'no_base' | 'empty'.
    """
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")

    base = (
        db.query(Service)
        .filter(Service.id == base_service_id, Service.tenant_id == tenant.id)
        .one_or_none()
    )
    if base is None:
        return {
            "suggestions": [],
            "rationale": "",
            "provider": "fallback",
            "status": "no_base",
        }

    pool = _candidates(db, tenant_id=tenant.id, base_service_id=base.id)

    suggestions: list[dict[str, Any]] = []
    # Ancillaries first (highest value), then upgrades
    for s in pool["ancillaries"][:2]:
        suggestions.append(_ser(s, kind="ancillary"))
    for s in pool["upgrades"][:1]:
        suggestions.append(_ser(s, kind="upgrade"))
    suggestions = suggestions[:MAX_SUGGESTIONS]

    if not suggestions:
        return {
            "suggestions": [],
            "rationale": "No add-ons are available for this service right now.",
            "provider": "fallback",
            "status": "empty",
        }

    # Build grounded prompt
    lines = [
        f"BUSINESS: {tenant.name}",
        f"BASE_SERVICE: {base.name} ({base.type}, {_round2(Decimal(str(base.price)))} {base.currency})",
        "",
        "AVAILABLE_ADDONS:",
    ]
    for s in suggestions:
        lines.append(
            f"  - {s['service_name']} ({s['kind']}, {s['price']} {s['currency']})"
        )

    lang = _LANGUAGE_NAMES.get(language, "English")
    prompt = (
        "You are a concierge for Platform-X. Based ONLY on the add-ons below, "
        "write a short, warm pitch (max 3 short sentences) recommending them "
        "to the guest currently booking. Do NOT invent prices or services. "
        "Mention at most one concrete add-on. Write in " + lang + ".\n\n"
        + "\n".join(lines)
    )

    rationale = None
    provider = "fallback"
    try:
        result = ai_service.chat(prompt, history=[])
        rationale = (result or {}).get("content", "").strip() or None
        if rationale:
            provider = "ai"
    except Exception:
        rationale = None

    if not rationale:
        names = ", ".join(s["service_name"] for s in suggestions)
        rationale = (
            f"Guests who book {base.name} often add: {names}. "
            f"They round out the stay nicely."
        )

    return {
        "suggestions": suggestions,
        "rationale": rationale,
        "provider": provider,
        "status": "ok",
    }
