"""Notification endpoints (auth required)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_tenant, get_current_user
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.notification import NotificationPublic, UnreadCount
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=PaginatedResponse[NotificationPublic])
def list_my_notifications(
    unread_only: Annotated[bool, Query()] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> PaginatedResponse[NotificationPublic]:
    """List current user's notifications."""
    items, total = notification_service.list_for_user(
        db,
        tenant_id=tenant.id,
        user_id=user.id,
        unread_only=unread_only,
        page=page,
        limit=limit,
    )
    return PaginatedResponse[NotificationPublic](
        items=[NotificationPublic.model_validate(n) for n in items],
        total=total,
        page=page,
        page_size=limit,
    )


@router.get("/unread-count", response_model=UnreadCount)
def get_unread_count(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> UnreadCount:
    """Return count of unread notifications."""
    return UnreadCount(unread=notification_service.unread_count(db, tenant_id=tenant.id, user_id=user.id))


@router.post("/{notification_id}/read", response_model=NotificationPublic)
def mark_notification_read(
    notification_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> NotificationPublic:
    """Mark a notification as read."""
    n = notification_service.mark_read(
        db, tenant_id=tenant.id, user_id=user.id, notification_id=notification_id
    )
    if n is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return NotificationPublic.model_validate(n)
