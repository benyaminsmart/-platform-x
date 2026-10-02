"""Rewards endpoints (auth required)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request

from app.core.rate_limit import limiter
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_tenant, get_current_user
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.reward import RedeemRequest, RewardPublic, RewardsSummary
from app.services import reward_service

router = APIRouter(prefix="/rewards", tags=["rewards"])


@limiter.limit("60/minute")
@router.get("/me", response_model=RewardsSummary)
def get_my_summary(
    request: Request,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> RewardsSummary:
    """Return the current user's points/tier summary."""
    return reward_service.get_summary(db, user=user)


@limiter.limit("60/minute")
@router.get("/history", response_model=PaginatedResponse[RewardPublic])
def get_my_history(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> PaginatedResponse[RewardPublic]:
    """Return paginated reward history."""
    items, total = reward_service.list_history(
        db, tenant_id=tenant.id, user_id=user.id, page=page, limit=limit
    )
    return PaginatedResponse[RewardPublic](
        items=[RewardPublic.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=limit,
    )


@limiter.limit("10/minute")
@router.post("/redeem", response_model=RewardPublic)
def redeem_reward(
    request: Request,
    payload: RedeemRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> RewardPublic:
    """Redeem a positive earn reward."""
    try:
        redemption = reward_service.redeem(
            db, tenant_id=tenant.id, user_id=user.id, reward_id=payload.reward_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if redemption is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reward not found")
    return RewardPublic.model_validate(redemption)
