"""Platform admin schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class AdminLoginRequest(BaseModel):
    """Admin login payload."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class AdminTokenResponse(BaseModel):
    """Admin JWT response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AdminPublic(BaseModel):
    """Admin profile response."""

    id: str
    email: str
    name: str
    role: str
    last_login_at: datetime | None

    model_config = {"from_attributes": True}
