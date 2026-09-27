"""Referral service — apply codes and track referrals."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.models.referral import Referral
from app.models.user import User
from app.services import reward_service

WELCOME_POINTS_REFERRER = 100
WELCOME_POINTS_REFERRED = 50


def get_by_referred_user(
    db: DBSession, *, tenant_id: str, referred_user_id: str
) -> Referral | None:
    """Return a referral record where this user was referred (if any)."""
    return db.execute(
        select(Referral).where(
            Referral.tenant_id == tenant_id,
            Referral.referred_user_id == referred_user_id,
        )
    ).scalar_one_or_none()


def apply_code(
    db: DBSession, *, tenant_id: str, current_user: User, referral_code: str
) -> Referral:
    """Link current_user to the referrer who owns referral_code.

    Raises ValueError on any invalid state.
    """
    code = referral_code.strip().upper()
    if not code:
        raise ValueError("Referral code is required")
    if current_user.referral_code == code:
        raise ValueError("Cannot refer yourself")

    # Only once per user
    if get_by_referred_user(db, tenant_id=tenant_id, referred_user_id=current_user.id):
        raise ValueError("Referral already applied")

    referrer = db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.referral_code == code,
            User.status == "active",
            User.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if referrer is None:
        raise ValueError("Referral code not found")

    referral = Referral(
        tenant_id=tenant_id,
        referrer_user_id=referrer.id,
        referred_user_id=current_user.id,
        referral_code=code,
        status="completed",
        reward_points=WELCOME_POINTS_REFERRER + WELCOME_POINTS_REFERRED,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(referral)
    db.flush()  # so referral.id is available if needed

    # Award points
    reward_service.add_points(
        db,
        tenant_id=tenant_id,
        user_id=referrer.id,
        points=WELCOME_POINTS_REFERRER,
        reward_type="earn",
        description="Referral bonus (referrer)",
        reference_id=referral.id,
    )
    reward_service.add_points(
        db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        points=WELCOME_POINTS_REFERRED,
        reward_type="earn",
        description="Referral bonus (welcome)",
        reference_id=referral.id,
    )

    db.commit()
    db.refresh(referral)
    return referral


def list_my_referrals(
    db: DBSession, *, tenant_id: str, referrer_user_id: str
) -> list[Referral]:
    """Return all referrals where this user was the referrer."""
    stmt = (
        select(Referral)
        .where(
            Referral.tenant_id == tenant_id,
            Referral.referrer_user_id == referrer_user_id,
        )
        .order_by(Referral.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def count_completed(db: DBSession, *, tenant_id: str, referrer_user_id: str) -> int:
    """Count completed referrals for the referrer."""
    return db.execute(
        select(func.count()).select_from(Referral).where(
            Referral.tenant_id == tenant_id,
            Referral.referrer_user_id == referrer_user_id,
            Referral.status == "completed",
        )
    ).scalar_one()
