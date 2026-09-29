"""Business Rooms API (Phase 36, Step 2).

Prefix: /business/api/rooms
Owner/manager for writes; all business roles for reads.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services import room_service


router = APIRouter(prefix="/business/api/rooms", tags=["business-rooms"])

_WRITE_ROLES = {"owner", "manager"}


class RoomItem(BaseModel):
    id: str
    number: str
    floor: int | None
    type: str | None
    status: str
    service_id: str | None
    notes: str | None


class RoomListResponse(BaseModel):
    total: int
    items: list[RoomItem]


class RoomCreateRequest(BaseModel):
    number: str = Field(min_length=1, max_length=20)
    service_id: str | None = None
    floor: int | None = Field(default=None, ge=-10, le=200)
    type: str | None = Field(default=None, max_length=50)
    status: str = Field(default="available", max_length=20)
    notes: str | None = None


class RoomUpdateRequest(BaseModel):
    number: str | None = Field(default=None, min_length=1, max_length=20)
    service_id: str | None = None
    floor: int | None = Field(default=None, ge=-10, le=200)
    type: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=20)
    notes: str | None = None


def _ser(r) -> RoomItem:
    return RoomItem(
        id=r.id, number=r.number, floor=r.floor, type=r.type,
        status=r.status, service_id=r.service_id, notes=r.notes,
    )


def _require_write(user: User) -> None:
    if user.business_role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Only owner or manager can manage rooms")


@router.get("", response_model=RoomListResponse)
@limiter.limit("60/minute")
def list_rooms(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    service_id: str | None = Query(default=None),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> RoomListResponse:
    rows = room_service.list_rooms(db, tenant, status_filter=status_filter, service_id=service_id)
    return RoomListResponse(total=len(rows), items=[_ser(r) for r in rows])


@router.post("", response_model=RoomItem)
@limiter.limit("30/minute")
def create_room(
    request: Request,
    payload: RoomCreateRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> RoomItem:
    _require_write(user)
    try:
        r = room_service.create_room(
            db, tenant,
            number=payload.number, service_id=payload.service_id,
            floor=payload.floor, type=payload.type, status=payload.status,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _ser(r)


@router.patch("/{room_id}", response_model=RoomItem)
@limiter.limit("30/minute")
def update_room(
    request: Request,
    room_id: str,
    payload: RoomUpdateRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> RoomItem:
    _require_write(user)
    updates = payload.model_dump(exclude_unset=True)
    try:
        r = room_service.update_room(db, tenant, room_id, updates=updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if r is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return _ser(r)


@router.delete("/{room_id}", response_model=RoomItem)
@limiter.limit("30/minute")
def delete_room(
    request: Request,
    room_id: str,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> RoomItem:
    _require_write(user)
    r = room_service.delete_room(db, tenant, room_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return _ser(r)
