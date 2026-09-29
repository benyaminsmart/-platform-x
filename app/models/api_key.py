"""APIKey model — tenant-scoped API keys for external integrations.

Security:
- Store only the SHA-256 hash of the key.
- Show the plaintext key exactly once at creation time.
- Each key has a prefix (pk_live_xxx) for identification in logs.
- Scopes: comma-separated list, e.g. "read:services,read:bookings".
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class APIKey(UUIDMixin, TimestampMixin, Base):
    """A tenant API key."""

    __tablename__ = "api_keys"
    __table_args__ = (
        Index("ix_api_keys_tenant_active", "tenant_id", "active"),
        Index("ix_api_keys_prefix", "prefix", unique=True),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    prefix: Mapped[str] = mapped_column(String(32), nullable=False)  # pk_live_abc123
    hashed_key: Mapped[str] = mapped_column(String(128), nullable=False)  # sha256 hex

    scopes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)

    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<APIKey {self.prefix} tenant={self.tenant_id} active={self.active}>"
