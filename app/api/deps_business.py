"""FastAPI dependencies for business owner authentication."""

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User


def get_current_business_user(
    authorization: str | None = Header(default=None),
    x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug"),
    db: DBSession = Depends(get_db),
) -> User:
    """Return the authenticated business user (must have business_role)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id, User.status == "active").one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not active")
    if not user.business_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a business user",
        )
    return user


def get_business_tenant(
    user: User = Depends(get_current_business_user),
    db: DBSession = Depends(get_db),
) -> Tenant:
    """Return the tenant this business user belongs to."""
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant
