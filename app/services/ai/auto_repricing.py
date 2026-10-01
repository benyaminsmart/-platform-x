"""AI Auto-Repricing Live — suggest a real-time price for one service.

Phase 60 (Wave 3, Blue-Ocean B2).

Design principles:
- Numbers are computed in Python. AI writes the rationale only.
- Deterministic signals from real DB:
    * occupancy on the target date (booked / capacity)
    * bookings in the last 7 days (demand velocity)
    * days until check-in (urgency)
    * peer median price in the same category
- Suggested price is bounded:
    * floor: base_price × (1 - MAX_DOWN)   (default -20%)
    * ceil:  base_price × (1 + MAX_UP)     (default +30%)
- Never applied automatically. Owner previews and can apply manually.
- Only works when Tenant.config["auto_repricing_enabled"] is True.
- Deterministic fallback rationale always available.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from statistics import median
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.service import Service
from app.models.tenant import Tenant
from app.services.ai import service as ai_service


SUPPORTED_LANGUAGES = {"en", "ar", "fil", "hi"}
_LANGUAGE_NAMES = {
    "en": "English", "ar": "Arabic (Modern Standard Arabic)",
    "fil": "Filipino (Tagalog)", "hi": "Hindi",
}

MAX_UP = Decimal("0.30")
MAX_DOWN = Decimal("0.20")

_ACTIVE = ("pending", "confirmed", "paid")


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _tenant_category(t: Tenant) -> str:
    typ = ((t.config or {}).get("type") or "").lower()
    return typ or "other"


def _occupancy_on(db: DBSession, *, service: Service, target: date) -> tuple[int, int, float]:
    """Return (booked_units, capacity, occupancy_pct 0..100)."""
    cap = int(service.capacity) if service and service.capacity else 1
    rows = (
        db.query(Booking)
        .filter(
            Booking.service_id == service.id,
            Booking.status.in_(list(_ACTIVE)),
            Booking.check_in <= target,
        )
        .all()
    )
    booked = 0
    for b in rows:
        b_out = b.check_out or (b.check_in + timedelta(days=1))
        if b_out > target:
            booked += 1
    occ = (booked / cap * 100.0) if cap > 0 else 0.0
    return booked, cap, round(occ, 1)


def _bookings_last_7d(db: DBSession, *, tenant_id: str) -> int:
    since = datetime.now(timezone.utc) - timedelta(days=7)
    return int(
        db.query(func.count(Booking.id))
        .filter(
            Booking.tenant_id == tenant_id,
            Booking.status.in_(list(_ACTIVE)),
            Booking.created_at >= since,
        )
        .scalar() or 0
    )


def _peer_median_price(db: DBSession, *, self_tenant_id: str, category: str) -> float | None:
    """Median price of active services across peers in the same category."""
    rows = (
        db.query(Service.price, Tenant.id)
        .join(Tenant, Tenant.id == Service.tenant_id)
        .filter(
            Service.status == "active",
            Tenant.status == "active",
            Tenant.deleted_at.is_(None),
            Tenant.id != self_tenant_id,
        )
        .all()
    )
    prices: list[float] = []
    tenant_cache: dict[str, Tenant] = {}
    for price, tid in rows:
        if tid not in tenant_cache:
            t = db.query(Tenant).filter(Tenant.id == tid).one_or_none()
            if t is not None:
                tenant_cache[tid] = t
        t = tenant_cache.get(tid)
        if t is None:
            continue
        if _tenant_category(t) != category:
            continue
        try:
            prices.append(float(price))
        except (TypeError, ValueError):
            continue
    if not prices:
        return None
    return float(median(prices))


def is_enabled(tenant: Tenant) -> bool:
    return bool((tenant.config or {}).get("auto_repricing_enabled"))


def suggest_price(
    db: DBSession,
    *,
    tenant: Tenant,
    service: Service,
    target_date: date | None = None,
    language: str = "en",
) -> dict[str, Any]:
    """Return a live price suggestion for one service.

    status: 'ok' | 'disabled' | 'not_found'.
    """
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")

    if service is None or service.tenant_id != tenant.id:
        return {"status": "not_found", "provider": "fallback",
                "rationale": "", "suggested_price": None, "signals": {}}

    if not is_enabled(tenant):
        return {"status": "disabled", "provider": "fallback",
                "rationale": "Auto-Repricing is not enabled for this business.",
                "suggested_price": None, "signals": {}}

    target = target_date or (date.today() + timedelta(days=1))
    base_price = Decimal(str(service.price))

    booked, cap, occ_pct = _occupancy_on(db, service=service, target=target)
    velocity_7d = _bookings_last_7d(db, tenant_id=tenant.id)
    days_until = (target - date.today()).days
    peer_median = _peer_median_price(
        db, self_tenant_id=tenant.id, category=_tenant_category(tenant)
    )

    # Deterministic adjustment delta (fraction)
    delta = Decimal("0")
    reasons: list[str] = []

    # occupancy signal
    if occ_pct >= 80:
        delta += Decimal("0.15"); reasons.append("high occupancy")
    elif occ_pct >= 50:
        delta += Decimal("0.05"); reasons.append("moderate occupancy")
    elif occ_pct <= 20:
        delta -= Decimal("0.10"); reasons.append("low occupancy")

    # velocity signal
    if velocity_7d >= 10:
        delta += Decimal("0.10"); reasons.append("strong recent demand")
    elif velocity_7d >= 4:
        delta += Decimal("0.03"); reasons.append("steady recent demand")
    elif velocity_7d == 0:
        delta -= Decimal("0.05"); reasons.append("no recent demand")

    # urgency signal
    if days_until <= 2:
        delta += Decimal("0.10"); reasons.append("last-minute")
    elif days_until <= 7:
        delta += Decimal("0.03"); reasons.append("near-term")

    # peer signal
    if peer_median is not None and peer_median > 0:
        my = float(base_price)
        if my < peer_median * 0.85:
            delta += Decimal("0.05"); reasons.append("below peers")
        elif my > peer_median * 1.15:
            delta -= Decimal("0.05"); reasons.append("above peers")

    # clamp
    if delta > MAX_UP:
        delta = MAX_UP
    if delta < -MAX_DOWN:
        delta = -MAX_DOWN

    suggested = _round2(base_price * (Decimal("1") + delta))

    signals = {
        "base_price": str(_round2(base_price)),
        "occupancy_pct": occ_pct,
        "booked_units": booked,
        "capacity": cap,
        "bookings_7d": velocity_7d,
        "days_until": days_until,
        "peer_median": peer_median,
        "delta_pct": int((delta * Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP)),
        "reasons": reasons,
    }

    # AI rationale (grounded)
    lines = [
        f"SERVICE: {service.name} ({service.type})",
        f"BASE_PRICE: {signals['base_price']} {service.currency}",
        f"TARGET_DATE: {target.isoformat()}",
        f"OCCUPANCY: {occ_pct}% ({booked}/{cap})",
        f"BOOKINGS_7D: {velocity_7d}",
        f"DAYS_UNTIL: {days_until}",
        f"PEER_MEDIAN_PRICE: {peer_median}",
        f"DELTA_PCT: {signals['delta_pct']}",
        f"SUGGESTED_PRICE: {suggested} {service.currency}",
        "",
        "REASONS:",
    ]
    for r in reasons:
        lines.append(f"  - {r}")

    lang = _LANGUAGE_NAMES.get(language, "English")
    prompt = (
        "You are a revenue manager for Platform-X. Based ONLY on the numbers "
        "below, write a short rationale (max 3 sentences) explaining the "
        "suggested live price adjustment. Do NOT invent numbers or promises. "
        "The adjustment is informational only — the owner decides. "
        "Write in " + lang + ".\n\n"
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
        reason_txt = ", ".join(reasons) if reasons else "baseline conditions"
        rationale = (
            f"Suggested {signals['delta_pct']:+d}% adjustment "
            f"({base_price} → {suggested} {service.currency}) "
            f"based on: {reason_txt}."
        )

    return {
        "status": "ok",
        "suggested_price": float(suggested),
        "base_price": float(_round2(base_price)),
        "currency": service.currency,
        "signals": signals,
        "rationale": rationale,
        "provider": provider,
    }
