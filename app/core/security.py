"""Security primitives: password hashing and JWT tokens.

Token strategy:
- Access token: short-lived (default 30 min), used for every request.
- Refresh token: long-lived (default 30 days), used only to obtain new access tokens.
- Both are signed with SECRET_KEY and carry a `type` claim to prevent misuse.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# bcrypt has a 72-byte limit; we truncate to avoid errors on long inputs.
_BCRYPT_MAX_BYTES = 72

TokenType = Literal["access", "refresh"]


def _to_bytes(password: str) -> bytes:
    """Encode password to bytes, truncating to bcrypt's limit."""
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Return a bcrypt hash for the given plaintext password."""
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(_to_bytes(password), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return True if the plaintext matches the stored hash."""
    try:
        return bcrypt.checkpw(_to_bytes(plain_password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _create_token(
    *,
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    tenant_id: str | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Internal helper: build and sign a JWT with a type claim."""
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if tenant_id is not None:
        payload["tenant_id"] = tenant_id
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(
    subject: str,
    tenant_id: str | None = None,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived JWT access token."""
    return _create_token(
        subject=subject,
        token_type="access",
        expires_delta=expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        tenant_id=tenant_id,
        extra_claims=extra_claims,
    )


def create_refresh_token(
    subject: str,
    tenant_id: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a long-lived JWT refresh token."""
    return _create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=expires_delta
        or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        tenant_id=tenant_id,
    )


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decode a JWT. Optionally enforce its `type` claim.

    Raises JWTError if invalid, expired, or type mismatch.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if expected_type is not None and payload.get("type") != expected_type:
        raise JWTError(f"Invalid token type (expected {expected_type})")
    return payload


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode an access token; raises JWTError if invalid/expired/wrong type."""
    return decode_token(token, expected_type="access")


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode a refresh token; raises JWTError if invalid/expired/wrong type."""
    return decode_token(token, expected_type="refresh")
