"""AI Content Writer — generate service descriptions + image keywords.

Design principles:
- AI writes prose grounded in REAL service data (name, type, price, attributes).
- AI never invents facts (e.g. "5-star" is only used if the tenant rating >= 4.5).
- Multi-language: en, ar, fil, hi.
- Deterministic fallback if AI is unavailable.
- Image suggestions use Unsplash source URL — no API key required.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

from sqlalchemy.orm import Session as DBSession

from app.models.service import Service
from app.models.tenant import Tenant
from app.services.ai import service as ai_service


SUPPORTED_LANGUAGES = {"en", "ar", "fil", "hi"}
SUPPORTED_TONES = {"professional", "friendly", "luxury", "playful"}

_LANGUAGE_NAMES = {
    "en": "English",
    "ar": "Arabic (Modern Standard)",
    "fil": "Filipino (Tagalog)",
    "hi": "Hindi",
}


# ---------- Helpers ----------


def _tenant_context(tenant: Tenant) -> dict[str, Any]:
    cfg = tenant.config or {}
    return {
        "name": tenant.name,
        "type": cfg.get("type", "business"),
        "location": cfg.get("location"),
        "rating": cfg.get("rating"),
        "reviews_count": cfg.get("reviews_count"),
        "tagline": cfg.get("tagline"),
        "amenities": cfg.get("amenities") or [],
    }


def _safe_ai(prompt: str) -> str | None:
    try:
        result = ai_service.chat(prompt, history=[])
        content = (result or {}).get("content", "").strip()
        # Strip surrounding quotes if the AI wrapped the whole reply
        if content.startswith('"') and content.endswith('"') and content.count('"') == 2:
            content = content[1:-1]
        return content or None
    except Exception:
        return None


# ---------- Service descriptions ----------


def _fallback_description(service: Service, tenant: Tenant, language: str) -> str:
    """Deterministic description if AI is unavailable."""
    parts = [service.name]
    if service.description:
        parts.append(service.description)
    if service.capacity:
        parts.append(f"Capacity: {service.capacity}")
    if tenant.config and tenant.config.get("location"):
        parts.append(f"Location: {tenant.config['location']}")
    return ". ".join(str(p) for p in parts if p) + "."


def _build_service_prompt(
    tenant: Tenant,
    service: Service,
    *,
    language: str,
    tone: str,
) -> str:
    ctx = _tenant_context(tenant)
    lang = _LANGUAGE_NAMES.get(language, "English")

    # Only claim a rating if it's actually strong
    rating_line = ""
    if isinstance(ctx["rating"], (int, float)) and ctx["rating"] >= 4.5:
        rating_line = f"Business rating: {ctx['rating']}/5 from {ctx['reviews_count']} reviews (safe to mention)."
    else:
        rating_line = "Do NOT mention a rating or star count."

    amenities = ", ".join(ctx["amenities"][:6]) if ctx["amenities"] else "—"
    attrs = service.attributes or {}
    attrs_str = ", ".join(f"{k}={v}" for k, v in list(attrs.items())[:8]) or "—"

    return f"""You are a professional hospitality copywriter for Platform-X.

TASK: Write a short, appealing service description.

LANGUAGE: Respond ONLY in {lang}.
TONE: {tone}.

SERVICE:
- Name: {service.name}
- Type: {service.type}
- Price: {service.price} {service.currency}
- Capacity: {service.capacity or "n/a"}
- Attributes: {attrs_str}
- Current notes: {service.description or "n/a"}

BUSINESS:
- Name: {ctx['name']}
- Type: {ctx['type']}
- Location: {ctx['location'] or "n/a"}
- Tagline: {ctx['tagline'] or "n/a"}
- Amenities: {amenities}
- {rating_line}

RULES:
- 3 to 5 sentences. No bullet lists. No emojis.
- Never invent facts not present above (no fake awards, no made-up amenities).
- Focus on what makes the service appealing without exaggeration.
- Do NOT repeat the price; the platform shows it separately.
- Return only the description text, nothing else."""


def write_service_description(
    db: DBSession,
    *,
    tenant: Tenant,
    service: Service,
    language: str = "en",
    tone: str = "professional",
) -> dict[str, Any]:
    """Return {'description', 'language', 'tone', 'provider', 'tokens_used'}."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")
    if tone not in SUPPORTED_TONES:
        raise ValueError(f"tone must be one of: {sorted(SUPPORTED_TONES)}")

    prompt = _build_service_prompt(tenant, service, language=language, tone=tone)
    content = _safe_ai(prompt)
    if not content:
        content = _fallback_description(service, tenant, language)

    return {
        "description": content,
        "language": language,
        "tone": tone,
        "provider": "ai" if content != _fallback_description(service, tenant, language) else "fallback",
    }


# ---------- Business tagline ----------


def _fallback_tagline(tenant: Tenant, language: str) -> str:
    cfg = tenant.config or {}
    parts = [tenant.name]
    if cfg.get("type"):
        parts.append(str(cfg["type"]).replace("_", " ").title())
    if cfg.get("location"):
        parts.append(str(cfg["location"]))
    return " — ".join(parts[:3]) or tenant.name


def _build_tagline_prompt(tenant: Tenant, *, language: str) -> str:
    ctx = _tenant_context(tenant)
    lang = _LANGUAGE_NAMES.get(language, "English")
    return f"""You are a brand strategist. Write ONE short tagline (max 10 words)
for the following business. Language: {lang}.

BUSINESS:
- Name: {ctx['name']}
- Type: {ctx['type']}
- Location: {ctx['location'] or "n/a"}
- Amenities: {", ".join(ctx['amenities'][:6]) or "n/a"}

RULES:
- Max 10 words. No quotes. No emojis. No period at the end.
- Do not invent facts.
- Return only the tagline."""


def write_business_tagline(
    db: DBSession,
    *,
    tenant: Tenant,
    language: str = "en",
) -> dict[str, Any]:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")
    prompt = _build_tagline_prompt(tenant, language=language)
    content = _safe_ai(prompt)
    if not content:
        content = _fallback_tagline(tenant, language)
    return {"tagline": content, "language": language}


# ---------- Image keyword suggestions ----------


def suggest_image_keywords(
    tenant: Tenant,
    service: Service,
) -> dict[str, Any]:
    """Return keyword list + Unsplash search URLs.

    No external API call; Unsplash source URLs work without a key.
    """
    cfg = tenant.config or {}
    keywords: list[str] = []

    # Service type + name
    if service.type:
        keywords.append(service.type.replace("_", " "))
    if service.name:
        # take first 3 meaningful words
        words = [w for w in service.name.split() if len(w) > 2][:3]
        keywords.extend(words)

    # Tenant type + location
    if cfg.get("type"):
        keywords.append(str(cfg["type"]).replace("_", " "))
    if cfg.get("location"):
        # use last part of location (usually city)
        loc = str(cfg["location"]).split(",")[-1].strip()
        if loc:
            keywords.append(loc)

    # Dedupe (case-insensitive), preserve order
    seen = set()
    uniq: list[str] = []
    for k in keywords:
        kl = k.lower()
        if kl and kl not in seen:
            seen.add(kl)
            uniq.append(k)

    query = " ".join(uniq[:5])
    return {
        "keywords": uniq,
        "query": query,
        "unsplash_search_url": f"https://unsplash.com/s/photos/{quote_plus(query)}",
        "unsplash_source_url": f"https://source.unsplash.com/1600x900/?{quote_plus(query)}",
    }
