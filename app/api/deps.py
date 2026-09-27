"""FastAPI dependencies for auth and tenancy."""

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services import user_service


def get_current_tenant(
    x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug"),
    db: DBSession = Depends(get_db),
) -> Tenant:
    """Resolve the current tenant from X-Tenant-Slug header.

    Falls back to DEFAULT_TENANT_SLUG when header is absent (dev convenience).
    """
    slug = (x_tenant_slug or settings.DEFAULT_TENANT_SLUG).strip().lower()
    tenant = db.query(Tenant).filter(
        Tenant.slug == slug,
        Tenant.status == "active",
        Tenant.deleted_at.is_(None),
    ).one_or_none()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{slug}' not found",
        )
    return tenant


def get_current_user(
    authorization: str | None = Header(default=None),
    tenant: Tenant = Depends(get_current_tenant),
    db: DBSession = Depends(get_db),
) -> User:
    """Return the authenticated user from the Bearer token."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = payload.get("sub")
    token_tenant = payload.get("tenant_id")
    if not user_id or token_tenant != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not match tenant",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_service.get_user_by_id(db, user_id)
    if user is None or user.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
