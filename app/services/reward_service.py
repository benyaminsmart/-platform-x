"""Reward service — points earn/redeem + summary."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.models.reward import Reward
from app.models.user import User
from app.schemas.reward import RewardsSummary

TIER_THRESHOLDS = [
    ("welcome", 0),
    ("silver", 500),
    ("gold", 2000),
    ("platinum", 5000),
    ("royal", 15000),
]


def _next_tier(current_tier: str) -> tuple[str | None, int]:
    """Return (next_tier_name, points_needed) based on order."""
    names = [t[0] for t in TIER_THRESHOLDS]
    if current_tier not in names:
        return None, 0
    idx = names.index(current_tier)
    if idx + 1 >= len(names):
        return None, 0
    return names[idx + 1], TIER_THRESHOLDS[idx + 1][1]


def tier_for_points(points: int) -> str:
    """Compute tier for a points total."""
    result = TIER_THRESHOLDS[0][0]
    for name, threshold in TIER_THRESHOLDS:
        if points >= threshold:
            result = name
        else:
            break
    return result


def get_summary(db: DBSession, *, user: User) -> RewardsSummary:
    """Return points + tier + progress for a user."""
    current_tier = tier_for_points(user.points)
    next_name, next_threshold = _next_tier(current_tier)
    if next_name is None:
        return RewardsSummary(
            points=user.points,
            tier=current_tier,
            next_tier=None,
            points_to_next_tier=0,
            progress_percent=100.0,
        )
    # Progress between current tier threshold and next threshold
    current_threshold = dict(TIER_THRESHOLDS)[current_tier]
    span = next_threshold - current_threshold
    progress = (user.points - current_threshold) / span if span > 0 else 1.0
    return RewardsSummary(
        points=user.points,
        tier=current_tier,
        next_tier=next_name,
        points_to_next_tier=max(0, next_threshold - user.points),
        progress_percent=round(min(100.0, max(0.0, progress * 100)), 2),
    )


def add_points(
    db: DBSession,
    *,
    tenant_id: str,
    user_id: str,
    points: int,
    reward_type: str,
    description: str | None = None,
    reference_id: str | None = None,
) -> Reward:
    """Create a reward entry and update user's points + tier."""
    reward = Reward(
        tenant_id=tenant_id,
        user_id=user_id,
        reward_type=reward_type,
        points=points,
        description=description,
        reference_id=reference_id,
    )
    db.add(reward)

    user = db.execute(select(User).where(User.id == user_id)).scalar_one()
    user.points = max(0, user.points + points)
    user.tier = tier_for_points(user.points)
    db.commit()
    db.refresh(reward)
    return reward


def list_history(
    db: DBSession, *, tenant_id: str, user_id: str, page: int = 1, limit: int = 20
) -> tuple[list[Reward], int]:
    """Return (rewards, total)."""
    filters = [Reward.tenant_id == tenant_id, Reward.user_id == user_id]
    total = db.execute(
        select(func.count()).select_from(Reward).where(*filters)
    ).scalar_one()
    stmt = (
        select(Reward)
        .where(*filters)
        .order_by(Reward.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all()), total


def redeem(
    db: DBSession, *, tenant_id: str, user_id: str, reward_id: str
) -> Reward | None:
    """Redeem a positive earn reward by spending its points.

    Simplified model: redeem means we create a negative reward entry
    that subtracts the same points as the given reward_id. Returns None
    if reward_id is missing or not owned.
    """
    original = db.execute(
        select(Reward).where(
            Reward.id == reward_id,
            Reward.tenant_id == tenant_id,
            Reward.user_id == user_id,
            Reward.reward_type == "earn",
            Reward.points > 0,
        )
    ).scalar_one_or_none()
    if original is None:
        return None

    user = db.execute(select(User).where(User.id == user_id)).scalar_one()
    if user.points < original.points:
        raise ValueError("Not enough points to redeem")

    redemption = Reward(
        tenant_id=tenant_id,
        user_id=user_id,
        reward_type="redeem",
        points=-original.points,
        description=f"Redeem reward {reward_id}",
        reference_id=reward_id,
    )
    db.add(redemption)
    user.points -= original.points
    user.tier = tier_for_points(user.points)
    db.commit()
    db.refresh(redemption)
    return redemption
