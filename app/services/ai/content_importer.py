"""AI Content Importer — parse free-text menus/room lists into services.

Design:
- AI extracts structured data from raw text (menus, room lists, packages).
- AI NEVER invents prices: if a price is not present, price is None.
- Deterministic fallback: each non-empty line becomes a simple candidate.
- Saving is a separate step; preview does not touch the DB.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.service import Service
from app.models.tenant import Tenant
from app.services.ai import service as ai_service


SUPPORTED_SERVICE_TYPES = {
    "room", "table", "treatment", "event", "package", "flight",
    "menu_item", "ticket", "tour", "activity", "other",
}

MAX_CANDIDATES = 100
MAX_TEXT_LEN = 8000


# ---------- Helpers ----------


def _safe_ai(prompt: str) -> str | None:
    try:
        result = ai_service.chat(prompt, history=[])
        content = (result or {}).get("content", "").strip()
        return content or None
    except Exception:
        return None


def _parse_price(s: Any) -> Decimal | None:
    if s is None:
        return None
    if isinstance(s, (int, float, Decimal)):
        try:
            return Decimal(str(s))
        except InvalidOperation:
            return None
    if not isinstance(s, str):
        return None
    # Extract first number-like token (with optional leading minus)
    m = re.search(r"(-?\d+(?:[.,]\d{1,2})?)", s.replace(",", ""))
    if not m:
        return None
    try:
        return Decimal(m.group(1))
    except InvalidOperation:
        return None


def _clean_str(s: Any, max_len: int = 200) -> str | None:
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    return s[:max_len]


# ---------- Fallback parser ----------


def _fallback_parse(text: str, default_type: str) -> list[dict[str, Any]]:
    """Very simple: each non-empty line -> one candidate.

    Tries to split on ' - ' or ':' to detect a trailing price.
    """
    candidates: list[dict[str, Any]] = []
    for raw in text.splitlines():
        line = raw.strip(" \t•-*")
        if not line or len(line) < 2:
            continue
        name = line
        price: Decimal | None = None
        # Try "Name - 100" or "Name: 100"
        for sep in (" - ", " – ", ": "):
            if sep in line:
                left, right = line.split(sep, 1)
                p = _parse_price(right)
                if p is not None:
                    name = left.strip()
                    price = p
                    break
        # Try trailing number "Room 200"
        if price is None:
            m = re.search(r"\s+(\d+(?:[.,]\d{1,2})?)\s*(?:aed|usd|eur|$)?\s*$", line, re.IGNORECASE)
            if m:
                p = _parse_price(m.group(1))
                if p is not None:
                    price = p
                    name = line[: m.start()].strip()

        candidates.append({
            "name": name[:200] or line[:200],
            "type": default_type,
            "description": None,
            "price": str(price) if price is not None else None,
            "currency": "AED",
            "capacity": None,
            "attributes": {},
        })
        if len(candidates) >= MAX_CANDIDATES:
            break
    return candidates


# ---------- AI parser ----------


def _build_prompt(text: str, default_type: str, language: str) -> str:
    types_str = ", ".join(sorted(SUPPORTED_SERVICE_TYPES))
    return f"""You are a data extraction assistant for Platform-X.

TASK: Read the raw text below and extract a list of services (rooms, menu
items, tours, packages, etc.).

OUTPUT FORMAT: Return ONLY a valid JSON object, no markdown, no explanations.

The JSON must be: {{"candidates": [ ... ]}}

Each candidate must have exactly these fields:
- name: string (required, short, max 120 chars)
- type: string (one of: {types_str})
- description: string or null (short, max 300 chars, do NOT invent)
- price: number or null (ONLY if a price appears in the text; never invent)
- currency: string (default "AED" if not clear)
- capacity: integer or null (only if present in text)
- attributes: object with key=value pairs found (e.g. {{"view": "sea"}})

RULES:
- Do NOT invent prices, amenities, or descriptions that are not in the text.
- If a price is not in the text, set price to null.
- Keep names short and clean.
- Return AT MOST {MAX_CANDIDATES} candidates.
- If you cannot extract anything, return {{"candidates": []}}.

