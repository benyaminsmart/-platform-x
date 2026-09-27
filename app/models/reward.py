"""Reward model — reward points history."""

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin
from sqlalchemy import DateTime
from datetime import datetime, timezone


class Reward(UUIDMixin, Base):
    """A reward points transaction (earn, redeem, adjust)."""

    __tablename__ = "rewards"
    __table_args__ = (
        Index("ix_rewards_tenant_user", "tenant_id", "user_id"),
        Index("ix_rewards_created_at", "created_at"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=False
    )
    reward_type: Mapped[str] = mapped_column(String(20), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Reward type={self.reward_type} points={self.points} user={self.user_id}>"
