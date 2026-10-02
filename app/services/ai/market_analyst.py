"""AI Market Analyst — plain-language interpretation of market insights.

Design:
- Metrics are deterministic (from market_insights service).
- AI writes ONLY the summary + advice, grounded in those metrics.
- AI must NOT invent numbers or competitor names.
- Deterministic strengths/weaknesses derived from percentiles.
"""

from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.tenant import Tenant
from app.core.logging_config import get_logger
from app.services import market_insights as mi
from app.services.ai import service as ai_service


SUPPORTED_LANGUAGES = {"en", "ar", "fil", "hi"}

_LANGUAGE_NAMES = {
    "en": "English",
    "ar": "Arabic (Modern Standard)",
    "fil": "Filipino (Tagalog)",
    "hi": "Hindi",
}

_POSITION_LABELS = {
    "avg_price": "average price",
    "rating": "customer rating",
    "service_count": "number of active services",
    "bookings_last_30d": "bookings in the last 30 days",
}



logger = get_logger(__name__)

def _safe_ai(prompt: str) -> str | None:
    try:
        result = ai_service.chat(prompt, history=[])
        return (result or {}).get("content", "").strip() or None
    except Exception:
        return None


# ---------- Deterministic highlights ----------


def highlight_strengths_and_weaknesses(
    position: dict[str, Any] | None,
) -> dict[str, list[dict[str, Any]]]:
    """Return sorted strengths and weaknesses from the tenant position."""
    strengths: list[dict[str, Any]] = []
    weaknesses: list[dict[str, Any]] = []
    if not position or not position.get("positions"):
        return {"strengths": [], "weaknesses": []}

    for key, label in _POSITION_LABELS.items():
        p = position["positions"].get(key)
        if not p:
            continue
        entry = {
            "key": key,
            "label": label,
            "value": p["value"],
            "percentile": p["percentile"],
        }
        if p["percentile"] >= 70:
            strengths.append(entry)
        elif p["percentile"] <= 30:
            weaknesses.append(entry)

    strengths.sort(key=lambda x: -x["percentile"])
    weaknesses.sort(key=lambda x: x["percentile"])
    return {"strengths": strengths, "weaknesses": weaknesses}


# ---------- Fallback ----------


def _fallback_summary(insights: dict[str, Any]) -> str:
    cat = insights.get("tenant_category") or "category"
    cohort = (insights.get("category_summary") or {}).get("cohort_size", 0)
    if cohort == 0:
        return (
            f"There are no other active businesses in the {cat} category yet. "
            "You are effectively alone in this cohort; benchmarks will improve "
            "as more businesses join."
        )
    pos = insights.get("tenant_position") or {}
    positions = pos.get("positions") or {}
    lines = [f"Your position vs {cohort} other active businesses in {cat}:"]
    for key, label in _POSITION_LABELS.items():
        p = positions.get(key)
        if not p:
            continue
        lines.append(f"  - {label}: {p['value']} (top {100 - p['percentile']:.0f}%)")
    return "\n".join(lines)


def _fallback_advice(sw: dict[str, list[dict[str, Any]]]) -> str:
    parts: list[str] = []
    if sw["weaknesses"]:
        parts.append("Focus on these areas:")
        for w in sw["weaknesses"][:3]:
            parts.append(f"  - {w['label']} (percentile {w['percentile']})")
    if sw["strengths"]:
        parts.append("Leverage these strengths in your marketing:")
        for s in sw["strengths"][:3]:
            parts.append(f"  - {s['label']} (percentile {s['percentile']})")
    if not parts:
        return "You are within the normal range across all measured dimensions. Keep it up."
    return "\n".join(parts)


# ---------- Prompt ----------


_SYSTEM = """You are a market analyst for a small business on Platform-X.

Rules:
- Ground every statement in the numbers provided. NEVER invent data.
- NEVER mention competitor names or specific businesses; refer to
  "other businesses in your category" instead.
- Be direct, warm, and short. Max 5 short paragraphs.
- Address the owner as "you"."""


