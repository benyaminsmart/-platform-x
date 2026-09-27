"""Security primitives: password hashing and JWT tokens."""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# bcrypt has a 72-byte limit; we truncate to avoid errors on long inputs.
_BCRYPT_MAX_BYTES = 72


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


def create_access_token(
    subject: str,
    tenant_id: str | None = None,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if tenant_id is not None:
        payload["tenant_id"] = tenant_id
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode a JWT; raises JWTError if invalid or expired."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
