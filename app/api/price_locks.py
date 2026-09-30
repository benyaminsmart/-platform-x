"""Price Locks API (Phase 47, Step 2).

  GET    /me/price-locks                       list user's locks
  POST   /me/price-locks                       create/replace a lock
  DELETE /me/price-locks/{lock_id}             delete a lock
  POST   /me/price-locks/consume               consume a lock (mark used on a booking)

Design: user-scoped, JWT required. No tenant header needed (global user).
NOTE: no 'from __future__ import annotations' in this file.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.services import price_lock_service as pls


router = APIRouter(prefix="/me/price-locks", tags=["price-locks"])


class LockItem(BaseModel):
    id: str
    service_id: str
    service_name: str
    tenant_id: str
    locked_price: float
    current_price: float | None
    currency: str
    active: bool
    expires_at: str | None
    created_at: str | None


class LockCreate(BaseModel):
    service_id: str = Field(min_length=1, max_length=36)
    window_hours: int = Field(default=48, ge=1, le=168)


class LockConsume(BaseModel):
    service_id: str = Field(min_length=1, max_length=36)
    booking_id: str = Field(min_length=1, max_length=36)


class LockConsumeResult(BaseModel):
    locked_price: float
    status: str


@router.get("", response_model=list[LockItem])
@limiter.limit("60/minute")
def list_locks(
    request: Request,
    active_only: bool = True,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[LockItem]:
    return [LockItem(**r) for r in pls.list_locks(db, user_id=user.id, active_only=active_only)]


@router.post("", response_model=LockItem, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_lock(
    request: Request,
    payload: LockCreate,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> LockItem:
    lock, st = pls.create_lock(
        db, user_id=user.id, service_id=payload.service_id,
        window_hours=payload.window_hours,
    )
    if st == "not_found":
        raise HTTPException(status_code=404, detail="Service not found")
    if st == "bad_window":
        raise HTTPException(status_code=422, detail="Invalid window_hours")
    # enrich for response
    rows = pls.list_locks(db, user_id=user.id, active_only=False)
    for r in rows:
        if r["id"] == lock.id:
            return LockItem(**r)
    raise HTTPException(status_code=500, detail="Lock created but not found")


@router.delete("/{lock_id}")
@limiter.limit("30/minute")
def delete_lock(
    request: Request,
    lock_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> dict:
    ok = pls.delete_lock(db, user_id=user.id, lock_id=lock_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Lock not found")
    return {"deleted": True, "lock_id": lock_id}


@router.post("/consume", response_model=LockConsumeResult)
@limiter.limit("30/minute")
def consume_lock(
    request: Request,
    payload: LockConsume,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> LockConsumeResult:
    price, st = pls.consume_lock(
        db, user_id=user.id, service_id=payload.service_id,
        booking_id=payload.booking_id,
    )
    if st == "not_found":
        raise HTTPException(status_code=404, detail="Lock or booking not found")
    if st == "not_active":
        raise HTTPException(status_code=409, detail="Lock is not active")
    return LockConsumeResult(locked_price=float(price), status=st)
