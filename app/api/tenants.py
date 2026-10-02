"""Public tenant endpoints."""

from fastapi import APIRouter, Depends, Request

from app.core.rate_limit import limiter
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_tenant
from app.db.session import get_db
from app.models.tenant import Tenant
from app.schemas.tenant import TenantPublic

router = APIRouter(prefix="/tenants", tags=["tenants"])


@limiter.limit("60/minute")
@router.get("/current", response_model=TenantPublic)
def get_current_tenant_info(
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
) -> TenantPublic:
    """Return the current tenant's public branding info."""
    return TenantPublic.model_validate(tenant)


@limiter.limit("60/minute")
@router.get("", response_model=list[TenantPublic])
def list_tenants(
    request: Request,
    db: DBSession = Depends(get_db),
) -> list[TenantPublic]:
    """List all active tenants (for demo directory page)."""
    tenants = (
        db.query(Tenant)
        .filter(Tenant.status == "active", Tenant.deleted_at.is_(None))
        .order_by(Tenant.name)
        .all()
    )
    return [TenantPublic.model_validate(t) for t in tenants]
