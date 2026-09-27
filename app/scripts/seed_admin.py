"""Seed a demo platform admin account.

Run: python -m app.scripts.seed_admin
Idempotent: skips if email exists.
"""

import os

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.platform_admin import PlatformAdmin
from app.services import admin_service

DEFAULT_EMAIL = "admin@platform-x.local"
DEFAULT_PASSWORD = "ChangeMe123!"


def main() -> None:
    email = os.environ.get("DEMO_ADMIN_EMAIL", DEFAULT_EMAIL)
    password = os.environ.get("DEMO_ADMIN_PASSWORD", DEFAULT_PASSWORD)

    with SessionLocal() as db:
        existing = db.execute(
            select(PlatformAdmin).where(PlatformAdmin.email == email)
        ).scalar_one_or_none()
        if existing:
            print(f"Admin {email} already exists, skipped")
            return
        admin_service.create(
            db,
            email=email,
            password=password,
            name="Platform Admin",
            role="super_admin",
        )
        print(f"Created admin: {email}")
        print(f"Password: {password}")
        print("!! CHANGE THIS PASSWORD BEFORE PUBLIC DEMO !!")


if __name__ == "__main__":
    main()
