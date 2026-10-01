"""AI Deep Peer Benchmark — compare a tenant against anonymized peers.

Phase 52 (Wave 2, Blue-Ocean B12).

Design:
- Cohort = active tenants in the same category (config.type), excluding self.
- For each metric, compute peer median and self value, then delta %.
- Metrics:
    avg_price       (mean price of active services)
    rating          (config.rating, 0..5)
    occupancy_30d   (booked nights / (capacity * window days), 0..1 → %)
    bookings_30d    (count, non-cancelled)
    services_count  (active services)
- Never exposes peer identity. Only aggregates.
- AI writes ONE short interpretation line per metric, grounded in numbers.
- Deterministic fallback always available.
"""

from __future__ import annotations

from datetime import date, timedelta
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

_EXCLUDED_STATUSES = ("cancelled",)


def _round2(v: float) -> float:
    return round(float(v), 2)


def _pct_delta(self_v: float, peer_v: float) -> float | None:
    if peer_v == 0:
        return None
    return _round2(((self_v - peer_v) / peer_v) * 100)


def _tenant_category(t: Tenant) -> str:
    cfg = t.config or {}
    typ = (cfg.get("type") or "").lower()
    return typ or "other"


def _services_count(db: DBSession, tenant_id: str) -> int:
    return int(
        db.query(func.count(Service.id))
        .filter(Service.tenant_id == tenant_id, Service.status == "active")
        .scalar() or 0
    )


def _avg_price(db: DBSession, tenant_id: str) -> float | None:
    row = (
        db.query(func.avg(Service.price))
        .filter(Service.tenant_id == tenant_id, Service.status == "active")
        .scalar()
    )
    return float(row) if row is not None else None


def _bookings_30d(db: DBSession, tenant_id: str, *, today: date) -> int:
    from_d = today - timedelta(days=30)
    return int(
        db.query(func.count(Booking.id))
        .filter(
            Booking.tenant_id == tenant_id,
            Booking.status.notin_(_EXCLUDED_STATUSES),
            Booking.check_in >= from_d,
        )
        .scalar() or 0
    )


def _booked_nights_30d(db: DBSession, tenant_id: str, *, today: date) -> int:
    from_d = today - timedelta(days=30)
    rows = (
        db.query(Booking.check_in, Booking.check_out)
        .filter(
            Booking.tenant_id == tenant_id,
            Booking.status.notin_(_EXCLUDED_STATUSES),
            Booking.check_in >= from_d,
        )
        .all()
    )
    total = 0
    for ci, co in rows:
        if ci is None:
            continue
        co = co or (ci + timedelta(days=1))
        total += max(1, (co - ci).days)
    return total


def _capacity_30d(db: DBSession, tenant_id: str) -> int:
    total_cap = (
        db.query(func.sum(Service.capacity))
        .filter(Service.tenant_id == tenant_id, Service.status == "active",
                Service.capacity.isnot(None))
        .scalar()
    )
    cap = int(total_cap or 0)
    return cap * 30


def _occupancy_30d(db: DBSession, tenant_id: str, *, today: date) -> float | None:
    cap = _capacity_30d(db, tenant_id)
    if cap <= 0:
        return None
    return _booked_nights_30d(db, tenant_id, today=today) / cap * 100.0


def _rating(t: Tenant) -> float | None:
    cfg = t.config or {}
    r = cfg.get("rating")
    try:
        return float(r) if r is not None else None
    except (TypeError, ValueError):
        return None


def _peer_metrics(db: DBSession, *, self_tenant: Tenant, today: date) -> dict[str, list[float]]:
    category = _tenant_category(self_tenant)
    peers = (
        db.query(Tenant)
        .filter(
            Tenant.id != self_tenant.id,
            Tenant.status == "active",
            Tenant.deleted_at.is_(None),
        )
        .all()
    )
    peers = [p for p in peers if _tenant_category(p) == category]

    out: dict[str, list[float]] = {
        "avg_price": [], "rating": [], "occupancy_30d": [],
        "bookings_30d": [], "services_count": [],
    }
    for p in peers:
        ap = _avg_price(db, p.id)
        if ap is not None:
            out["avg_price"].append(ap)
        r = _rating(p)
        if r is not None:
            out["rating"].append(r)
        occ = _occupancy_30d(db, p.id, today=today)
        if occ is not None:
            out["occupancy_30d"].append(occ)
        out["bookings_30d"].append(float(_bookings_30d(db, p.id, today=today)))
        out["services_count"].append(float(_services_count(db, p.id)))
    return out


