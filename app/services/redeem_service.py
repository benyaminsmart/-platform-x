"""Redeem service — list options + redeem for points.

Phase 44: when a user redeems an option, we deduct points via reward_service
and record a reward row of type "redeem". The actual reward (credit, discount,
perk) is a note for now; redemption records the value and option id.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session as DBSession

from app.models.redeem_option import RedeemOption
from app.models.user import User
from app.services import reward_service


def list_options(db: DBSession, *, active_only: bool = True) -> list[RedeemOption]:
    q = db.query(RedeemOption)
    if active_only:
        q = q.filter(RedeemOption.active.is_(True))
    return q.order_by(RedeemOption.display_order.asc(), RedeemOption.points_cost.asc()).all()


def get_option(db: DBSession, option_id: str) -> RedeemOption | None:
    return db.query(RedeemOption).filter(RedeemOption.id == option_id).one_or_none()


def redeem(
    db: DBSession,
    *,
    user: User,
    option_id: str,
) -> dict:
    opt = get_option(db, option_id)
    if opt is None or not opt.active:
        raise ValueError("option not found or inactive")

    if user.points < opt.points_cost:
        raise ValueError(f"not enough points (need {opt.points_cost}, have {user.points})")

    # Deduct points via reward_service (negative earn)
    reward_service.add_points(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        points=-int(opt.points_cost),
        reward_type="redeem",
        description=f"Redeemed: {opt.name}",
        reference_id=opt.id,
    )

    return {
        "option_id": opt.id,
        "name": opt.name,
        "points_spent": opt.points_cost,
        "reward_type": opt.reward_type,
        "reward_value": str(opt.reward_value),
        "message": "Redeemed successfully. The reward will be applied on your next booking.",
    }
