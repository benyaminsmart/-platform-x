"""Shared Pydantic schemas."""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base for schemas that read from SQLAlchemy models."""

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response envelope."""

    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size


class TimestampedModel(ORMModel):
    """Adds id + timestamps to read schemas."""

    id: str
    created_at: datetime
    updated_at: datetime
