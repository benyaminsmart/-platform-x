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
from app.schemas.reward_wallet import (
    RedeemCatalogItemPublic,
    RedeemOptionRequest,
    RewardLedgerEntryPublic,
    RewardWalletPublic,
)
from app.services import reward_engine, reward_redemption, reward_service

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


# ---------- Phase 79: Wallet + Catalog + Ledger ----------


@limiter.limit("60/minute")
@router.get("/wallet", response_model=RewardWalletPublic)
def get_my_wallet(
    request: Request,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> RewardWalletPublic:
    """Return the current user's wallet balances."""
    w = reward_engine.get_or_create_wallet(db, user=user)
    return RewardWalletPublic.model_validate(w)


@limiter.limit("60/minute")
@router.get("/catalog", response_model=list[RedeemCatalogItemPublic])
def get_redeem_catalog(
    request: Request,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[RedeemCatalogItemPublic]:
    """Return the active redeem catalog."""
    rows = reward_redemption.list_active_options(db)
    return [RedeemCatalogItemPublic.model_validate(o) for o in rows]


@limiter.limit("30/minute")
@router.post("/redeem-option", response_model=RewardLedgerEntryPublic, status_code=status.HTTP_201_CREATED)
def redeem_catalog_option(
    request: Request,
    payload: RedeemOptionRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> RewardLedgerEntryPublic:
    """Redeem a catalog option using the user's available balance."""
    try:
        entry = reward_redemption.redeem_option(
            db,
            tenant=tenant,
            user=user,
            option_id=payload.option_id,
            reference_id=payload.reference_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return RewardLedgerEntryPublic.model_validate(entry)


@limiter.limit("60/minute")
@router.get("/ledger", response_model=list[RewardLedgerEntryPublic])
def get_my_ledger(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[RewardLedgerEntryPublic]:
    """Return the current user's ledger entries (newest first)."""
    rows = reward_engine.list_ledger(db, user_id=user.id, limit=limit)
    # list_ledger returns dicts; validate through the schema
    return [RewardLedgerEntryPublic(**r) for r in rows]
