"""Business API Keys management (Phase 14, Step 5).

Prefix: /business/api/keys
Auth: business JWT. Write ops restricted to owner/manager.

NOTE: no 'from __future__ import annotations'.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services import api_key_service


router = APIRouter(prefix="/business/api/keys", tags=["business-api-keys"])

_WRITE_ROLES = {"owner", "manager"}


class APIKeyItem(BaseModel):
    id: str
    name: str
    prefix: str
    scopes: list[str]
    active: bool
    created_at: str | None
    last_used_at: str | None
    expires_at: str | None


class APIKeyListResponse(BaseModel):
    total: int
    items: list[APIKeyItem]
    allowed_scopes: list[str]


class CreateAPIKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    scopes: list[str] = Field(min_length=1)
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)


class CreateAPIKeyResponse(BaseModel):
    key: APIKeyItem
    plaintext: str
    warning: str


class RevokeResponse(BaseModel):
    id: str
    active: bool


def _require_write(user: User) -> None:
    if user.business_role not in _WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Only owner or manager can manage API keys")


def _to_item(row) -> APIKeyItem:
    return APIKeyItem(
        id=row.id,
        name=row.name,
        prefix=row.prefix,
        scopes=list(row.scopes or []),
        active=bool(row.active),
        created_at=row.created_at.isoformat() if row.created_at else None,
        last_used_at=row.last_used_at.isoformat() if row.last_used_at else None,
        expires_at=row.expires_at.isoformat() if row.expires_at else None,
    )


@router.get("", response_model=APIKeyListResponse)
@limiter.limit("60/minute")
def list_keys(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> APIKeyListResponse:
    rows = api_key_service.list_keys(db, tenant)
    return APIKeyListResponse(
        total=len(rows),
        items=[_to_item(r) for r in rows],
        allowed_scopes=sorted(api_key_service.ALLOWED_SCOPES),
    )


@router.post("", response_model=CreateAPIKeyResponse)
@limiter.limit("20/minute")
def create_key(
    request: Request,
    payload: CreateAPIKeyRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> CreateAPIKeyResponse:
    _require_write(user)
    expires = None
    if payload.expires_in_days:
        expires = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)
    try:
        row, plaintext = api_key_service.create_key(
            db, tenant=tenant, name=payload.name, scopes=payload.scopes,
            user_id=user.id, expires_at=expires,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CreateAPIKeyResponse(
        key=_to_item(row),
        plaintext=plaintext,
        warning="Store this key safely — it will not be shown again.",
    )


@router.post("/{key_id}/revoke", response_model=RevokeResponse)
@limiter.limit("20/minute")
def revoke_key(
    request: Request,
    key_id: str,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> RevokeResponse:
    _require_write(user)
    row = api_key_service.revoke_key(db, tenant, key_id)
    if row is None:
        raise HTTPException(status_code=404, detail="API key not found")
    return RevokeResponse(id=row.id, active=bool(row.active))
