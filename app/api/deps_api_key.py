"""Dependencies for public API key authentication (Phase 14).

Header: X-API-Key: pk_live_xxx

Usage:
  from app.api.deps_api_key import get_api_key, require_scope

  @router.get("/something")
  def endpoint(api_key: APIKey = Depends(get_api_key)): ...
  # or with scope:
  @router.get("/something", dependencies=[Depends(require_scope("read:services"))])
"""

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.db.session import get_db
from app.models.api_key import APIKey
from app.services import api_key_service


def get_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: DBSession = Depends(get_db),
) -> APIKey:
    """Resolve and verify the API key from X-API-Key header."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    row = api_key_service.authenticate(db, x_api_key)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )
    return row


def require_scope(scope: str):
    """Return a dependency that enforces a specific scope."""
    def _checker(api_key: APIKey = Depends(get_api_key)) -> APIKey:
        if not api_key_service.has_scope(api_key, scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key is missing required scope: {scope}",
            )
        return api_key
    return _checker
