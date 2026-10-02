"""Referral endpoints (auth required)."""

from fastapi import APIRouter, Depends, HTTPException, status, Request

from app.core.rate_limit import limiter
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_tenant, get_current_user
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.referral import ApplyReferralRequest, ReferralPublic, ReferralsMe
from app.services import referral_service

router = APIRouter(prefix="/referrals", tags=["referrals"])


@limiter.limit("60/minute")
@router.get("/me", response_model=ReferralsMe)
def get_my_referrals(
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ReferralsMe:
    """Return referral code + list of referred users."""
    refs = referral_service.list_my_referrals(
        db, tenant_id=tenant.id, referrer_user_id=user.id
    )
    completed = sum(1 for r in refs if r.status == "completed")
    total_points = sum(r.reward_points for r in refs if r.status == "completed")
    return ReferralsMe(
        referral_code=user.referral_code,
        referred_count=len(refs),
        completed_count=completed,
        total_points_earned=total_points,
        referrals=[ReferralPublic.model_validate(r) for r in refs],
    )


@limiter.limit("10/minute")
@router.post("/apply", response_model=ReferralPublic, status_code=status.HTTP_201_CREATED)
def apply_referral(
    request: Request,
    payload: ApplyReferralRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ReferralPublic:
    """Apply a referral code (once per user)."""
    try:
        referral = referral_service.apply_code(
            db, tenant_id=tenant.id, current_user=user, referral_code=payload.referral_code
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ReferralPublic.model_validate(referral)
