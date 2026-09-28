"""Authentication schemas."""

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """User registration payload."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    language: str = Field(default="en", max_length=10)
    preferred_currency: str = Field(default="AED", max_length=10)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        return v


class LoginRequest(BaseModel):
    """User login payload."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class TokenResponse(BaseModel):
    """JWT token response (access + refresh)."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    """Request to exchange a refresh token for a new access token."""

    refresh_token: str = Field(min_length=10)


class CurrentUserResponse(BaseModel):
    """Minimal current-user info returned by /me."""

    id: str
    email: str
    phone: str | None = None
    first_name: str
    last_name: str
    tenant_id: str
    language: str
    preferred_currency: str
    points: int
    tier: str


class ForgotPasswordRequest(BaseModel):
    """Request to start password reset flow."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Complete password reset with token + new password."""

    token: str = Field(min_length=10)
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        return v


class BusinessLoginRequest(BaseModel):
    """Business owner login payload."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class BusinessMeResponse(BaseModel):
    """Current business user profile."""

    id: str
    email: str
    first_name: str
    last_name: str
    tenant_id: str
    tenant_name: str
    tenant_slug: str
    business_role: str
