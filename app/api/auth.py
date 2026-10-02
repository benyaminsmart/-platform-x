"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_tenant, get_current_user
from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.rate_limit import LIMITS, limiter
from app.core.security import create_access_token, create_refresh_token, decode_refresh_token
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.auth import (
    CurrentUserResponse,
    ForgotPasswordRequest,
    RefreshRequest,
    ResetPasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services import session_service, user_service

logger = get_logger(__name__)


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
    access = create_access_token(user.id, tenant_id=tenant.id)
    refresh = create_refresh_token(user.id, tenant_id=tenant.id)
    session_service.create_session(
        db,
        tenant_id=tenant.id,
        user_id=user.id,
        refresh_token=refresh,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # Record welcome notification + send email (both non-blocking)
    try:
        from app.services import notification_service
        base_url = str(request.base_url).rstrip("/")

        notification_service.create(
            db,
            tenant_id=tenant.id,
            user_id=user.id,
            channel="in_app",
            template="welcome",
            subject="Welcome to Platform-X",
            content=f"Welcome {user.first_name}! Your account is ready.",
        )
        notification_service.send_welcome_email(
            to_email=user.email,
            user_name=user.first_name,
            home_url=base_url,
        )
    except Exception:
        logger.warning("Failed to send welcome email to %s", user.email, exc_info=True)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
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
    user, error = user_service.authenticate(db, tenant.id, payload.email, payload.password)
    if user is None:
        if error == "locked":
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to too many failed attempts. Try again in 15 minutes.",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    access = create_access_token(user.id, tenant_id=tenant.id)
    refresh = create_refresh_token(user.id, tenant_id=tenant.id)
    session_service.create_session(
        db,
        tenant_id=tenant.id,
        user_id=user.id,
        refresh_token=refresh,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # Record welcome notification + send email (both non-blocking)
    try:
        from app.services import notification_service
        base_url = str(request.base_url).rstrip("/")

        notification_service.create(
            db,
            tenant_id=tenant.id,
            user_id=user.id,
            channel="in_app",
            template="welcome",
            subject="Welcome to Platform-X",
            content=f"Welcome {user.first_name}! Your account is ready.",
        )
        notification_service.send_welcome_email(
            to_email=user.email,
            user_name=user.first_name,
            home_url=base_url,
        )
    except Exception:
        logger.warning("Failed to send welcome email (register/login)", exc_info=True)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
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


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
def refresh_token(
    request: Request,
    payload: RefreshRequest,
    db: DBSession = Depends(get_db),
) -> TokenResponse:
    """Exchange a refresh token for a new access token pair."""
    from jose import JWTError

    try:
        data = decode_refresh_token(payload.refresh_token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from exc

    user_id = data.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )

    user = user_service.get_user_by_id(db, user_id)
    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer active",
        )

    # Check session is not revoked
    if not session_service.is_valid(db, payload.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked",
        )

    # Revoke the old session and create a new one (rotation)
    session_service.revoke_by_token(db, payload.refresh_token)
    new_access = create_access_token(user.id, tenant_id=user.tenant_id)
    new_refresh = create_refresh_token(user.id, tenant_id=user.tenant_id)
    session_service.create_session(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        refresh_token=new_refresh,
    )
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", response_model=MessageResponse)
@limiter.limit("30/minute")
def logout(
    request: Request,
    payload: RefreshRequest,
    db: DBSession = Depends(get_db),
) -> MessageResponse:
    """Revoke the session associated with the given refresh token."""
    session_service.revoke_by_token(db, payload.refresh_token)
    return MessageResponse(message="Logged out")


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/minute")
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: DBSession = Depends(get_db),
) -> MessageResponse:
    """Start password reset flow. Always returns success (no email enumeration)."""
    user = user_service.get_user_by_email(db, tenant.id, payload.email)
    if user is not None:
        try:
            token = user_service.create_password_reset(db, user_id=user.id)
            base_url = str(request.base_url).rstrip("/")
            reset_url = f"{base_url}/reset-password?token={token}"
            from app.services import notification_service
            notification_service.send_password_reset_email(
                to_email=user.email,
                user_name=user.first_name,
                reset_url=reset_url,
            )
        except Exception:
            logger.warning("Failed to send password reset email", exc_info=True)

    return MessageResponse(
        message="If this email is registered, a reset link has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/minute")
def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: DBSession = Depends(get_db),
) -> MessageResponse:
    """Complete password reset with token + new password."""
    user_id = user_service.consume_password_reset(db, token=payload.token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user = user_service.get_user_by_id(db, user_id)
    if user is None or user.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found for this tenant",
        )

    user_service.update_password(db, user_id=user_id, new_password=payload.new_password)

    # Record notification
    try:
        from app.services import notification_service
        notification_service.create(
            db,
            tenant_id=tenant.id,
            user_id=user_id,
            channel="in_app",
            template="password_changed",
            subject="Your password was changed",
            content="Your Platform-X password was successfully changed.",
        )
    except Exception:
        logger.warning("Failed to send password-changed email", exc_info=True)

    return MessageResponse(message="Password updated. You can now sign in.")
