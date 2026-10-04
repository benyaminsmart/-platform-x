"""Referral endpoints — new engine (Phase 77).

Endpoints:
    GET  /referrals/me        — code + list of relationships (as referrer)
    POST /referrals/apply     — apply a referral code (as referred user)
    POST /referrals/generate  — generate an extra referral code
    GET  /referrals/history   — audit events for one relationship
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_tenant, get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.referral_event import ReferralEvent
from app.models.referral_relationship import ReferralRelationship
from app.models.referral_reward import ReferralReward
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.referral import (
    ApplyReferralRequest,
    GenerateReferralCodeRequest,
    ReferralCodePublic,
    ReferralEventPublic,
    ReferralRelationshipPublic,
    ReferralsMe,
)
from app.services import referral_engine

router = APIRouter(prefix="/referrals", tags=["referrals"])


@limiter.limit("60/minute")
@router.get("/me", response_model=ReferralsMe)
def get_my_referrals(
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ReferralsMe:
    """Return the user's default referral code + a summary of referrals."""
    rc = referral_engine.generate_code(db, tenant=tenant, user=user)
    rows = referral_engine.list_my_referrals(db, referrer_user_id=user.id)

    completed = sum(1 for r in rows if r.status == "REWARDED")
    pending = sum(1 for r in rows if r.status in ("REGISTERED", "VERIFIED", "QUALIFIED"))

    total_credit = 0
    for r in rows:
        rewards = (
            db.query(ReferralReward)
            .filter(
                ReferralReward.relationship_id == r.id,
                ReferralReward.side == "REFERRER",
                ReferralReward.status == "ISSUED",
            )
            .all()
        )
        total_credit += sum(float(rw.amount) for rw in rewards)

    return ReferralsMe(
        referral_code=rc.code,
        referred_count=len(rows),
        completed_count=completed,
        pending_count=pending,
        total_referral_credit=total_credit,
        referrals=[ReferralRelationshipPublic.model_validate(r) for r in rows],
    )


@limiter.limit("10/minute")
@router.post(
    "/apply",
    response_model=ReferralRelationshipPublic,
    status_code=status.HTTP_201_CREATED,
)
def apply_referral(
    request: Request,
    payload: ApplyReferralRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ReferralRelationshipPublic:
    """Apply a referral code (once per referred user)."""
    try:
        rel = referral_engine.apply_code(
            db,
            tenant=tenant,
            current_user=user,
            code=payload.referral_code,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return ReferralRelationshipPublic.model_validate(rel)


@limiter.limit("10/minute")
@router.post(
    "/generate",
    response_model=ReferralCodePublic,
    status_code=status.HTTP_201_CREATED,
)
def generate_referral_code(
    request: Request,
    payload: GenerateReferralCodeRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ReferralCodePublic:
    """Return (or create) the user's default referral code.

    `label` is accepted for future non-default codes; today it is only
    applied when the user has no default code yet.
    """
    rc = referral_engine.generate_code(
        db, tenant=tenant, user=user, label=payload.label
    )
    return ReferralCodePublic.model_validate(rc)


@limiter.limit("60/minute")
@router.get(
    "/history/{relationship_id}",
    response_model=list[ReferralEventPublic],
)
def get_referral_history(
    request: Request,
    relationship_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[ReferralEventPublic]:
    """Return the audit events for a referral the user participates in."""
    rel = (
        db.query(ReferralRelationship)
        .filter(
            ReferralRelationship.id == relationship_id,
            ReferralRelationship.tenant_id == tenant.id,
        )
        .one_or_none()
    )
    if rel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found"
        )
    if user.id not in (rel.referrer_user_id, rel.referred_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not your referral"
        )
    events = (
        db.query(ReferralEvent)
        .filter(ReferralEvent.relationship_id == relationship_id)
        .order_by(ReferralEvent.created_at.asc())
        .all()
    )
    return [ReferralEventPublic.model_validate(e) for e in events]
