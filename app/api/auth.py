"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_tenant, get_current_user
from app.core.config import settings
from app.core.rate_limit import LIMITS, limiter
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(LIMITS["auth_register"])
def register(
    request: Request,
    payload: RegisterRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: DBSession = Depends(get_db),
) -> TokenResponse:
    """Register a new guest under the current tenant."""
    if user_service.get_user_by_email(db, tenant.id, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered for this tenant",
        )
    if payload.phone and user_service.get_user_by_phone(db, tenant.id, payload.phone):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone already registered for this tenant",
        )
    user = user_service.create_user(
        db,
        tenant_id=tenant.id,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        language=payload.language,
        preferred_currency=payload.preferred_currency,
    )
    token = create_access_token(user.id, tenant_id=tenant.id)
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(LIMITS["auth_login"])
def login(
    request: Request,
    payload: LoginRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: DBSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate and return a JWT."""
    user = user_service.authenticate(db, tenant.id, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(user.id, tenant_id=tenant.id)
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=CurrentUserResponse)
@limiter.limit(LIMITS["auth_me"])
def me(request: Request, current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    """Return the authenticated user's profile."""
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        phone=current_user.phone,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        tenant_id=current_user.tenant_id,
        language=current_user.language,
        preferred_currency=current_user.preferred_currency,
        points=current_user.points,
        tier=current_user.tier,
    )
