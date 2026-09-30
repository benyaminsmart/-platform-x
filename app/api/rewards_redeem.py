"""Redeem API (Phase 44, Step 2).

  GET  /rewards/redeem-options
  POST /rewards/redeem-options/{option_id}/redeem
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.services import redeem_service


router = APIRouter(prefix="/rewards/redeem-options", tags=["redeem"])


class RedeemOptionItem(BaseModel):
    id: str
    name: str
    description: str | None
    points_cost: int
    reward_type: str
    reward_value: str


class RedeemResult(BaseModel):
    option_id: str
    name: str
    points_spent: int
    reward_type: str
    reward_value: str
    message: str


@router.get("", response_model=list[RedeemOptionItem])
@limiter.limit("60/minute")
def list_options(
    request: Request,
    db: DBSession = Depends(get_db),
) -> list[RedeemOptionItem]:
    rows = redeem_service.list_options(db)
    return [
        RedeemOptionItem(
            id=o.id, name=o.name, description=o.description,
            points_cost=o.points_cost, reward_type=o.reward_type,
            reward_value=str(o.reward_value),
        )
        for o in rows
    ]


@router.post("/{option_id}/redeem", response_model=RedeemResult)
@limiter.limit("10/minute")
def redeem(
    request: Request,
    option_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> RedeemResult:
    try:
        out = redeem_service.redeem(db, user=user, option_id=option_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedeemResult(**out)
