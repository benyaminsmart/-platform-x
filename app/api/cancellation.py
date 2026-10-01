"""Cancellation API (Phase 30, Step 5b — Wave 0 part A).

Public (auth required):
  GET  /bookings/{id}/refund-preview
  POST /bookings/{id}/cancel-with-refund

Extends the existing /bookings/{id}/cancel with policy info.

NOTE: no 'from __future__ import annotations'.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.booking import Booking
from app.models.user import User
from app.services import cancellation_service


router = APIRouter(prefix="/bookings", tags=["cancellation"])


class RefundPreview(BaseModel):
    booking_id: str
    status: str
    days_until_check_in: int
    refund_pct: int
    refund_amount: str
    currency: str
    policy_label: str
    reason: str
    can_cancel: bool


class CancelResult(BaseModel):
    booking_id: str
    status: str
    refund_pct: int
    refund_amount: str
    currency: str
    policy_label: str
    message: str


class AIRefundPreview(BaseModel):
    booking_id: str
    status: str
    currency: str
    base_pct: int
    base_amount: str
    suggested_pct: int
    suggested_amount: str
    delta_pp: int
    policy_label: str
    rationale: str
    provider: str
    signals: dict


def _get_owned_booking(db: DBSession, *, user_id: str, booking_id: str) -> Booking:
    b = (
        db.query(Booking)
        .filter(Booking.id == booking_id, Booking.user_id == user_id)
        .one_or_none()
    )
    if b is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return b


@router.get("/{booking_id}/refund-preview", response_model=RefundPreview)
@limiter.limit("30/minute")
def refund_preview(
    request: Request,
    booking_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> RefundPreview:
    b = _get_owned_booking(db, user_id=user.id, booking_id=booking_id)
    r = cancellation_service.compute_refund_policy(b)
    return RefundPreview(
        booking_id=b.id,
        status=b.status,
        days_until_check_in=r["days_until_check_in"],
        refund_pct=r["refund_pct"],
        refund_amount=r["refund_amount"],
        currency=b.currency,
        policy_label=r["policy_label"],
        reason=r["reason"],
        can_cancel=cancellation_service.can_cancel(b),
    )


@router.post("/{booking_id}/cancel-with-refund", response_model=CancelResult)
@limiter.limit("10/minute")
def cancel_with_refund(
    request: Request,
    booking_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> CancelResult:
    b = _get_owned_booking(db, user_id=user.id, booking_id=booking_id)
    try:
        out = cancellation_service.cancel_booking(db, booking=b, by_user=user)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return CancelResult(
        booking_id=out["booking_id"],
        status="cancelled",
        refund_pct=out["refund"]["refund_pct"],
        refund_amount=out["refund"]["refund_amount"],
        currency=b.currency,
        policy_label=out["refund"]["policy_label"],
        message="Booking cancelled. Refund will be processed per policy.",
    )

# ---------- AI Instant Refund (Phase 54, Step 2) ----------


@router.get("/{booking_id}/ai-refund", response_model=AIRefundPreview)
@limiter.limit("15/minute")
def ai_refund_preview(
    request: Request,
    booking_id: str,
    language: str = "en",
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> AIRefundPreview:
    """Return the base policy + AI-adjusted refund recommendation.

    The recommendation is informational only. It is NOT applied
    automatically to the booking. Cancellation still uses the base policy.
    """
    from app.core.config import settings
    if not settings.AI_ENABLED:
        raise HTTPException(status_code=503, detail="AI disabled")
    if language not in {"en", "ar", "fil", "hi"}:
        raise HTTPException(status_code=422, detail="Unsupported language")

    b = _get_owned_booking(db, user_id=user.id, booking_id=booking_id)
    from app.services.ai import instant_refund
    try:
        out = instant_refund.evaluate(db, booking=b, user=user, language=language)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return AIRefundPreview(
        booking_id=b.id,
        status=b.status,
        currency=out["currency"],
        base_pct=out["base_pct"],
        base_amount=out["base_amount"],
        suggested_pct=out["suggested_pct"],
        suggested_amount=out["suggested_amount"],
        delta_pp=out["delta_pp"],
        policy_label=out["policy_label"],
        rationale=out["rationale"],
        provider=out["provider"],
        signals=out["signals"],
    )

