"""AIChatMessage model — persistent AI chat history per user."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin


class AIChatMessage(UUIDMixin, Base):
    """A single message in a user's AI chat history.

    Scoped to (tenant, user). Layer: "user" or "business".
    """

    __tablename__ = "ai_chat_messages"
    __table_args__ = (
        Index("ix_ai_chat_tenant_user", "tenant_id", "user_id"),
    )

    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    layer: Mapped[str] = mapped_column(String(20), default="user", nullable=False)  # user | business
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tokens_used: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AIChatMessage {self.role} layer={self.layer}>"