def _build_prompt(
    insights: dict[str, Any],
    sw: dict[str, list[dict[str, Any]]],
    language: str,
) -> str:
    lang = _LANGUAGE_NAMES.get(language, "English")
    cat = insights.get("tenant_category")
    region = insights.get("tenant_region")
    cat_summary = insights.get("category_summary") or {}
    position = insights.get("tenant_position") or {}
    region_summary = insights.get("region_summary")

    lines = [_SYSTEM, "", f"LANGUAGE: {lang}", ""]
    lines.append(f"BUSINESS CATEGORY: {cat}")
    lines.append(f"REGION: {region or 'n/a'}")
    lines.append("")
    lines.append(f"CATEGORY COHORT SIZE: {cat_summary.get('cohort_size', 0)}")

    metrics = cat_summary.get("metrics") or {}
    for key, label in _POSITION_LABELS.items():
        q = metrics.get(key)
        if q:
            lines.append(f"{label.upper()} (peers): median={q['median']}, p25={q['p25']}, p75={q['p75']}, avg={q['avg']}")

    lines.append("")
    lines.append("YOUR POSITION (percentile among peers, 0 = lowest, 100 = highest):")
    positions = position.get("positions") or {}
    for key, label in _POSITION_LABELS.items():
        p = positions.get(key)
        if p:
            lines.append(f"  - {label}: value={p['value']}, percentile={p['percentile']}")

    if sw["strengths"]:
        lines.append("")
        lines.append("PRE-COMPUTED STRENGTHS:")
        for s in sw["strengths"]:
            lines.append(f"  - {s['label']} (percentile {s['percentile']})")

    if sw["weaknesses"]:
        lines.append("")
        lines.append("PRE-COMPUTED WEAKNESSES:")
        for w in sw["weaknesses"]:
            lines.append(f"  - {w['label']} (percentile {w['percentile']})")

    if region_summary:
        lines.append("")
        lines.append(
            f"REGION: {region} has {region_summary.get('cohort_size', 0)} peers, "
            f"avg_price={region_summary.get('avg_price')}, "
            f"median_price={region_summary.get('median_price')}"
        )

    lines.append("")
    lines.append(
        "TASK: Return a JSON object with exactly two fields:\n"
        '  "summary": a 2-4 sentence plain-language summary of where this '
        "business stands relative to peers (max 400 chars).\n"
        '  "advice": 3-5 short, concrete recommendations (max 700 chars).\n'
        "Return ONLY the JSON, no extra text."
    )
    return "\n".join(lines)


# ---------- Public ----------


def interpret_market(
    db: DBSession,
    tenant: Tenant,
    *,
    language: str = "en",
) -> dict[str, Any]:
    """Return {'metrics', 'strengths', 'weaknesses', 'summary', 'advice', 'provider'}."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")

    insights = mi.market_insights(db, tenant)
    sw = highlight_strengths_and_weaknesses(insights.get("tenant_position"))

    prompt = _build_prompt(insights, sw, language)
    raw = _safe_ai(prompt)

    summary: str | None = None
    advice: str | None = None
    provider = "fallback"

    if raw:
        import json as _json

        def _try_parse(s: str) -> dict[str, Any] | None:
            try:
                return _json.loads(s)
            except Exception:
                logger.warning("Market analyst JSON extraction failed", exc_info=True)
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
                        try:
                            return _json.loads(s[start : i + 1])
                        except Exception:
                            return None
            return None

        def _as_text(v) -> str:
            """Coerce a value (str, list[str], dict) into a plain string."""
            if v is None:
                return ""
            if isinstance(v, str):
                return v
            if isinstance(v, list):
                return "\n".join(_as_text(x) for x in v if x is not None)
            if isinstance(v, dict):
                return "\n".join(f"{k}: {_as_text(val)}" for k, val in v.items())
            return str(v)

        parsed = _try_parse(raw)
        if parsed and isinstance(parsed.get("summary"), (str, list, dict)):
            summary = _as_text(parsed.get("summary")).strip()[:500]
            advice = _as_text(parsed.get("advice")).strip()[:1200] or None
            if summary:
                provider = "ai"

    if not summary:
        summary = _fallback_summary(insights)
    if not advice:
        advice = _fallback_advice(sw)

    return {
        "metrics": insights,
        "strengths": sw["strengths"],
        "weaknesses": sw["weaknesses"],
        "summary": summary,
        "advice": advice,
        "provider": provider,
    }
