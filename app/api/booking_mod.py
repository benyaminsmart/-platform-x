"""Booking modification API (Phase 35, Step 2).

Auth: user JWT.
Routes:
  GET  /bookings/{id}/modify-preview?check_in=&check_out=   preview price delta
  POST /bookings/{id}/modify                                apply
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.booking import Booking
from app.models.user import User
from app.services import booking_mod_service


router = APIRouter(prefix="/bookings", tags=["booking-mod"])


class ModifyRequest(BaseModel):
    new_check_in: date
    new_check_out: date | None = None


class ModifyPreview(BaseModel):
    booking_id: str
    can_modify: bool
    reason: str
    current_check_in: str
    current_check_out: str | None
    current_total: str
    new_check_in: str
    new_check_out: str | None
    new_total: str | None = None
    delta_amount: str | None = None
    currency: str


class ModifyResult(BaseModel):
    ok: bool
    booking_id: str | None = None
    new_check_in: str | None = None
    new_check_out: str | None = None
    new_total: str | None = None
    delta_amount: str | None = None
    currency: str | None = None
    reason: str | None = None


def _get_owned(db: DBSession, user: User, booking_id: str) -> Booking:
    b = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == user.id).one_or_none()
    if b is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return b


@router.get("/{booking_id}/modify-preview", response_model=ModifyPreview)
@limiter.limit("30/minute")
def modify_preview(
    request: Request,
    booking_id: str,
    new_check_in: date = Query(...),
    new_check_out: date | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ModifyPreview:
    b = _get_owned(db, user, booking_id)
    allowed, reason = booking_mod_service.can_modify(b)

    # Simulate the modification on a temp dict (no commit)
    delta = None
    new_total = None
    if allowed:
        try:
            # do a dry-run: don't commit, just compute
            from datetime import timedelta
            from decimal import Decimal
            from app.models.service import Service
            new_co = new_check_out
            if new_co is not None and new_co <= new_check_in:
                return ModifyPreview(
                    booking_id=b.id, can_modify=False, reason="new_check_out must be after new_check_in",
                    current_check_in=str(b.check_in), current_check_out=(str(b.check_out) if b.check_out else None),
                    current_total=str(b.total_amount), new_check_in=str(new_check_in),
                    new_check_out=(str(new_co) if new_co else None),
                    new_total=None, delta_amount=None, currency=b.currency,
                )
            if new_check_in <= date.today():
                return ModifyPreview(
                    booking_id=b.id, can_modify=False, reason="new_check_in must be in the future",
                    current_check_in=str(b.check_in), current_check_out=(str(b.check_out) if b.check_out else None),
                    current_total=str(b.total_amount), new_check_in=str(new_check_in),
                    new_check_out=(str(new_co) if new_co else None),
                    new_total=None, delta_amount=None, currency=b.currency,
                )
            if b.service_id:
                s = db.query(Service).filter(Service.id == b.service_id).one_or_none()
                if s is not None and new_co is not None and s.capacity is not None:
                    nights = (new_co - new_check_in).days
                    if nights > 0:
                        calc = (Decimal(str(s.price)) * Decimal(nights)).quantize(Decimal("0.01"))
                        new_total = str(calc)
                        delta = str(calc - Decimal(str(b.total_amount or 0)))
            if new_total is None:
                new_total = str(b.total_amount)
                delta = "0.00"
        except Exception as exc:
            return ModifyPreview(
                booking_id=b.id, can_modify=False, reason=f"preview error: {exc}",
                current_check_in=str(b.check_in), current_check_out=(str(b.check_out) if b.check_out else None),
                current_total=str(b.total_amount), new_check_in=str(new_check_in),
                new_check_out=(str(new_check_out) if new_check_out else None),
                new_total=None, delta_amount=None, currency=b.currency,
            )

    return ModifyPreview(
        booking_id=b.id,
        can_modify=allowed,
        reason=reason,
        current_check_in=str(b.check_in),
        current_check_out=(str(b.check_out) if b.check_out else None),
        current_total=str(b.total_amount),
        new_check_in=str(new_check_in),
        new_check_out=(str(new_check_out) if new_check_out else None),
        new_total=new_total,
        delta_amount=delta,
        currency=b.currency,
    )


@router.post("/{booking_id}/modify", response_model=ModifyResult)
@limiter.limit("10/minute")
def modify(
    request: Request,
    booking_id: str,
    payload: ModifyRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ModifyResult:
    b = _get_owned(db, user, booking_id)
    try:
        out = booking_mod_service.modify_booking(
            db, booking=b,
            new_check_in=payload.new_check_in,
            new_check_out=payload.new_check_out,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not out.get("ok"):
        return ModifyResult(ok=False, reason=out.get("reason", "not allowed"))
    return ModifyResult(**{k: v for k, v in out.items()})