DEFAULT TYPE for ambiguous items: {default_type}
PREFERRED LANGUAGE for names/descriptions: {language}

RAW TEXT:
\"\"\"
{text}
\"\"\"
"""


def _extract_json(s: str) -> dict[str, Any] | None:
    """Find the first {...} JSON object in a string."""
    # Try direct parse
    try:
        return json.loads(s)
    except Exception:
        pass
    # Find balanced braces
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                chunk = s[start : i + 1]
                try:
                    return json.loads(chunk)
                except Exception:
                    return None
    return None


def _normalize_candidate(raw: dict[str, Any], default_type: str) -> dict[str, Any] | None:
    name = _clean_str(raw.get("name"), max_len=120)
    if not name:
        return None
    rtype = _clean_str(raw.get("type"), max_len=50) or default_type
    if rtype not in SUPPORTED_SERVICE_TYPES:
        rtype = default_type
    desc = _clean_str(raw.get("description"), max_len=300)
    price = _parse_price(raw.get("price"))
    currency = _clean_str(raw.get("currency"), max_len=10) or "AED"
    capacity = raw.get("capacity")
    try:
        capacity = int(capacity) if capacity is not None and capacity != "" else None
    except (TypeError, ValueError):
        capacity = None
    attrs = raw.get("attributes")
    if not isinstance(attrs, dict):
        attrs = {}
    # Only keep primitive values
    attrs = {str(k)[:50]: (str(v)[:200] if v is not None else "") for k, v in list(attrs.items())[:10]}

    return {
        "name": name,
        "type": rtype,
        "description": desc,
        "price": str(price) if price is not None else None,
        "currency": currency,
        "capacity": capacity,
        "attributes": attrs,
    }


# ---------- Public API ----------


def parse_services_from_text(
    db: DBSession,
    *,
    tenant: Tenant,
    text: str,
    default_type: str = "room",
    language: str = "en",
) -> dict[str, Any]:
    """Parse free text into candidate services. Does NOT touch the DB."""
    if not text or not text.strip():
        raise ValueError("text is empty")
    if len(text) > MAX_TEXT_LEN:
        text = text[:MAX_TEXT_LEN]
    if default_type not in SUPPORTED_SERVICE_TYPES:
        default_type = "room"

    prompt = _build_prompt(text, default_type, language)
    raw = _safe_ai(prompt)

    provider = "ai"
    candidates: list[dict[str, Any]] = []

    if raw:
        parsed = _extract_json(raw)
        if parsed and isinstance(parsed.get("candidates"), list):
            for item in parsed["candidates"][:MAX_CANDIDATES]:
                if not isinstance(item, dict):
                    continue
                c = _normalize_candidate(item, default_type)
                if c:
                    candidates.append(c)

    if not candidates:
        provider = "fallback"
        candidates = _fallback_parse(text, default_type)

    return {
        "candidates": candidates,
        "provider": provider,
        "count": len(candidates),
    }


def bulk_create_services(
    db: DBSession,
    *,
    tenant: Tenant,
    candidates: list[dict[str, Any]],
    user_id: str | None = None,
) -> dict[str, Any]:
    """Persist a list of candidates as services.

    Validation: each candidate must have a name. Price must be >= 0 if present.
    """
    created_ids: list[str] = []
    skipped: list[dict[str, Any]] = []

    for raw in candidates[:MAX_CANDIDATES]:
        norm = _normalize_candidate(raw, "room")
        if not norm:
            skipped.append({"reason": "missing name", "raw": raw})
            continue
        price = _parse_price(norm["price"])
        if price is not None and price < 0:
            skipped.append({"reason": "negative price", "name": norm["name"]})
            continue

        svc = Service(
            tenant_id=tenant.id,
            type=norm["type"],
            name=norm["name"],
            description=norm["description"],
            price=price if price is not None else Decimal("0"),
            currency=norm["currency"] or "AED",
            capacity=norm["capacity"],
            attributes=norm["attributes"],
            image_urls=[],
            status="active",
            display_order=0,
        )
        db.add(svc)
        db.flush()
        created_ids.append(svc.id)

    db.commit()

    return {
        "created": len(created_ids),
        "skipped": skipped,
        "service_ids": created_ids,
    }
