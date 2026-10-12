"""Admin service — auth and lookups for platform admins."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.core.security import hash_password, verify_password
from app.models.platform_admin import PlatformAdmin


def get_by_email(db: DBSession, email: str) -> PlatformAdmin | None:
    return db.execute(
        select(PlatformAdmin).where(PlatformAdmin.email == email.lower().strip())
    ).scalar_one_or_none()


def get_by_id(db: DBSession, admin_id: str) -> PlatformAdmin | None:
    return db.execute(
        select(PlatformAdmin).where(PlatformAdmin.id == admin_id)
    ).scalar_one_or_none()


def authenticate(db: DBSession, email: str, password: str) -> PlatformAdmin | None:
    """Verify credentials only — no side effects.

    Callers must call record_login() once the full login flow (including
    2FA, if enabled) has succeeded.
    """
    admin = get_by_email(db, email)
    if admin is None:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin


def record_login(db: DBSession, admin: PlatformAdmin) -> None:
    """Mark a successful login on the admin record."""
    admin.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(admin)


def set_mfa_secret(db: DBSession, admin: PlatformAdmin, secret: str) -> None:
    """Store a pending TOTP secret (2FA not enabled until verified)."""
    admin.mfa_secret = secret
    admin.mfa_enabled = False
    db.commit()
    db.refresh(admin)


def enable_mfa(db: DBSession, admin: PlatformAdmin) -> None:
    """Activate 2FA after the first successful TOTP verification."""
    admin.mfa_enabled = True
    db.commit()
    db.refresh(admin)


def disable_mfa(db: DBSession, admin: PlatformAdmin) -> None:
    """Turn off 2FA and clear the stored secret."""
    admin.mfa_enabled = False
    admin.mfa_secret = None
    db.commit()
    db.refresh(admin)


def create(
    db: DBSession,
    *,
    email: str,
    password: str,
    name: str,
    role: str = "admin",
) -> PlatformAdmin:
    admin = PlatformAdmin(
        email=email.lower().strip(),
        password_hash=hash_password(password),
        name=name.strip(),
        role=role,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin
