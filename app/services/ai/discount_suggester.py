"""AI Discount Suggester — recommend discounts per segment.

Design principle (Tech Lead decision):
- Discount percentages are FIXED platform policy, not AI-generated.
- AI only writes the *rationale* text, grounded in the real numbers.
- This avoids the AI inventing aggressive discounts that hurt the business.

Policy table (platform-enforced caps):
  segment            | pct  | days | reason
  -------------------+------+------+------------------------------------
  inactive_90d       | 15%  | 14   | win back inactive guests
  loyalty_gold_plus  | 10%  | 30   | loyalty perk
  new_30d            | 10%  | 21   | convert first-timers
  high_value         | 12%  | 14   | VIP recognition
  past_bookers       |  8%  | 21   | gentle reactivation
  all                |  5%  | 14   | base fallback
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.tenant import Tenant
from app.services import marketing as marketing_service
from app.services.ai import service as ai_service
from app.services.ai.business_context import build_business_context, context_to_prompt


SUPPORTED_LANGUAGES = {"en", "ar", "fil", "hi"}
MAX_DISCOUNT_PCT = 20.0

_LANGUAGE_NAMES = {
    "en": "English", "ar": "Arabic (Modern Standard)",
    "fil": "Filipino (Tagalog)", "hi": "Hindi",
}


POLICY: dict[str, dict[str, Any]] = {
    "inactive_90d": {"pct": 15.0, "days": 14, "goal": "win back inactive guests"},
    "loyalty_gold_plus": {"pct": 10.0, "days": 30, "goal": "loyalty perk for top tier"},
    "new_30d": {"pct": 10.0, "days": 21, "goal": "convert first-time guests"},
    "high_value": {"pct": 12.0, "days": 14, "goal": "VIP recognition"},
    "past_bookers": {"pct": 8.0, "days": 21, "goal": "gentle reactivation"},
    "all": {"pct": 5.0, "days": 14, "goal": "broad base offer"},
}


def _safe_ai(prompt: str) -> str | None:
    try:
        result = ai_service.chat(prompt, history=[])
        return (result or {}).get("content", "").strip() or None
    except Exception:
        return None


def _estimate_revenue_impact(audience: int, avg_booking: float, discount_pct: float) -> dict[str, Any]:
    """Very rough deterministic estimate.

    Assumption (documented):
      - 15% of the audience will act on the offer.
      - Average order value = avg_booking (from context).
      - Revenue impact is bounded by the platform cap.
    """
    conversion_assumption = 0.15
    expected_orders = max(0.0, audience * conversion_assumption)
    gross = expected_orders * avg_booking
    discount_value = gross * (discount_pct / 100.0)
    return {
        "expected_orders": round(expected_orders, 1),
        "gross_revenue_aed": round(gross, 2),
        "discount_value_aed": round(discount_value, 2),
        "net_after_discount_aed": round(gross - discount_value, 2),
        "conversion_assumption": conversion_assumption,
    }


def _fallback_reason(segment: str, policy: dict[str, Any], audience: int) -> str:
    return (
        f"{policy['goal'].capitalize()} ({audience} guests in this segment). "
        f"Suggested {policy['pct']}% off for {policy['days']} days."
    )


def _build_prompt(
    tenant: Tenant,
    segment: str,
    policy: dict[str, Any],
    audience: int,
    impact: dict[str, Any],
    context_text: str,
    language: str,
) -> str:
    lang = _LANGUAGE_NAMES.get(language, "English")
    return f"""You are a growth advisor for a small business on Platform-X.

CONTEXT:
{context_text}

SEGMENT: {segment} ({audience} customers)
PLATFORM POLICY (fixed, do NOT change): {policy['pct']}% discount for {policy['days']} days
GOAL: {policy['goal']}

DETERMINISTIC IMPACT ESTIMATE:
- expected orders: {impact['expected_orders']}
- gross revenue: {impact['gross_revenue_aed']} AED
- discount value: {impact['discount_value_aed']} AED
- net after discount: {impact['net_after_discount_aed']} AED

TASK: Write a short rationale (2-3 sentences) in {lang} explaining why this
discount makes sense for this segment.

RULES:
- Do NOT invent different discount percentages or durations (they are fixed).
- Reference the impact estimate numbers above.
- Be direct and practical. No emojis. Max 3 sentences.
- Return ONLY the rationale text."""


def suggest_discounts(
    db: DBSession,
    *,
    tenant: Tenant,
    language: str = "en",
    segment_filter: list[str] | None = None,
) -> dict[str, Any]:
    """Return {'suggestions': [...], 'provider': 'ai'|'fallback'}."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")

    seg_data = marketing_service.segment_customers(db, tenant)
    segments = seg_data["segments"]

    # Build business context for avg booking
    ctx = build_business_context(db, tenant)
    avg_booking = float(
        (ctx.get("performance") or {}).get("avg_booking_value_aed") or 0.0
    ) or 500.0  # safe default if no paid bookings yet

    context_text = context_to_prompt(ctx)

    # Order matters (priority)
    order = ["inactive_90d", "high_value", "loyalty_gold_plus", "new_30d", "past_bookers", "all"]

    suggestions: list[dict[str, Any]] = []
    provider = "fallback"

    for seg in order:
        if segment_filter and seg not in segment_filter:
            continue
        audience = int(segments.get(seg, {}).get("count", 0))
        if audience == 0 and seg != "all":
            continue
        policy = POLICY[seg]
        pct = min(policy["pct"], MAX_DISCOUNT_PCT)
        impact = _estimate_revenue_impact(audience, avg_booking, pct)

        prompt = _build_prompt(
            tenant, seg, {**policy, "pct": pct}, audience, impact, context_text, language
        )
        reason = _safe_ai(prompt)
        if not reason:
            reason = _fallback_reason(seg, {**policy, "pct": pct}, audience)
        else:
            provider = "ai"

        suggestions.append({
            "segment": seg,
            "discount_pct": pct,
            "duration_days": policy["days"],
            "goal": policy["goal"],
            "estimated_audience": audience,
            "estimated_impact": impact,
            "reason": reason,
        })

    # If nothing selected (all empty except 'all'), keep 'all'
    if not suggestions:
        policy = POLICY["all"]
        suggestions.append({
            "segment": "all",
            "discount_pct": policy["pct"],
            "duration_days": policy["days"],
            "goal": policy["goal"],
            "estimated_audience": 0,
            "estimated_impact": _estimate_revenue_impact(0, avg_booking, policy["pct"]),
            "reason": _fallback_reason("all", policy, 0),
        })

    return {"suggestions": suggestions, "provider": provider}
