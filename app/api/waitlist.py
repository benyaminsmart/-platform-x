"""Waitlist API (Phase 48, Step 2).

  GET    /me/waitlist                        list user's waitlist entries
  POST   /me/waitlist                        join the waitlist
  DELETE /me/waitlist/{entry_id}             leave the waitlist
  POST   /me/waitlist/check                  on-demand notify (public check may come later)

Design: user-scoped, JWT required. No tenant header needed (global user).
NOTE: no 'from __future__ import annotations' in this file.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.services import waitlist_service as wls


router = APIRouter(prefix="/me/waitlist", tags=["waitlist"])


class WaitlistItem(BaseModel):
    id: str
    service_id: str
    service_name: str
    tenant_slug: str | None = None
    tenant_name: str
    check_in: str | None
    check_out: str | None
    guests: int
    active: bool
    position: int | None
    notified_at: str | None
    created_at: str | None


class WaitlistJoin(BaseModel):
    service_id: str = Field(min_length=1, max_length=36)
    check_in: date
    check_out: date
    guests: int = Field(default=1, ge=1, le=50)


class WaitlistCheck(BaseModel):
    service_id: str = Field(min_length=1, max_length=36)
    check_in: date
    check_out: date


class WaitlistCheckResult(BaseModel):
    notified: bool
    entry_id: str | None = None
    user_id: str | None = None
    check_in: str | None = None
    check_out: str | None = None


@router.get("", response_model=list[WaitlistItem])
@limiter.limit("60/minute")
def list_waitlist(
    request: Request,
    active_only: bool = True,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[WaitlistItem]:
    return [WaitlistItem(**r) for r in wls.list_entries(db, user_id=user.id, active_only=active_only)]


@router.post("", response_model=WaitlistItem, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def join_waitlist(
    request: Request,
    payload: WaitlistJoin,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> WaitlistItem:
    entry, st = wls.join(
        db, user_id=user.id, service_id=payload.service_id,
        check_in=payload.check_in, check_out=payload.check_out,
        guests=payload.guests,
    )
    if st == "bad_dates":
        raise HTTPException(status_code=422, detail="check_out must be after check_in")
    if st == "not_found":
        raise HTTPException(status_code=404, detail="Service not found")
    if st == "not_full":
        raise HTTPException(status_code=409, detail="Service is not full for these dates")
    if st == "already":
        # return existing entry with 200 instead of 201
        rows = wls.list_entries(db, user_id=user.id, active_only=False)
        for r in rows:
            if r["id"] == entry.id:
                return WaitlistItem(**r)
    rows = wls.list_entries(db, user_id=user.id, active_only=False)
    for r in rows:
        if r["id"] == entry.id:
            return WaitlistItem(**r)
    raise HTTPException(status_code=500, detail="Waitlist entry created but not found")


@router.delete("/{entry_id}")
@limiter.limit("30/minute")
def leave_waitlist(
    request: Request,
    entry_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> dict:
    ok = wls.leave(db, user_id=user.id, entry_id=entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    return {"deleted": True, "entry_id": entry_id}


@router.post("/check", response_model=WaitlistCheckResult)
@limiter.limit("30/minute")
def check_waitlist(
    request: Request,
    payload: WaitlistCheck,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> WaitlistCheckResult:
    """Trigger on-demand notify: if capacity is free, notify the first FIFO entry."""
    result = wls.check_and_notify(
        db, service_id=payload.service_id,
        check_in=payload.check_in, check_out=payload.check_out,
    )
    if result is None:
        return WaitlistCheckResult(notified=False)
    return WaitlistCheckResult(
        notified=True,
        entry_id=result["entry_id"],
        user_id=result["user_id"],
        check_in=result["check_in"],
        check_out=result["check_out"],
    )
