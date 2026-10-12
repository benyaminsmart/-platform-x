"""Platform admin schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class AdminLoginRequest(BaseModel):
    """Admin login payload."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class AdminTokenResponse(BaseModel):
    """Admin JWT response.

    If mfa_required is True, access_token is empty and the client must
    call /auth/2fa/login with the provided mfa_token and a TOTP code.
    """

    access_token: str = ""
    token_type: str = "bearer"
    expires_in: int = 0
    mfa_required: bool = False
    mfa_token: str | None = None


class AdminPublic(BaseModel):
    """Admin profile response."""

    id: str
    email: str
    name: str
    role: str
    last_login_at: datetime | None

    model_config = {"from_attributes": True}



class MfaLoginRequest(BaseModel):
    """Second step of admin login: exchange mfa_token + TOTP for a full token."""

    mfa_token: str = Field(min_length=10)
    totp_code: str = Field(min_length=6, max_length=6)


class MfaSetupResponse(BaseModel):
    """Returned by /auth/2fa/setup — client shows provisioning_uri as QR."""

    secret: str
    provisioning_uri: str


class MfaVerifyRequest(BaseModel):
    """Confirm a newly provisioned TOTP secret."""

    totp_code: str = Field(min_length=6, max_length=6)


class MfaDisableRequest(BaseModel):
    """Disable 2FA — requires a valid current TOTP code."""

    totp_code: str = Field(min_length=6, max_length=6)