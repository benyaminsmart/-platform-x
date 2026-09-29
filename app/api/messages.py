"""Messages API (Phase 39, Step 5).

User side:   /messages/*
Business side: /business/api/messages/*

NOTE: no 'from __future__ import annotations'.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_tenant, get_current_user
from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User
from app.services import message_service


router = APIRouter(prefix="/messages", tags=["messages"])
business_router = APIRouter(prefix="/business/api/messages", tags=["business-messages"])


class MessageItem(BaseModel):
    id: str
    thread_id: str
    sender_role: str
    body: str
    created_at: str | None
    read_at_user: str | None = None
    read_at_business: str | None = None


class SendRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class ThreadItem(BaseModel):
    thread_id: str
    booking_id: str | None
    service_name: str
    check_in: str
    unread: int
    last_message: str | None
    last_at: str | None


def _ser(m) -> MessageItem:
    return MessageItem(
        id=m.id, thread_id=m.thread_id, sender_role=m.sender_role, body=m.body,
        created_at=(m.created_at.isoformat() if m.created_at else None),
        read_at_user=(m.read_at_user.isoformat() if m.read_at_user else None),
        read_at_business=(m.read_at_business.isoformat() if m.read_at_business else None),
    )


# ---------- User side ----------


@router.get("/threads", response_model=list[ThreadItem])
@limiter.limit("60/minute")
def user_threads(
    request: Request,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: DBSession = Depends(get_db),
) -> list[ThreadItem]:
    return [ThreadItem(**t) for t in message_service.user_threads(db, tenant_id=tenant.id, user_id=user.id)]


@router.get("/{thread_id}", response_model=list[MessageItem])
@limiter.limit("60/minute")
def user_thread_messages(
    request: Request,
    thread_id: str,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: DBSession = Depends(get_db),
) -> list[MessageItem]:
    # thread_id = booking_id; verify ownership
    b = db.query(Booking).filter(Booking.id == thread_id, Booking.user_id == user.id, Booking.tenant_id == tenant.id).one_or_none()
    if b is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    message_service.mark_read_for_user(db, tenant_id=tenant.id, thread_id=thread_id)
    rows = message_service.list_thread_messages(db, tenant_id=tenant.id, thread_id=thread_id)
    return [_ser(m) for m in rows]


@router.post("/{thread_id}", response_model=MessageItem, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
def user_send(
    request: Request,
    thread_id: str,
    payload: SendRequest,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: DBSession = Depends(get_db),
) -> MessageItem:
    b = db.query(Booking).filter(Booking.id == thread_id, Booking.user_id == user.id, Booking.tenant_id == tenant.id).one_or_none()
    if b is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    try:
        m = message_service.send_message(
            db, tenant_id=tenant.id, thread_id=thread_id,
            sender_role="user", sender_user_id=user.id,
            booking_id=b.id, body=payload.body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _ser(m)


# ---------- Business side ----------


@business_router.get("/threads", response_model=list[ThreadItem])
@limiter.limit("60/minute")
def business_threads(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> list[ThreadItem]:
    return [ThreadItem(**t) for t in message_service.business_threads(db, tenant_id=tenant.id)]


@business_router.get("/{thread_id}", response_model=list[MessageItem])
@limiter.limit("60/minute")
def business_thread_messages(
    request: Request,
    thread_id: str,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> list[MessageItem]:
    b = db.query(Booking).filter(Booking.id == thread_id, Booking.tenant_id == tenant.id).one_or_none()
    if b is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    message_service.mark_read_for_business(db, tenant_id=tenant.id, thread_id=thread_id)
    rows = message_service.list_thread_messages(db, tenant_id=tenant.id, thread_id=thread_id)
    return [_ser(m) for m in rows]


@business_router.post("/{thread_id}", response_model=MessageItem, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
def business_send(
    request: Request,
    thread_id: str,
    payload: SendRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> MessageItem:
    b = db.query(Booking).filter(Booking.id == thread_id, Booking.tenant_id == tenant.id).one_or_none()
    if b is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    try:
        m = message_service.send_message(
            db, tenant_id=tenant.id, thread_id=thread_id,
            sender_role="business", sender_user_id=None,
            booking_id=b.id, body=payload.body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _ser(m)
