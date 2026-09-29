"""Revenue forecasting — deterministic numbers + optional AI interpretation.

Method (transparent):
1. Daily revenue average over the last 30 days (weight 0.7)
2. Daily revenue average over the last 90 days (weight 0.3)
3. Weighted average = 0.7 * a30 + 0.3 * a90
4. Apply growth factor derived from last-30 vs prev-30 window
5. Forecast = weighted_avg * days * growth_factor
6. Low/High band = +/-20%

Only PAID bookings count (payment_status == "paid").
Cancelled bookings are excluded.
"""

from datetime import date, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.tenant import Tenant
from app.services.ai import service as ai_service
from app.services.ai.business_context import build_business_context, context_to_prompt


_EXCLUDED_STATUSES = ("cancelled",)
DEFAULT_CURRENCY = "AED"


def _round2(v: float) -> float:
    return round(float(v), 2)


def _revenue_in_window(db, tenant, *, from_date, to_date) -> float:
    v = (
        db.query(func.coalesce(func.sum(Booking.total_amount), 0))
        .filter(
            Booking.tenant_id == tenant.id,
            Booking.status.notin_(_EXCLUDED_STATUSES),
            Booking.payment_status == "paid",
            Booking.check_in >= from_date,
            Booking.check_in < to_date,
        )
        .scalar()
        or 0
    )
    return float(v)


def _daily_average(db, tenant, *, today, days) -> float:
    if days <= 0:
        return 0.0
    to_date = today + timedelta(days=1)
    from_date = to_date - timedelta(days=days)
    return _revenue_in_window(db, tenant, from_date=from_date, to_date=to_date) / days


def forecast_revenue(db, tenant, *, days: int = 30, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    days = max(7, min(int(days), 180))

    a30 = _daily_average(db, tenant, today=today, days=30)
    a90 = _daily_average(db, tenant, today=today, days=90)

    to_cur = today + timedelta(days=1)
    from_cur = to_cur - timedelta(days=30)
    from_prev = from_cur - timedelta(days=30)

    rev_cur = _revenue_in_window(db, tenant, from_date=from_cur, to_date=to_cur)
    rev_prev = _revenue_in_window(db, tenant, from_date=from_prev, to_date=from_cur)

    raw_growth = (rev_cur - rev_prev) / rev_prev if rev_prev > 0 else 0.0
    growth_factor = 1.0 + max(-0.5, min(0.5, raw_growth))

    weighted_daily_avg = 0.7 * a30 + 0.3 * a90
    expected = weighted_daily_avg * days * growth_factor

    note = None
    if weighted_daily_avg == 0:
        note = "no paid bookings in the recent window; forecast is zero"

    return {
        "daily_avg_last_30d": _round2(a30),
        "daily_avg_last_90d": _round2(a90),
        "weighted_daily_avg": _round2(weighted_daily_avg),
        "revenue_last_30d": _round2(rev_cur),
        "revenue_prev_30d": _round2(rev_prev),
        "raw_growth_pct": _round2(raw_growth * 100),
        "growth_factor_applied": _round2(growth_factor),
        "forecast_days": days,
        "expected_revenue": _round2(expected),
        "low_revenue": _round2(expected * 0.8),
        "high_revenue": _round2(expected * 1.2),
        "currency": DEFAULT_CURRENCY,
        "note": note,
    }


_SYSTEM = (
    "You are a revenue advisor for a small business on Platform-X. "
    "Interpret the forecast below in plain language. Ground every claim in the "
    "numbers provided. Never invent data. Max 4 short paragraphs. "
    "Address the owner as 'you'. Currency is AED."
)


def _safe_ai(prompt: str) -> str | None:
    try:
        result = ai_service.chat(prompt, history=[])
        return (result or {}).get("content", "").strip() or None
    except Exception:
        return None


def _fallback_advice(metrics: dict[str, Any]) -> str:
    if metrics["weighted_daily_avg"] <= 0:
        return (
            "Not enough paid bookings in the recent window to forecast. "
            "Focus on getting your first repeat bookings."
        )
    direction = "growing" if metrics["raw_growth_pct"] > 0 else "flat or declining"
    return (
        f"Your recent daily revenue is ~{metrics['weighted_daily_avg']} AED "
        f"(last-30 avg {metrics['daily_avg_last_30d']}, last-90 avg {metrics['daily_avg_last_90d']}). "
        f"The last 30 days are {direction} ({metrics['raw_growth_pct']}% vs the prior 30). "
        f"For the next {metrics['forecast_days']} days, expect around "
        f"{metrics['expected_revenue']} AED (range "
        f"{metrics['low_revenue']}-{metrics['high_revenue']})."
    )


def forecast_with_advice(db, tenant, *, days: int = 30, today: date | None = None) -> dict[str, Any]:
    metrics = forecast_revenue(db, tenant, days=days, today=today)
    ctx = build_business_context(db, tenant)
    context_text = context_to_prompt(ctx)

    prompt = (
        _SYSTEM
        + "\n\nCONTEXT:\n" + context_text
        + "\n\nFORECAST METRICS (deterministic):\n"
        + "\n".join(f"  - {k}: {v}" for k, v in metrics.items())
        + "\n\nTASK: Interpret this forecast. Highlight what it means for the next "
        + f"{metrics['forecast_days']} days and give 2-3 concrete suggestions."
    )
    advice = _safe_ai(prompt) or _fallback_advice(metrics)
    return {"metrics": metrics, "advice": advice}
