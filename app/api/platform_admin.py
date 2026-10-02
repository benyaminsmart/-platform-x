"""Platform admin endpoints."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request

from app.core.rate_limit import limiter
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.api.deps_admin import get_current_admin, require_role
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.booking import Booking
from app.models.order import Order
from app.models.platform_admin import PlatformAdmin
from app.models.subscription import Subscription
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.audit_log import AuditLogPublic
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.platform_admin import (
    AdminLoginRequest,
    AdminPublic,
    AdminTokenResponse,
)
from app.schemas.subscription import SubscriptionCreate, SubscriptionPublic
from app.schemas.tenant import TenantPublic
from app.services import admin_service, audit_service

router = APIRouter(prefix="/platform", tags=["platform-admin"])


# ---------- Auth ----------


@limiter.limit("10/minute")
@router.post("/auth/login", response_model=AdminTokenResponse)
def admin_login(
    request: Request,
    payload: AdminLoginRequest,
    db: DBSession = Depends(get_db),
) -> AdminTokenResponse:
    """Authenticate a platform admin and return a JWT."""
    admin = admin_service.authenticate(db, payload.email, payload.password)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(
        admin.id,
        extra_claims={"actor": "platform_admin", "role": admin.role},
    )
    audit_service.log(
        db,
        actor_id=admin.id,
        actor_type="platform_admin",
        action="login",
        ip_address=None,
        user_agent=None,
    )
    return AdminTokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@limiter.limit("60/minute")
@router.get("/me", response_model=AdminPublic)
def admin_me(
    request: Request,
    admin: PlatformAdmin = Depends(get_current_admin),
) -> AdminPublic:
    """Return the current admin's profile."""
    return AdminPublic.model_validate(admin)


# ---------- Tenants ----------


@limiter.limit("60/minute")
@router.get("/tenants", response_model=list[TenantPublic])
def list_all_tenants(
    request: Request,
    limit: int = 200,
    admin: PlatformAdmin = Depends(get_current_admin),
    db: DBSession = Depends(get_db),
) -> list[TenantPublic]:
    """List all tenants (including suspended) for admin.

    Capped at `limit` (default 200, max 1000) to bound the payload.
    """
    limit = max(1, min(int(limit), 1000))
    tenants = (
        db.execute(
            select(Tenant).order_by(Tenant.created_at.desc()).limit(limit)
        )
        .scalars()
        .all()
    )
    return [TenantPublic.model_validate(t) for t in tenants]


@limiter.limit("30/minute")
@router.patch("/tenants/{tenant_id}/status", response_model=TenantPublic)
def update_tenant_status(
    request: Request,
    tenant_id: str,
    new_status: str,
    admin: PlatformAdmin = Depends(require_role("super_admin", "admin")),
    db: DBSession = Depends(get_db),
) -> TenantPublic:
    """Update a tenant's status (active, suspended, deleted)."""
    if new_status not in {"active", "suspended", "deleted"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status"
        )
    tenant = db.execute(select(Tenant).where(Tenant.id == tenant_id)).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    old_status = tenant.status
    tenant.status = new_status
    if new_status == "deleted":
        tenant.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tenant)
    audit_service.log(
        db,
        actor_id=admin.id,
        actor_type="platform_admin",
        action="tenant.status.update",
        tenant_id=tenant.id,
        target_table="tenants",
        target_id=tenant.id,
        changes={"old_status": old_status, "new_status": new_status},
    )
    return TenantPublic.model_validate(tenant)


# ---------- Analytics ----------


@limiter.limit("60/minute")
@router.get("/analytics")
def platform_analytics(
    request: Request,
    admin: PlatformAdmin = Depends(get_current_admin),
    db: DBSession = Depends(get_db),
) -> dict:
    """Platform-wide counts."""
    total_tenants = db.execute(select(func.count()).select_from(Tenant)).scalar_one()
    active_tenants = db.execute(
        select(func.count()).select_from(Tenant).where(Tenant.status == "active")
    ).scalar_one()
    total_users = db.execute(select(func.count()).select_from(User)).scalar_one()
    total_bookings = db.execute(select(func.count()).select_from(Booking)).scalar_one()
    total_orders = db.execute(select(func.count()).select_from(Order)).scalar_one()
    return {
        "tenants": {"total": total_tenants, "active": active_tenants},
        "users": {"total": total_users},
        "bookings": {"total": total_bookings},
        "orders": {"total": total_orders},
    }


# ---------- Subscriptions ----------


@limiter.limit("60/minute")
@router.get("/subscriptions", response_model=list[SubscriptionPublic])
def list_subscriptions(
    request: Request,
    admin: PlatformAdmin = Depends(get_current_admin),
    db: DBSession = Depends(get_db),
) -> list[SubscriptionPublic]:
    """List all subscriptions."""
    subs = db.execute(
        select(Subscription).order_by(Subscription.created_at.desc())
    ).scalars().all()
    return [SubscriptionPublic.model_validate(s) for s in subs]


@limiter.limit("30/minute")
@router.post(
    "/subscriptions",
    response_model=SubscriptionPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_subscription(
    request: Request,
    payload: SubscriptionCreate,
    admin: PlatformAdmin = Depends(require_role("super_admin", "admin")),
    db: DBSession = Depends(get_db),
) -> SubscriptionPublic:
    """Create a subscription for a tenant."""
    tenant = db.execute(
        select(Tenant).where(Tenant.id == payload.tenant_id)
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    now = datetime.now(timezone.utc)
    end = now.replace(year=now.year + 1) if payload.billing_cycle == "yearly" else now.replace(month=(now.month % 12) + 1)
    sub = Subscription(
        tenant_id=payload.tenant_id,
        plan=payload.plan,
        status="active",
        price=payload.price,
        currency=payload.currency,
        billing_cycle=payload.billing_cycle,
        current_period_start=now,
        current_period_end=end,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    audit_service.log(
        db,
        actor_id=admin.id,
        actor_type="platform_admin",
        action="subscription.create",
        tenant_id=sub.tenant_id,
        target_table="subscriptions",
        target_id=sub.id,
        changes={"plan": sub.plan, "price": str(sub.price)},
    )
    return SubscriptionPublic.model_validate(sub)


# ---------- Audit Logs ----------


@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogPublic])
def list_audit_logs(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    admin: PlatformAdmin = Depends(require_role("super_admin", "admin")),
    db: DBSession = Depends(get_db),
) -> PaginatedResponse[AuditLogPublic]:
    """List audit logs."""
    from app.models.audit_log import AuditLog

    total = db.execute(select(func.count()).select_from(AuditLog)).scalar_one()
    rows = db.execute(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).scalars().all()
    return PaginatedResponse[AuditLogPublic](
        items=[AuditLogPublic.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=limit,
    )


# ---------- Health ----------


@router.get("/health", response_model=MessageResponse)
def admin_health() -> MessageResponse:
    """Admin-scoped health marker."""
    return MessageResponse(message="platform admin api ok")

