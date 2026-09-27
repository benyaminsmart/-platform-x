"""Partner application schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

TenantType = Literal["hotel", "restaurant", "travel_agency", "entertainment"]
TierInterest = Literal["starter", "professional", "enterprise"]


class PartnerApplicationCreate(BaseModel):
    """Payload to submit a partner application."""

    # Business type
    tenant_type: TenantType

    # Contact
    contact_name: str = Field(min_length=2, max_length=200)
    contact_role: str = Field(min_length=2, max_length=80)
    email: EmailStr
    phone: str = Field(min_length=5, max_length=50)
    whatsapp: str | None = Field(default=None, max_length=50)

    # Business
    business_name: str = Field(min_length=2, max_length=255)
    brand_name: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=2, max_length=120)
    address: str = Field(min_length=5, max_length=500)
    website: str | None = Field(default=None, max_length=255)
    instagram: str | None = Field(default=None, max_length=255)
    founded_year: int | None = Field(default=None, ge=1900, le=2100)
    staff_count: str | None = Field(default=None, max_length=50)

    # Plan
    tier_interest: TierInterest = "professional"
    languages: list[str] = Field(default_factory=lambda: ["en"])

    # Free-form
    about: str | None = Field(default=None, max_length=2000)
    motivation: str | None = Field(default=None, max_length=2000)

    # Type-specific details
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: list[str]) -> list[str]:
        allowed = {"en", "ar", "fil", "hi"}
        bad = [x for x in v if x not in allowed]
        if bad:
            raise ValueError(f"Unsupported languages: {bad}")
        if not v:
            raise ValueError("At least one language required")
        return v


class PartnerApplicationPublic(BaseModel):
    """Read model for a partner application."""

    id: str
    tenant_type: str
    contact_name: str
    contact_role: str
    email: str
    phone: str
    whatsapp: str | None
    business_name: str
    brand_name: str | None
    city: str
    address: str
    website: str | None
    instagram: str | None
    founded_year: int | None
    staff_count: str | None
    tier_interest: str
    languages: list[str]
    about: str | None
    motivation: str | None
    details: dict[str, Any]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PartnerApplicationReceived(BaseModel):
    """Response after submitting an application."""

    id: str
    message: str
    email: str
