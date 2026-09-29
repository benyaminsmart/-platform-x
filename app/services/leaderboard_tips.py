"""Leaderboard AI Tips — analyze weak criteria + generate advice.

Design:
- The "weakest criteria" analysis is deterministic.
- AI is used ONLY to produce a natural-language advice text,
  grounded in the actual numbers. It never invents scores.
- If AI fails, a deterministic fallback text is returned.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.business_score import BusinessScore
from app.models.tenant import Tenant
from app.services.ai import service as ai_service
from app.services.ai.business_context import build_business_context, context_to_prompt


CRITERIA_LABELS = {
    "customer_satisfaction": "Customer Satisfaction",
    "service_quality": "Service Quality",
    "pricing_competitiveness": "Pricing Competitiveness",
    "engagement": "Engagement",
    "loyalty": "Loyalty",
}


def _weakest_criteria(row: BusinessScore, n: int = 3) -> list[dict[str, Any]]:
    """Return up to `n` criteria with lowest scores, each as a dict."""
    values = {
        "customer_satisfaction": float(row.customer_satisfaction or 0),
        "service_quality": float(row.service_quality or 0),
        "pricing_competitiveness": float(row.pricing_competitiveness or 0),
        "engagement": float(row.engagement or 0),
        "loyalty": float(row.loyalty or 0),
    }
    sorted_items = sorted(values.items(), key=lambda kv: kv[1])
    return [
        {
            "key": k,
            "label": CRITERIA_LABELS[k],
            "score": round(v, 2),
            "gap_to_100": round(100.0 - v, 2),
        }
        for k, v in sorted_items[:n]
    ]


def _next_rank_gap(row: BusinessScore, db: DBSession) -> dict[str, Any] | None:
    """If the tenant is not rank 1 in its category, return the score to beat."""
    if row.rank_in_category is None or row.rank_in_category <= 1:
        return None

    target_rank = row.rank_in_category - 1
    above = (
        db.query(BusinessScore)
        .filter(
            BusinessScore.period_start == row.period_start,
            BusinessScore.period_end == row.period_end,
            BusinessScore.category == row.category,
            BusinessScore.rank_in_category == target_rank,
        )
        .one_or_none()
    )
    if above is None:
        return None
    gap = max(0.0, round(float(above.overall_score) - float(row.overall_score), 2))
    return {
        "target_rank": target_rank,
        "target_overall_score": round(float(above.overall_score), 2),
        "gap": gap,
    }


# ---------- Prompt building ----------


_SYSTEM = """You are a growth coach for a small business on the Platform-X
marketplace. You help them improve their leaderboard score.

Rules:
- Use ONLY the numbers provided in the context and the score breakdown.
- NEVER invent scores, competitor names, or facts you do not have.
- Be direct, warm, and concrete. Max 5 short bullet points or paragraphs.
- For each weak criterion, give one specific, actionable suggestion.
- Address the business owner as "you".
"""


def _build_prompt(
    tenant: Tenant,
    row: BusinessScore,
    weakest: list[dict[str, Any]],
    next_rank: dict[str, Any] | None,
    context_text: str,
) -> str:
    lines = [_SYSTEM, "", "BUSINESS CONTEXT:", context_text, ""]
    lines.append("CURRENT SCORE:")
    lines.append(f"  overall: {round(float(row.overall_score), 2)} / 100")
    lines.append(f"  category: {row.category}")
    lines.append(f"  rank_in_category: {row.rank_in_category}")
    lines.append(f"  rank_overall: {row.rank_overall}")
    lines.append("")
    lines.append("CRITERIA SCORES:")
    for k, label in CRITERIA_LABELS.items():
        v = float(getattr(row, k) or 0)
        lines.append(f"  - {label}: {round(v, 2)}")
    lines.append("")
    lines.append("WEAKEST CRITERIA (already computed):")
    for w in weakest:
        lines.append(f"  - {w['label']} = {w['score']} (gap to 100: {w['gap_to_100']})")
    if next_rank:
        lines.append("")
        lines.append(
            f"NEXT RANK: to reach rank {next_rank['target_rank']}, "
            f"you need to beat {next_rank['target_overall_score']} "
            f"(gap: {next_rank['gap']})."
        )
    lines.append("")
    lines.append(
        "TASK: Give 3-5 concise, concrete recommendations focused on the "
        "weakest criteria above. Prioritize actions the owner can take this week."
    )
    return "\n".join(lines)


def _fallback_advice(weakest: list[dict[str, Any]], next_rank: dict[str, Any] | None) -> str:
    """Deterministic fallback if AI is unavailable."""
    if not weakest:
        return "Your score is on track. Keep providing great service."
    parts = ["Focus on these areas to improve your score:"]
    tips = {
        "customer_satisfaction": "Ask recent guests to leave reviews (rating + volume both count).",
        "service_quality": "Activate more services, diversify your offering, and complete your profile (tagline, gallery, amenities).",
        "pricing_competitiveness": "Compare your prices to the peer median and adjust toward the market.",
        "engagement": "Increase bookings and use the AI assistant to answer customer questions faster.",
        "loyalty": "Keep an active subscription and grow your paid bookings over time.",
    }
    for w in weakest:
        parts.append(f"- {w['label']} ({w['score']}/100): {tips.get(w['key'], '')}")
    if next_rank:
        parts.append(
            f"To reach rank {next_rank['target_rank']}, you need +{next_rank['gap']} points."
        )
    return "\n".join(parts)


def _safe_ai(prompt: str) -> str | None:
    try:
        result = ai_service.chat(prompt, history=[])
        content = (result or {}).get("content", "").strip()
        return content or None
    except Exception:
        return None


# ---------- Public API ----------


def generate_tips(
    db: DBSession,
    *,
    tenant: Tenant,
    row: BusinessScore,
) -> dict[str, Any]:
    """Return {'weakest': [...], 'next_rank_gap': {...}, 'advice': '...'}."""
    weakest = _weakest_criteria(row, n=3)
    next_rank = _next_rank_gap(row, db)

    ctx = build_business_context(db, tenant)
    context_text = context_to_prompt(ctx)

    prompt = _build_prompt(tenant, row, weakest, next_rank, context_text)
    advice = _safe_ai(prompt)
    if not advice:
        advice = _fallback_advice(weakest, next_rank)

    return {
        "weakest": weakest,
        "next_rank_gap": next_rank,
        "advice": advice,
    }
