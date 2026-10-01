"""AI Group Coordinator — coordination plan for group bookings (10+).

Phase 59 (Wave 3, Blue-Ocean B6).

Design principles:
- Deterministic layer: build a structured plan from real data:
    * members count, paid/unpaid split, remaining to allocate
    * group size vs service capacity (rooms needed)
    * complementary services (dining, activities) from the same tenant
- AI writes the coordination narrative ONLY. It never invents.
- Fallback text always available.
- Read-only: no booking changes, no auto-reservations.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.booking import Booking
from app.models.group_member import GroupMember
from app.models.service import Service
from app.models.tenant import Tenant
from app.services import group_service
from app.services.ai import service as ai_service


SUPPORTED_LANGUAGES = {"en", "ar", "fil", "hi"}
_LANGUAGE_NAMES = {
    "en": "English", "ar": "Arabic (Modern Standard Arabic)",
    "fil": "Filipino (Tagalog)", "hi": "Hindi",
}

# Minimum members to be considered a "group"
MIN_GROUP_SIZE = 10

# Ancillary keywords for activity suggestions
_ACTIVITY_KEYWORDS = (
    "tour", "activity", "spa", "dinner", "lunch", "breakfast",
    "transfer", "airport", "package", "experience", "show", "ticket",
)


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"))


def _is_activity(s: Service) -> bool:
    haystack = " ".join(filter(None, [
        (s.name or "").lower(),
        (s.type or "").lower(),
        (s.description or "").lower(),
    ]))
    return any(k in haystack for k in _ACTIVITY_KEYWORDS)


def _pick_activities(db: DBSession, tenant_id: str, limit: int = 4) -> list[dict[str, Any]]:
    rows = (
        db.query(Service)
        .filter(Service.tenant_id == tenant_id, Service.status == "active")
        .all()
    )
    acts = [s for s in rows if _is_activity(s)]
    acts.sort(key=lambda s: -(float(s.price)))
    return [
        {
            "service_id": s.id,
            "service_name": s.name,
            "service_type": s.type,
            "price": float(s.price),
            "currency": s.currency,
        }
        for s in acts[:limit]
    ]


def coordinate(
    db: DBSession,
    *,
    booking: Booking,
    language: str = "en",
) -> dict[str, Any]:
    """Return a coordination plan for a group booking.

    status: 'ok' | 'not_group' | 'too_small'.
    """
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")

    members = group_service.list_members(db, booking_id=booking.id)
    n = len(members)
    if not booking.is_group:
        return {
            "status": "not_group",
            "plan": "",
            "stats": {},
            "activity_suggestions": [],
            "provider": "fallback",
        }
    if n < MIN_GROUP_SIZE:
        return {
            "status": "too_small",
            "plan": "",
            "stats": {"members_count": n, "min_required": MIN_GROUP_SIZE},
            "activity_suggestions": [],
            "provider": "fallback",
        }

    summary = group_service.share_summary(db, booking=booking)
    service = (
        db.query(Service).filter(Service.id == booking.service_id).one_or_none()
        if booking.service_id
        else None
    )
    capacity = int(service.capacity) if (service and service.capacity) else 1
    rooms_needed = max(1, (booking.guests + capacity - 1) // capacity) if capacity > 0 else 1

    activities = _pick_activities(db, tenant_id=booking.tenant_id, limit=4)

    # Deterministic allocation hint: spread remaining evenly across unpaid
    remaining = Decimal(str(summary["remaining_to_allocate"]))
    unpaid_count = max(1, n - int(summary["paid_members_count"]))
    per_unpaid = _round2(remaining / Decimal(unpaid_count)) if remaining > 0 else Decimal("0.00")

    stats: dict[str, Any] = {
        "members_count": n,
        "paid_members_count": int(summary["paid_members_count"]),
        "unpaid_members_count": unpaid_count,
        "booking_total": summary["booking_total"],
        "shares_total": summary["shares_total"],
        "remaining_to_allocate": summary["remaining_to_allocate"],
        "suggested_per_unpaid": str(per_unpaid),
        "capacity_per_unit": capacity,
        "rooms_needed": rooms_needed,
        "check_in": booking.check_in.isoformat() if booking.check_in else None,
        "check_out": booking.check_out.isoformat() if booking.check_out else None,
        "guests": booking.guests,
    }

    # Build grounded prompt
    lines = [
        f"GROUP_SIZE: {n}",
        f"BOOKING_TOTAL: {summary['booking_total']} {booking.currency}",
        f"SHARES_ALLOCATED: {summary['shares_total']}",
        f"PAID: {summary['paid_total']}",
        f"REMAINING_TO_ALLOCATE: {summary['remaining_to_allocate']}",
        f"SUGGESTED_PER_UNPAID: {per_unpaid}",
        f"ROOMS_NEEDED: {rooms_needed} (capacity per unit = {capacity})",
        f"CHECK_IN: {stats['check_in']}, CHECK_OUT: {stats['check_out']}",
        "",
        "AVAILABLE_ACTIVITIES:",
    ]
    for a in activities:
        lines.append(f"  - {a['service_name']} ({a['price']} {a['currency']})")

    lang = _LANGUAGE_NAMES.get(language, "English")
    prompt = (
        "You are a group-trip coordinator for Platform-X. Based ONLY on the "
        "numbers and activities below, write a short coordination plan (max 4 "
        "short paragraphs) covering: (1) a fair allocation approach for the "
        "remaining balance; (2) how many rooms/units to book; (3) 1-2 concrete "
        "activity suggestions from the list. Do NOT invent numbers. Do NOT "
        "promise anything not in the data. Write in " + lang + ".\n\n"
        + "\n".join(lines)
    )

    plan = None
    provider = "fallback"
    try:
        result = ai_service.chat(prompt, history=[])
        plan = (result or {}).get("content", "").strip() or None
        if plan:
            provider = "ai"
    except Exception:
        plan = None

    if not plan:
        parts = [
            f"Group of {n} with {unpaid_count} unpaid member(s).",
            f"Remaining balance to allocate: {summary['remaining_to_allocate']} "
            f"{booking.currency} — suggested {per_unpaid} per unpaid member.",
            f"Rooms needed (capacity {capacity}): {rooms_needed}.",
        ]
        if activities:
            names = ", ".join(a["service_name"] for a in activities[:2])
            parts.append(f"Suggested group activities: {names}.")
        plan = " ".join(parts)

    return {
        "status": "ok",
        "plan": plan,
        "stats": stats,
        "activity_suggestions": activities,
        "provider": provider,
    }
