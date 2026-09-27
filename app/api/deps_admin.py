"""FastAPI dependencies for platform admin auth."""

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session as DBSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.platform_admin import PlatformAdmin
from app.services import admin_service


def get_current_admin(
    authorization: str | None = Header(default=None),
    db: DBSession = Depends(get_db),
) -> PlatformAdmin:
    """Return the authenticated platform admin from the Bearer token."""
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

    if payload.get("actor") != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a platform admin token",
        )

    admin_id = payload.get("sub")
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    admin = admin_service.get_by_id(db, admin_id)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin no longer exists",
        )
    return admin


def require_role(*allowed_roles: str):
    """Return a dependency that requires one of the given roles."""

    def _checker(admin: PlatformAdmin = Depends(get_current_admin)) -> PlatformAdmin:
        if admin.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}",
            )
        return admin

    return _checker
