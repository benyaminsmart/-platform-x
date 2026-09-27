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
    admin = get_by_email(db, email)
    if admin is None:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    admin.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(admin)
    return admin


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
