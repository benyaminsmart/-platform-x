"""Session service — create, revoke, and validate user sessions.

A session is created on login/register and stores a hash of the refresh
token. On logout, the session is marked as revoked, which invalidates
the refresh token. Access tokens are short-lived and expire on their own.
"""

import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.models.session import Session


def _hash_token(token: str) -> str:
    """Return a SHA-256 hex digest of a token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(
    db: DBSession,
    *,
    tenant_id: str,
    user_id: str,
    refresh_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Session:
    """Create a new session for a user based on their refresh token."""
    session = Session(
        tenant_id=tenant_id,
        user_id=user_id,
        token_hash=_hash_token(refresh_token),
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_by_token(db: DBSession, refresh_token: str) -> Session | None:
    """Return a session by its refresh-token hash."""
    stmt = select(Session).where(Session.token_hash == _hash_token(refresh_token))
    return db.execute(stmt).scalar_one_or_none()


def revoke(db: DBSession, session: Session) -> None:
    """Mark a session as revoked."""
    session.revoked = True
    db.commit()


def revoke_by_token(db: DBSession, refresh_token: str) -> bool:
    """Revoke the session that owns this refresh token. Returns True if found."""
    session = get_by_token(db, refresh_token)
    if session is None:
        return False
    revoke(db, session)
    return True


def is_valid(db: DBSession, refresh_token: str) -> bool:
    """Check that a refresh token belongs to a non-revoked, non-expired session."""
    session = get_by_token(db, refresh_token)
    if session is None:
        return False
    if session.revoked:
        return False
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at > datetime.now(timezone.utc)
