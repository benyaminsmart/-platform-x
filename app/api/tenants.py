"""Public tenant endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_tenant
from app.db.session import get_db
from app.models.tenant import Tenant
from app.schemas.tenant import TenantPublic

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/current", response_model=TenantPublic)
def get_current_tenant_info(
    tenant: Tenant = Depends(get_current_tenant),
) -> TenantPublic:
    """Return the current tenant's public branding info."""
    return TenantPublic.model_validate(tenant)


@router.get("", response_model=list[TenantPublic])
def list_tenants(db: DBSession = Depends(get_db)) -> list[TenantPublic]:
    """List all active tenants (for demo directory page)."""
    tenants = (
        db.query(Tenant)
        .filter(Tenant.status == "active", Tenant.deleted_at.is_(None))
        .order_by(Tenant.name)
        .all()
    )
    return [TenantPublic.model_validate(t) for t in tenants]
