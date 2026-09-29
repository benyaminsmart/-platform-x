"""API Key service — generate, verify, and manage tenant API keys.

Security model:
- Plaintext key shown exactly once at creation, then discarded.
- Only the SHA-256 hash is stored.
- Prefix (pk_live_xxx) is stored for log identification.
- Comparison uses constant-time comparison to avoid timing attacks.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.api_key import APIKey
from app.models.tenant import Tenant


KEY_PREFIX = "pk_live_"
KEY_HEX_BYTES = 24  # 48 hex chars
PREFIX_DISPLAY_LEN = 12  # pk_live_ + first 4 hex chars? we use 8 hex


ALLOWED_SCOPES = {
    "read:services",
    "read:bookings",
    "read:orders",
    "read:reviews",
    "read:analytics",
    "write:webhooks",
}


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def generate_key() -> dict[str, str]:
    """Return {'plaintext', 'prefix', 'hashed'}."""
    body = secrets.token_hex(KEY_HEX_BYTES)
    plaintext = KEY_PREFIX + body
    prefix = KEY_PREFIX + body[:8]
    hashed = _sha256_hex(plaintext)
    return {"plaintext": plaintext, "prefix": prefix, "hashed": hashed}


def validate_scopes(scopes: list[str]) -> list[str]:
    if not scopes:
        raise ValueError("at least one scope is required")
    bad = [s for s in scopes if s not in ALLOWED_SCOPES]
    if bad:
        raise ValueError(f"unknown scopes: {bad}. allowed: {sorted(ALLOWED_SCOPES)}")
    return scopes


def create_key(
    db: DBSession,
    *,
    tenant: Tenant,
    name: str,
    scopes: list[str],
    user_id: str | None = None,
    expires_at: datetime | None = None,
) -> tuple[APIKey, str]:
    """Create a new API key. Returns (row, plaintext_key)."""
    name = (name or "").strip()
    if not name:
        raise ValueError("name is required")
    validate_scopes(scopes)

    k = generate_key()
    row = APIKey(
        tenant_id=tenant.id,
        name=name[:200],
        prefix=k["prefix"],
        hashed_key=k["hashed"],
        scopes=list(scopes),
        active=True,
        expires_at=expires_at,
        created_by_user_id=user_id,
        extra={},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, k["plaintext"]


def list_keys(db: DBSession, tenant: Tenant) -> list[APIKey]:
    return (
        db.query(APIKey)
        .filter(APIKey.tenant_id == tenant.id)
        .order_by(APIKey.created_at.desc())
        .all()
    )


def get_key(db: DBSession, tenant: Tenant, key_id: str) -> APIKey | None:
    return (
        db.query(APIKey)
        .filter(APIKey.id == key_id, APIKey.tenant_id == tenant.id)
        .one_or_none()
    )


def revoke_key(db: DBSession, tenant: Tenant, key_id: str) -> APIKey | None:
    row = get_key(db, tenant, key_id)
    if row is None:
        return None
    row.active = False
    db.commit()
    db.refresh(row)
    return row


def authenticate(db: DBSession, plaintext_key: str) -> APIKey | None:
    """Return the APIKey row if the key matches and is active; else None.

    Uses constant-time comparison on the hashed form.
    """
    if not plaintext_key or not plaintext_key.startswith(KEY_PREFIX):
        return None

    hashed = _sha256_hex(plaintext_key)

    # Fast lookup by prefix, then constant-time verify of the hash.
    prefix = plaintext_key[: len(KEY_PREFIX) + 8]
    row = db.query(APIKey).filter(APIKey.prefix == prefix).one_or_none()
    if row is None:
        return None

    if not hmac.compare_digest(row.hashed_key, hashed):
        return None

    if not row.active:
        return None

    if row.expires_at is not None:
        now = datetime.now(timezone.utc)
        exp = row.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now >= exp:
            return None

    # best-effort: record usage
    row.last_used_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception:
        db.rollback()

    return row


def serialize_key(row: APIKey) -> dict[str, Any]:
    """Return API key as dict without hashed_key (for API responses)."""
    return {
        "id": row.id,
        "name": row.name,
        "prefix": row.prefix,
        "scopes": list(row.scopes or []),
        "active": bool(row.active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
    }


def has_scope(row: APIKey, scope: str) -> bool:
    return scope in (row.scopes or [])
