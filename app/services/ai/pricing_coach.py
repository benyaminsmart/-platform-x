"""Pricing Coach — deterministic metrics + AI-generated advice.

Design principle (Tech Lead decision):
- ALL numeric analysis is computed in Python from real DB data.
- The AI NEVER invents numbers. It only interprets and advises.
- Every endpoint returns two sections: `metrics` (deterministic) and
  `advice` (AI text, grounded in metrics).

This preserves trust: business owners see real numbers, not hallucinations.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.tenant import Tenant
from app.services.ai import service as ai_service
from app.services.ai.business_context import build_business_context, context_to_prompt


# ---------- Analysis ----------


def analyze_pricing(db: DBSession, tenant: Tenant) -> dict[str, Any]:
    """Return deterministic pricing metrics + AI advice.

    Metrics include per-type pricing stats and position vs peer cohort.
    """
    ctx = build_business_context(db, tenant)
    p = ctx["portfolio"]
    b = ctx["benchmark"]

    metrics: dict[str, Any] = {
        "dominant_type": ctx["tenant"]["dominant_type"],
        "active_services": p["active_services"],
        "total_services": p["total_services"],
        "pricing_by_type": p["pricing_by_type"],
        "benchmark": b,
    }

    # Add per-type "position" labels (deterministic)
    positions: dict[str, str] = {}
    if b.get("cohort_size") and b.get("avg_price") is not None:
        for typ, stats in p["pricing_by_type"].items():
            if typ != b["cohort_type"]:
                continue
            own_avg = stats["avg"]
            cohort_avg = b["avg_price"]
            if cohort_avg <= 0:
                continue
            delta_pct = ((own_avg - cohort_avg) / cohort_avg) * 100
            if delta_pct <= -10:
                label = "below_market"
            elif delta_pct >= 10:
                label = "above_market"
            else:
                label = "at_market"
            positions[typ] = label
    metrics["position_by_type"] = positions

    # AI advice grounded in metrics
    prompt = _build_pricing_prompt(ctx)
    advice = _safe_ai(prompt)

    return {"metrics": metrics, "advice": advice}


def suggest_pricing(db: DBSession, tenant: Tenant) -> dict[str, Any]:
    """Return deterministic per-type price suggestions + AI reasoning.

    The suggestion algorithm is rule-based (transparent):
    - If tenant is below market by >10%: suggest +5% toward cohort avg
    - If tenant is above market by >10%: suggest -5% toward cohort avg
    - If at market: suggest hold, unless 30d trend is strongly negative
    - Always keep the change bounded to +/-10% per suggestion
    """
    ctx = build_business_context(db, tenant)
    p = ctx["portfolio"]
    b = ctx["benchmark"]
    r30 = ctx["rolling_30d"]

    suggestions: list[dict[str, Any]] = []

    if b.get("cohort_size") and b.get("avg_price") is not None:
        cohort_avg = b["avg_price"]
        for typ, stats in p["pricing_by_type"].items():
            if typ != b["cohort_type"]:
                continue
            own_avg = stats["avg"]
            if own_avg <= 0 or cohort_avg <= 0:
                continue
            delta_pct = ((own_avg - cohort_avg) / cohort_avg) * 100

            change_pct = 0.0
            reason = ""
            if delta_pct <= -10:
                change_pct = min(5.0, -delta_pct / 2)
                reason = (
                    f"Your average is {abs(round(delta_pct,1))}% below the anonymized "
                    f"peer cohort. A modest increase moves you toward market."
                )
            elif delta_pct >= 10:
                change_pct = -min(5.0, delta_pct / 2)
                reason = (
                    f"Your average is {round(delta_pct,1)}% above the anonymized "
                    f"peer cohort. A modest decrease may improve conversion."
                )
            else:
                # at market — factor in 30d trend
                growth = r30.get("growth_pct")
                if growth is not None and growth <= -20:
                    change_pct = -3.0
                    reason = (
                        f"Pricing is at market, but 30-day bookings dropped "
                        f"{growth}%. A small reduction could recover demand."
                    )
                elif growth is not None and growth >= 20:
                    change_pct = 3.0
                    reason = (
                        f"Pricing is at market, and 30-day bookings grew "
                        f"{growth}%. A small increase may capture value."
                    )
                else:
                    change_pct = 0.0
                    reason = "Pricing is at market and demand is stable. Hold."

            new_avg = round(own_avg * (1 + change_pct / 100), 2)
            suggestions.append({
                "type": typ,
                "current_avg_aed": round(own_avg, 2),
                "cohort_avg_aed": round(cohort_avg, 2),
                "delta_vs_cohort_pct": round(delta_pct, 1),
                "suggested_change_pct": round(change_pct, 1),
                "suggested_new_avg_aed": new_avg,
                "reason": reason,
            })

    if not suggestions:
        suggestions.append({
            "type": None,
            "note": (
                "Not enough peer data yet to suggest pricing. "
                "The peer cohort for your dominant category has fewer than 1 "
                "other active business on the platform."
            ),
        })

    # AI adds qualitative advice on top of the deterministic suggestions
    prompt = _build_suggest_prompt(ctx, suggestions)
    advice = _safe_ai(prompt)

    return {
        "metrics": {
            "dominant_type": ctx["tenant"]["dominant_type"],
            "benchmark": b,
            "rolling_30d": r30,
            "suggestions": suggestions,
        },
        "advice": advice,
    }


def forecast_demand(db: DBSession, tenant: Tenant, days: int = 30) -> dict[str, Any]:
    """Return a deterministic 30-day demand forecast + AI interpretation.

    Method (transparent):
    - Weekly average from last 30 days
    - Adjust by rolling_30d growth rate if available
    - Clamp to non-negative
    - Provide low/expected/high band (±25%)
    """
    days = max(7, min(90, int(days)))
    ctx = build_business_context(db, tenant)
    r30 = ctx["rolling_30d"]
    m = ctx["monthly"]

    last_30 = r30["bookings_last_30d"]
    weekly_avg = last_30 / (30 / 7)  # bookings per week

    growth = r30.get("growth_pct")
    if growth is None:
        growth_factor = 1.0
        growth_note = "No prior period data; assuming flat."
    else:
        growth_factor = 1.0 + max(-0.5, min(0.5, growth / 100.0))
        growth_note = f"Applied 30d growth factor of {round(growth,1)}%."

    expected = max(0.0, weekly_avg * growth_factor * (days / 7.0))

    forecast = {
        "days": days,
        "weekly_avg_last_30d": round(weekly_avg, 2),
        "growth_pct_applied": growth if growth is not None else None,
        "growth_note": growth_note,
        "expected_bookings": round(expected, 1),
        "low_bookings": round(expected * 0.75, 1),
        "high_bookings": round(expected * 1.25, 1),
        "revenue_this_month_aed": m["this_month"]["revenue_aed"],
        "revenue_prev_month_aed": m["prev_month"]["revenue_aed"],
        "revenue_growth_pct": m.get("revenue_growth_pct"),
    }

    prompt = _build_forecast_prompt(ctx, forecast)
    advice = _safe_ai(prompt)

    return {"metrics": forecast, "advice": advice}


def market_insights(db: DBSession, tenant: Tenant) -> dict[str, Any]:
    """Return anonymized platform-wide market insights for the tenant's category.

    Never reveals peer identity or exact peer revenue.
    """
    ctx = build_business_context(db, tenant)
    b = ctx["benchmark"]
    p = ctx["portfolio"]

    metrics: dict[str, Any] = {
        "dominant_type": ctx["tenant"]["dominant_type"],
        "cohort_size": b.get("cohort_size", 0),
        "cohort_avg_price_aed": b.get("avg_price"),
        "cohort_median_price_aed": b.get("median_price"),
        "your_avg_price_aed": (
            p["pricing_by_type"].get(b.get("cohort_type"), {}).get("avg")
            if b.get("cohort_type") else None
        ),
        "your_position_pct": b.get("tenant_price_vs_cohort_pct"),
    }

    prompt = _build_insights_prompt(ctx)
    advice = _safe_ai(prompt)

    return {"metrics": metrics, "advice": advice}


# ---------- AI prompt builders ----------


_BASE_SYSTEM = """You are an expert pricing and revenue advisor for small
hospitality and travel businesses on the Platform-X marketplace.

