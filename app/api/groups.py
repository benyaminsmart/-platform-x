"""Group booking API (Phase 40, Step 3).

Prefix: /bookings/{booking_id}/group
User-side only. Owner of the booking can manage members.

NOTE: no 'from __future__ import annotations'.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.booking import Booking
from app.models.user import User
from app.services import group_service


router = APIRouter(prefix="/bookings/{booking_id}/group", tags=["groups"])


class GroupMemberItem(BaseModel):
    id: str
    name: str
    email: str
    share_amount: str
    paid: bool
    note: str | None


class GroupSummary(BaseModel):
    booking_id: str
    is_group: bool
    booking_total: str
    shares_total: str
    paid_total: str
    unpaid_total: str
    remaining_to_allocate: str
    members_count: int
    paid_members_count: int
    members: list[GroupMemberItem]


class GroupMemberCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    share_amount: float = Field(default=0, ge=0)
    note: str | None = None


class GroupMemberUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    share_amount: float | None = Field(default=None, ge=0)
    paid: bool | None = None
    note: str | None = None


def _ser(m) -> GroupMemberItem:
    return GroupMemberItem(
        id=m.id, name=m.name, email=m.email,
        share_amount=str(m.share_amount), paid=bool(m.paid), note=m.note,
    )


def _owned_booking(db: DBSession, *, user_id: str, booking_id: str) -> Booking:
    b = (
        db.query(Booking)
        .filter(Booking.id == booking_id, Booking.user_id == user_id)
        .one_or_none()
    )
    if b is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return b


@router.get("", response_model=GroupSummary)
@limiter.limit("60/minute")
def get_group(
    request: Request,
    booking_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> GroupSummary:
    b = _owned_booking(db, user_id=user.id, booking_id=booking_id)
    members = group_service.list_members(db, booking_id=b.id)
    s = group_service.share_summary(db, booking=b)
    return GroupSummary(
        booking_id=b.id,
        is_group=bool(b.is_group),
        booking_total=s["booking_total"],
        shares_total=s["shares_total"],
        paid_total=s["paid_total"],
        unpaid_total=s["unpaid_total"],
        remaining_to_allocate=s["remaining_to_allocate"],
        members_count=s["members_count"],
        paid_members_count=s["paid_members_count"],
        members=[_ser(m) for m in members],
    )


@router.post("", response_model=GroupMemberItem, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
def add_member(
    request: Request,
    booking_id: str,
    payload: GroupMemberCreate,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> GroupMemberItem:
    b = _owned_booking(db, user_id=user.id, booking_id=booking_id)
    try:
        m = group_service.add_member(
            db, booking=b, name=payload.name, email=payload.email,
            share_amount=payload.share_amount, note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _ser(m)


@router.patch("/{member_id}", response_model=GroupMemberItem)
@limiter.limit("20/minute")
def update_member(
    request: Request,
    booking_id: str,
    member_id: str,
    payload: GroupMemberUpdate,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> GroupMemberItem:
    b = _owned_booking(db, user_id=user.id, booking_id=booking_id)
    updates = payload.model_dump(exclude_unset=True)
    try:
        m = group_service.update_member(db, booking=b, member_id=member_id, updates=updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if m is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return _ser(m)


@router.delete("/{member_id}")
@limiter.limit("20/minute")
def remove_member(
    request: Request,
    booking_id: str,
    member_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> dict:
    b = _owned_booking(db, user_id=user.id, booking_id=booking_id)
    ok = group_service.remove_member(db, booking=b, member_id=member_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"deleted": True, "member_id": member_id}

# ---------- AI Group Coordinator (Phase 59, Step 2) ----------


class ActivitySuggestion(BaseModel):
    service_id: str
    service_name: str
    service_type: str
    price: float
    currency: str


class CoordinateResponse(BaseModel):
    status: str
    plan: str
    stats: dict
    activity_suggestions: list[ActivitySuggestion] = []
    provider: str


@router.post("/coordinate", response_model=CoordinateResponse)
@limiter.limit("15/minute")
def coordinate_group(
    request: Request,
    booking_id: str,
    language: str = "en",
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> CoordinateResponse:
    """Return an AI coordination plan for a group booking (10+ members).

    Read-only: does not modify the booking or create reservations.
    """
    from app.core.config import settings
    if not settings.AI_ENABLED:
        raise HTTPException(status_code=503, detail="AI disabled")
    if language not in {"en", "ar", "fil", "hi"}:
        raise HTTPException(status_code=422, detail="Unsupported language")

    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id, Booking.user_id == user.id)
        .one_or_none()
    )
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    from app.services.ai import group_coordinator
    try:
        out = group_coordinator.coordinate(db, booking=booking, language=language)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CoordinateResponse(**out)

