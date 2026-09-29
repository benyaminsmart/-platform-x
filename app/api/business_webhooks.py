"""Business Webhooks management (Phase 14, Step 6).

Prefix: /business/api/webhooks
Auth: business JWT. Write ops restricted to owner/manager.

NOTE: no 'from __future__ import annotations'.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services import webhook_service


router = APIRouter(prefix="/business/api/webhooks", tags=["business-webhooks"])

_WRITE_ROLES = {"owner", "manager"}


class WebhookItem(BaseModel):
    id: str
    name: str
    url: str
    events: list[str]
    active: bool
    created_at: str | None
    last_success_at: str | None
    last_failure_at: str | None
    last_status_code: int | None
    failure_count: int


class WebhookListResponse(BaseModel):
    total: int
    items: list[WebhookItem]
    allowed_events: list[str]


class CreateWebhookRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1, max_length=1000)
    events: list[str] = Field(min_length=1)


class CreateWebhookResponse(BaseModel):
    webhook: WebhookItem
    plaintext_secret: str
    warning: str


class DeleteResponse(BaseModel):
    id: str
    active: bool


def _require_write(user: User) -> None:
    if user.business_role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Only owner or manager can manage webhooks")


def _to_item(row) -> WebhookItem:
    return WebhookItem(**webhook_service.serialize_webhook(row))


@router.get("", response_model=WebhookListResponse)
@limiter.limit("60/minute")
def list_webhooks(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> WebhookListResponse:
    rows = webhook_service.list_webhooks(db, tenant)
    return WebhookListResponse(
        total=len(rows),
        items=[_to_item(r) for r in rows],
        allowed_events=sorted(webhook_service.ALLOWED_EVENTS),
    )


@router.post("", response_model=CreateWebhookResponse)
@limiter.limit("20/minute")
def create_webhook(
    request: Request,
    payload: CreateWebhookRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> CreateWebhookResponse:
    _require_write(user)
    try:
        row, secret = webhook_service.register_webhook(
            db, tenant=tenant, name=payload.name, url=payload.url,
            events=payload.events, user_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CreateWebhookResponse(
        webhook=_to_item(row),
        plaintext_secret=secret,
        warning="Store this secret safely — it will not be shown again.",
    )


@router.post("/{webhook_id}/delete", response_model=DeleteResponse)
@limiter.limit("20/minute")
def delete_webhook(
    request: Request,
    webhook_id: str,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> DeleteResponse:
    _require_write(user)
    row = webhook_service.delete_webhook(db, tenant, webhook_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return DeleteResponse(id=row.id, active=bool(row.active))