def _metric_block(
    name: str, self_v: float | None, peers: list[float], *, unit: str = ""
) -> dict[str, Any]:
    if self_v is None or not peers:
        return {
            "metric": name, "self": None if self_v is None else _round2(self_v),
            "peer_median": None, "delta_pct": None, "sample_size": len(peers),
            "unit": unit,
        }
    pm = _round2(median(peers))
    return {
        "metric": name,
        "self": _round2(self_v),
        "peer_median": pm,
        "delta_pct": _pct_delta(self_v, pm),
        "sample_size": len(peers),
        "unit": unit,
    }


def compute(
    db: DBSession, *, tenant: Tenant, language: str = "en"
) -> dict[str, Any]:
    """Return peer benchmark block + AI interpretation."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")

    today = date.today()
    peers = _peer_metrics(db, self_tenant=tenant, today=today)

    metrics: list[dict[str, Any]] = []
    metrics.append(_metric_block(
        "avg_price", _avg_price(db, tenant.id), peers["avg_price"], unit="currency"))
    metrics.append(_metric_block(
        "rating", _rating(tenant), peers["rating"], unit="stars"))
    metrics.append(_metric_block(
        "occupancy_30d", _occupancy_30d(db, tenant.id, today=today),
        peers["occupancy_30d"], unit="pct"))
    metrics.append(_metric_block(
        "bookings_30d", float(_bookings_30d(db, tenant.id, today=today)),
        peers["bookings_30d"], unit="count"))
    metrics.append(_metric_block(
        "services_count", float(_services_count(db, tenant.id)),
        peers["services_count"], unit="count"))

    has_peers = any(m["sample_size"] > 0 for m in metrics)

    if not has_peers:
        return {
            "category": _tenant_category(tenant),
            "metrics": metrics,
            "summary": "No peer data available yet in your category.",
            "provider": "fallback",
        }

    # Build prompt from real numbers only
    lines = [
        f"CATEGORY: {_tenant_category(tenant)}",
        "",
        "METRIC_COMPARISON (self vs peer_median, delta_pct):",
    ]
    for m in metrics:
        if m["self"] is None or m["peer_median"] is None:
            continue
        lines.append(
            f"  - {m['metric']}: self={m['self']} peer_median={m['peer_median']} "
            f"delta={m['delta_pct']}% (n={m['sample_size']})"
        )

    lang = _LANGUAGE_NAMES.get(language, "English")
    prompt = (
        "You are an analyst for Platform-X. Based ONLY on the numbers below, "
        "write 2-4 short bullet points comparing this business to its anonymized "
        "peer group. Do NOT invent numbers. Highlight at most one strength and "
        "one weakness with concrete percentages from the data. Write in " + lang + ".\n\n"
        + "\n".join(lines)
    )

    summary = None
    provider = "fallback"
    try:
        result = ai_service.chat(prompt, history=[])
        summary = (result or {}).get("content", "").strip() or None
        if summary:
            provider = "ai"
    except Exception:
        summary = None

    if not summary:
        parts: list[str] = []
        for m in metrics:
            if m["delta_pct"] is None:
                continue
            direction = "above" if m["delta_pct"] > 0 else "below"
            parts.append(
                f"{m['metric']}: {abs(m['delta_pct'])}% {direction} peers (median {m['peer_median']})"
            )
        summary = ". ".join(parts) if parts else "Not enough comparable metrics."

    return {
        "category": _tenant_category(tenant),
        "metrics": metrics,
        "summary": summary,
        "provider": provider,
    }
