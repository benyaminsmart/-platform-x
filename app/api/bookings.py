"""Booking endpoints (auth required)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_tenant, get_current_user
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingPublic
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services import booking_service

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingPublic, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> BookingPublic:
    """Create a new booking for the current user."""
    try:
        booking = booking_service.create_booking(
            db, tenant_id=tenant.id, user_id=user.id, payload=payload
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return BookingPublic.model_validate(booking)


@router.get("", response_model=PaginatedResponse[BookingPublic])
def list_my_bookings(
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    from_date: Annotated[date | None, Query()] = None,
    to_date: Annotated[date | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    all_tenants: Annotated[bool, Query(alias="all")] = False,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> PaginatedResponse[BookingPublic]:
    """List current user's bookings with filters and pagination.

    Pass ?all=true to get bookings across every tenant.
    """
    items, total = booking_service.list_bookings(
        db,
        tenant_id=None if all_tenants else tenant.id,
        user_id=user.id,
        status=status_filter,
        from_date=from_date,
        to_date=to_date,
        page=page,
        limit=limit,
    )
    return PaginatedResponse[BookingPublic](
        items=[BookingPublic.model_validate(b) for b in items],
        total=total,
        page=page,
        page_size=limit,
    )


@router.get("/{booking_id}", response_model=BookingPublic)
def get_booking(
    booking_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> BookingPublic:
    """Return booking details (must belong to current user)."""
    booking = booking_service.get_booking(
        db, user_id=user.id, booking_id=booking_id, tenant_id=None
    )
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return BookingPublic.model_validate(booking)


@router.post("/{booking_id}/cancel", response_model=BookingPublic)
def cancel_booking(
    booking_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> BookingPublic:
    """Cancel a booking if it is in a cancellable state."""
    try:
        booking = booking_service.cancel_booking(
            db, user_id=user.id, booking_id=booking_id, tenant_id=None
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return BookingPublic.model_validate(booking)