Rules:
- ALWAYS ground your advice in the numbers provided in the context block.
- NEVER invent numbers, competitor names, or market data you do not have.
- If the data is insufficient, say so plainly.
- Be direct, concrete, and short (max 5 short paragraphs).
- Address the business owner as "you".
- Currency is AED unless stated otherwise.
"""


def _build_pricing_prompt(ctx: dict[str, Any]) -> str:
    return (
        _BASE_SYSTEM
        + "\n\nContext:\n"
        + context_to_prompt(ctx)
        + "\n\nTask: Analyze the current pricing. Point out 2-3 concrete "
        + "strengths and 2-3 concrete risks based strictly on the numbers above. "
        + "Do not suggest specific new prices; the platform provides those."
    )


def _build_suggest_prompt(ctx: dict[str, Any], suggestions: list[dict[str, Any]]) -> str:
    import json as _json
    sugg_text = _json.dumps(suggestions, ensure_ascii=False, indent=2)
    return (
        _BASE_SYSTEM
        + "\n\nContext:\n"
        + context_to_prompt(ctx)
        + "\n\nDeterministic platform suggestions (already computed):\n"
        + sugg_text
        + "\n\nTask: Explain the rationale for these suggestions to the owner "
        + "in plain language. Warn about trade-offs. Max 4 short paragraphs."
    )


def _build_forecast_prompt(ctx: dict[str, Any], forecast: dict[str, Any]) -> str:
    import json as _json
    f_text = _json.dumps(forecast, ensure_ascii=False, indent=2)
    return (
        _BASE_SYSTEM
        + "\n\nContext:\n"
        + context_to_prompt(ctx)
        + "\n\nDeterministic forecast (already computed):\n"
        + f_text
        + "\n\nTask: Interpret this forecast for the owner. Highlight what it "
        + "means for staffing, inventory, and marketing over the next "
        + f"{forecast['days']} days. Max 4 short paragraphs."
    )


def _build_insights_prompt(ctx: dict[str, Any]) -> str:
    return (
        _BASE_SYSTEM
        + "\n\nContext:\n"
        + context_to_prompt(ctx)
        + "\n\nTask: Provide 3 concrete market insights for this business based "
        + "ONLY on the anonymized peer benchmark shown above. Do not invent "
        + "competitor names or specific peer businesses. Max 4 short paragraphs."
    )


# ---------- AI wrapper ----------


def _safe_ai(prompt: str) -> str:
    """Call AI, catch any failure, return a safe fallback string."""
    try:
        result = ai_service.chat(prompt, history=[])
        content = (result or {}).get("content", "").strip()
        if not content:
            return "AI advice unavailable right now. The metrics above are live."
        return content
    except Exception:
        return "AI advice unavailable right now. The metrics above are live."
