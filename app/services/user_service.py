"""User service — DB operations for users."""

import secrets
from datetime import datetime, timedelta, timezone

# Account lockout
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

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


def get_user_by_phone(db: DBSession, tenant_id: str, phone: str) -> User | None:
    """Return user by tenant + phone, excluding soft-deleted."""
    stmt = select(User).where(
        User.tenant_id == tenant_id,
        User.phone == phone,
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


def authenticate(
    db: DBSession, tenant_id: str, email: str, password: str
) -> tuple[User | None, str | None]:
    """Authenticate a user with lockout protection.

    Returns (user, error):
      - (user, None) on success
      - (None, "invalid") on wrong credentials
      - (None, "locked") if account is currently locked
    """
    user = get_user_by_email(db, tenant_id, email.lower().strip())
    if user is None:
        return None, "invalid"

    now = datetime.now(timezone.utc)

    # Check lockout
    if user.locked_until is not None:
        locked_until = user.locked_until
        # SQLite returns naive datetimes; assume UTC if naive
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            return None, "locked"

    # Verify password
    if not verify_password(password, user.password_hash):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            user.failed_login_attempts = 0
            db.commit()
            return None, "locked"
        db.commit()
        return None, "invalid"

    # Success — reset counters
    if user.failed_login_attempts or user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
        db.commit()
    return user, None


# ---------- Password Reset ----------


def _hash_reset_token(token: str) -> str:
    """SHA-256 hash of a password reset token."""
    import hashlib
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset(
    db: DBSession, *, user_id: str
) -> str:
    """Create a reset token (returns plaintext token)."""
    import secrets
    from datetime import datetime, timedelta, timezone

    from app.models.password_reset import PasswordReset

    token = secrets.token_urlsafe(32)
    reset = PasswordReset(
        user_id=user_id,
        token_hash=_hash_reset_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(reset)
    db.commit()
    return token


def consume_password_reset(
    db: DBSession, *, token: str
) -> str | None:
    """Validate + consume a reset token. Returns user_id or None."""
    from datetime import datetime, timezone

    from app.models.password_reset import PasswordReset

    token_hash = _hash_reset_token(token)
    reset = db.execute(
        select(PasswordReset).where(PasswordReset.token_hash == token_hash)
    ).scalar_one_or_none()

    if reset is None:
        return None
    if reset.used_at is not None:
        return None

    expires_at = reset.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None

    reset.used_at = datetime.now(timezone.utc)
    db.commit()
    return reset.user_id


def update_password(db: DBSession, *, user_id: str, new_password: str) -> bool:
    """Update user's password. Also unlocks the account."""
    from app.core.security import hash_password

    user = get_user_by_id(db, user_id)
    if user is None:
        return False
    user.password_hash = hash_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    return True
