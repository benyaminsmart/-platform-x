"""No-show API for business panel (Phase 35, Step 4).

Prefix: /business/api/no-shows
Owner/manager only.

NOTE: no 'from __future__ import annotations'.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User
from app.services import no_show_service


router = APIRouter(prefix="/business/api/no-shows", tags=["business-no-show"])

_WRITE_ROLES = {"owner", "manager"}


def _require_write(user: User) -> None:
    if user.business_role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Only owner or manager can manage no-shows")


class NoShowItem(BaseModel):
    id: str
    service_name: str
    check_in: str
    check_out: str | None
    guests: int
    total_amount: str
    currency: str
    status: str
    payment_status: str


class NoShowListResponse(BaseModel):
    total: int
    items: list[NoShowItem]


class MarkResult(BaseModel):
    ok: bool
    booking_id: str | None = None
    status: str | None = None
    note: str | None = None
    reason: str | None = None


def _ser(b: Booking) -> NoShowItem:
    return NoShowItem(
        id=b.id,
        service_name=b.service_name,
        check_in=str(b.check_in),
        check_out=(str(b.check_out) if b.check_out else None),
        guests=b.guests,
        total_amount=str(b.total_amount),
        currency=b.currency,
        status=b.status,
        payment_status=b.payment_status,
    )


@router.get("", response_model=NoShowListResponse)
@limiter.limit("30/minute")
def list_candidates(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> NoShowListResponse:
    """List bookings eligible to be marked as no-show."""
    rows = no_show_service.list_candidates(db, tenant_id=tenant.id)
    return NoShowListResponse(total=len(rows), items=[_ser(r) for r in rows])


@router.post("/{booking_id}/mark", response_model=MarkResult)
@limiter.limit("20/minute")
def mark_no_show(
    request: Request,
    booking_id: str,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> MarkResult:
    _require_write(user)
    b = (
        db.query(Booking)
        .filter(Booking.id == booking_id, Booking.tenant_id == tenant.id)
        .one_or_none()
    )
    if b is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    out = no_show_service.mark_no_show(db, booking=b, by_business=True)
    if not out.get("ok"):
        return MarkResult(ok=False, reason=out.get("reason"))
    return MarkResult(**{k: v for k, v in out.items()})
