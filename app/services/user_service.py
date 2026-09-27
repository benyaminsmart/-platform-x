"""User service — DB operations for users."""

import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.core.security import hash_password, verify_password
from app.models.user import User


def _generate_referral_code() -> str:
    """Generate a unique-ish referral code."""
    return secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:10].upper()


def get_user_by_email(db: DBSession, tenant_id: str, email: str) -> User | None:
    """Return user by tenant + email, excluding soft-deleted."""
    stmt = select(User).where(
        User.tenant_id == tenant_id,
        User.email == email,
        User.status == "active",
        User.deleted_at.is_(None),
    )
    return db.execute(stmt).scalar_one_or_none()


def get_user_by_id(db: DBSession, user_id: str) -> User | None:
    """Return user by id (active only)."""
    stmt = select(User).where(
        User.id == user_id,
        User.status == "active",
        User.deleted_at.is_(None),
    )
    return db.execute(stmt).scalar_one_or_none()


def create_user(
    db: DBSession,
    *,
    tenant_id: str,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    phone: str | None = None,
    language: str = "en",
    preferred_currency: str = "AED",
) -> User:
    """Create a new user with hashed password."""
    user = User(
        tenant_id=tenant_id,
        email=email.lower().strip(),
        phone=phone,
        password_hash=hash_password(password),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        language=language,
        preferred_currency=preferred_currency,
        referral_code=_generate_referral_code(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: DBSession, tenant_id: str, email: str, password: str) -> User | None:
    """Return user if credentials valid, else None."""
    user = get_user_by_email(db, tenant_id, email.lower().strip())
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    # Update last login via updated_at is automatic; no dedicated field yet.
    return user
