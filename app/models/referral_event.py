"""ReferralEvent — an immutable audit trail for referral lifecycle changes.

Phase 77, Step 1c (plan §10, §23 rule 3 "every reward operation is auditable").

Every transition (INVITED → REGISTERED → VERIFIED → ...) writes one
event. Events are append-only and never edited.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin

REFERRAL_EVENT_TYPES = (
    "INVITED",
    "REGISTERED",
    "VERIFIED",
    "QUALIFIED",
    "REWARDED",
    "REVERSED",
    "EXPIRED",
    "REVIEW_FLAGGED",
    "REVIEW_CLEARED",
    "CANCELLED",
    "CODE_GENERATED",
    "CODE_DEACTIVATED",
)


class ReferralEvent(UUIDMixin, Base):
    """Append-only audit event for a referral lifecycle change."""

    __tablename__ = "referral_events"
    __table_args__ = (
        Index("ix_referral_events_relationship", "relationship_id", "created_at"),
        Index("ix_referral_events_type", "event_type"),
        Index("ix_referral_events_tenant", "tenant_id"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    relationship_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("referral_relationships.id"), index=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # Snapshot of the relationship status at the moment of the event
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    extra: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ReferralEvent type={self.event_type} "
            f"relationship={self.relationship_id}>"
        )
