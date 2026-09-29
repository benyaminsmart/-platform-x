"""Service endpoints — public read, admin-only write."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_tenant
from app.api.deps_admin import require_role
from app.db.session import get_db
from app.models.tenant import Tenant
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.service import ServiceCreate, ServicePublic, ServiceUpdate
from app.services import service_service

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=PaginatedResponse[ServicePublic])
def list_services(
    type_filter: Annotated[str | None, Query(alias="type")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    tenant: Tenant = Depends(get_current_tenant),
    db: DBSession = Depends(get_db),
) -> PaginatedResponse[ServicePublic]:
    """List active services for the current tenant (public)."""
    items, total = service_service.list_services(
        db,
        tenant_id=tenant.id,
        type_filter=type_filter,
        status_filter="active",
        page=page,
        limit=limit,
    )
    return PaginatedResponse[ServicePublic](
        items=[ServicePublic.model_validate(s) for s in items],
        total=total,
        page=page,
        page_size=limit,
    )


@router.get("/{service_id}", response_model=ServicePublic)
def get_service(
    service_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: DBSession = Depends(get_db),
) -> ServicePublic:
    """Return a service by id (public)."""
    svc = service_service.get_service(db, tenant_id=tenant.id, service_id=service_id)
    if svc is None or svc.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return ServicePublic.model_validate(svc)


@router.post(
    "",
    response_model=ServicePublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("super_admin", "admin"))],
)
def create_service(
    payload: ServiceCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: DBSession = Depends(get_db),
) -> ServicePublic:
    """Create a new service (admin only)."""
    svc = service_service.create_service(db, tenant_id=tenant.id, payload=payload)
    return ServicePublic.model_validate(svc)


@router.patch(
    "/{service_id}",
    response_model=ServicePublic,
    dependencies=[Depends(require_role("super_admin", "admin"))],
)
def update_service(
    service_id: str,
    payload: ServiceUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: DBSession = Depends(get_db),
) -> ServicePublic:
    """Partially update a service (admin only)."""
    svc = service_service.update_service(
        db, tenant_id=tenant.id, service_id=service_id, payload=payload
    )
    if svc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return ServicePublic.model_validate(svc)


@router.delete(
    "/{service_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_role("super_admin", "admin"))],
)
def delete_service(
    service_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: DBSession = Depends(get_db),
) -> MessageResponse:
    """Soft-delete a service (admin only)."""
    ok = service_service.delete_service(db, tenant_id=tenant.id, service_id=service_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return MessageResponse(message="Service deactivated")

@router.get("/{service_id}/gallery")
def service_gallery(
    service_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: DBSession = Depends(get_db),
) -> dict:
    """Return the image gallery + attributes for one service."""
    from app.models.service import Service
    s = (
        db.query(Service)
        .filter(Service.id == service_id, Service.tenant_id == tenant.id)
        .one_or_none()
    )
    if s is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Service not found")
    return {
        "service_id": s.id,
        "service_name": s.name,
        "service_type": s.type,
        "price": str(s.price),
        "currency": s.currency,
        "capacity": s.capacity,
        "images": list(s.image_urls or []),
        "attributes": dict(s.attributes or {}),
        "description": s.description,
    }



@router.get("/{service_id}/rate-plans")
def service_rate_plans(
    service_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: DBSession = Depends(get_db),
) -> list[dict]:
    """Public: list active rate plans for a service."""
    from app.models.rate_plan import RatePlan
    rows = (
        db.query(RatePlan)
        .filter(
            RatePlan.tenant_id == tenant.id,
            RatePlan.service_id == service_id,
            RatePlan.active.is_(True),
        )
        .order_by(RatePlan.price_modifier_value.asc())
        .all()
    )
    return [
        {
            "id": rp.id,
            "name": rp.name,
            "code": rp.code,
            "price_modifier_type": rp.price_modifier_type,
            "price_modifier_value": str(rp.price_modifier_value),
            "meal_plan": rp.meal_plan,
            "refundable": rp.refundable,
            "min_nights": rp.min_nights,
            "description": rp.description,
        }
        for rp in rows
    ]
