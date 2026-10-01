"""AI Receptionist — auto-draft business replies to guest messages.

Phase 53 (Wave 2, Blue-Ocean B10).

Design:
- Deterministic layer: gather grounded tenant facts (services, hours,
  pricing range, policies) from the DB and recent thread messages.
- AI layer: draft a short, professional reply in the guest's language.
- The AI never invents facts, prices, or availability.
- Owner can preview, edit, and send manually (auto-send is opt-in
  at a later phase).
- Deterministic fallback always available.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.service import Service
from app.models.tenant import Tenant
from app.services import message_service
from app.services.ai import service as ai_service


SUPPORTED_LANGUAGES = {"en", "ar", "fil", "hi"}
_LANGUAGE_NAMES = {
    "en": "English", "ar": "Arabic (Modern Standard Arabic)",
    "fil": "Filipino (Tagalog)", "hi": "Hindi",
}

# Tonality is a business choice
ALLOWED_TONES = {"professional", "friendly", "concise"}


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"))


def _services_snippet(db: DBSession, tenant_id: str, limit: int = 8) -> list[dict[str, Any]]:
    rows = (
        db.query(Service)
        .filter(Service.tenant_id == tenant_id, Service.status == "active")
        .order_by(Service.display_order.asc(), Service.name.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "name": s.name,
            "type": s.type,
            "price": str(_round2(Decimal(str(s.price)))),
            "currency": s.currency,
        }
        for s in rows
    ]


def _price_range(services: list[dict[str, Any]]) -> tuple[str | None, str | None, str | None]:
    if not services:
        return None, None, None
    prices = [Decimal(s["price"]) for s in services]
    cur = services[0]["currency"]
    return str(_round2(min(prices))), str(_round2(max(prices))), cur


def _thread_snippet(
    db: DBSession, *, tenant_id: str, thread_id: str, limit: int = 6
) -> list[dict[str, str]]:
    rows = message_service.list_thread_messages(
        db, tenant_id=tenant_id, thread_id=thread_id, limit=limit,
    )
    return [{"role": m.sender_role, "body": m.body} for m in rows]


def _fallback_reply(*, tenant: Tenant, services: list[dict[str, Any]]) -> str:
    name = tenant.name
    if not services:
        return (
            f"Thank you for reaching out to {name}. We received your message "
            f"and a member of our team will reply as soon as possible."
        )
    lo, hi, cur = _price_range(services)
    sample = ", ".join(s["name"] for s in services[:3])
    parts = [f"Thank you for contacting {name}."]
    if lo and hi:
        parts.append(f"Our prices currently range from {lo} to {hi} {cur}.")
    if sample:
        parts.append(f"Popular options include {sample}.")
    parts.append("Please let us know your dates and preferences and we'll help you further.")
    return " ".join(parts)


def draft_reply(
    db: DBSession,
    *,
    tenant: Tenant,
    thread_id: str,
    language: str = "en",
    tone: str = "professional",
) -> dict[str, Any]:
    """Draft an AI reply for the last guest message in a thread.

    status: 'ok' | 'empty_thread' | 'no_guest_message'.
    """
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")
    if tone not in ALLOWED_TONES:
        raise ValueError(f"tone must be one of: {sorted(ALLOWED_TONES)}")

    thread = _thread_snippet(db, tenant_id=tenant.id, thread_id=thread_id)
    if not thread:
        return {
            "reply": "",
            "provider": "fallback",
            "status": "empty_thread",
        }

    # The last guest message is the anchor; if the last is from business
    # we still respond to the latest guest line for continuity.
    last_guest = None
    for m in reversed(thread):
        if m["role"] == "user":
            last_guest = m["body"]
            break
    if last_guest is None:
        return {
            "reply": "",
            "provider": "fallback",
            "status": "no_guest_message",
        }

    services = _services_snippet(db, tenant.id)
    lo, hi, cur = _price_range(services)

    # Build grounded prompt
    lines = [
        f"BUSINESS: {tenant.name}",
        f"CATEGORY: {(tenant.config or {}).get('type') or 'general'}",
    ]
    if lo and hi:
        lines.append(f"PRICE_RANGE: {lo}-{hi} {cur}")
    if services:
        lines.append("SERVICES:")
        for s in services[:6]:
            lines.append(f"  - {s['name']} ({s['type']}, {s['price']} {s['currency']})")

    lines.append("")
    lines.append("RECENT_THREAD:")
    for m in thread[-5:]:
        role_label = "GUEST" if m["role"] == "user" else "BUSINESS"
        lines.append(f"  {role_label}: {m['body']}")

    lang = _LANGUAGE_NAMES.get(language, "English")
    tone_hint = {
        "professional": "professional and warm",
        "friendly": "friendly and casual",
        "concise": "very short and to the point",
    }[tone]

    prompt = (
        f"You are the AI receptionist for {tenant.name}. Write a single reply "
        f"to the guest's most recent message. Tone: {tone_hint}. "
        f"RULES:\n"
        f"- Do NOT invent prices, availability, or services not listed above.\n"
        f"- Do NOT promise discounts.\n"
        f"- If the guest asks about availability, invite them to share dates "
        f"and confirm you will check.\n"
        f"- Keep it under 100 words.\n"
        f"- Write in {lang}.\n\n"
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
        reply = _fallback_reply(tenant=tenant, services=services)
        provider = "fallback"

    return {
        "reply": reply,
        "provider": provider,
        "status": "ok",
    }
