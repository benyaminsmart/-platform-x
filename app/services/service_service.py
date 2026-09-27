"""Service service — DB operations for tenant services."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceUpdate


def list_services(
    db: DBSession,
    *,
    tenant_id: str,
    type_filter: str | None = None,
    status_filter: str = "active",
    page: int = 1,
    limit: int = 50,
) -> tuple[list[Service], int]:
    """Return (services, total) with filters and pagination."""
    filters = [Service.tenant_id == tenant_id]
    if type_filter:
        filters.append(Service.type == type_filter)
    if status_filter:
        filters.append(Service.status == status_filter)

    total = db.execute(
        select(func.count()).select_from(Service).where(*filters)
    ).scalar_one()

    stmt = (
        select(Service)
        .where(*filters)
        .order_by(Service.display_order.asc(), Service.name.asc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all()), total


def get_service(db: DBSession, *, tenant_id: str, service_id: str) -> Service | None:
    """Return a service by id within a tenant."""
    stmt = select(Service).where(
        Service.id == service_id,
        Service.tenant_id == tenant_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def create_service(
    db: DBSession, *, tenant_id: str, payload: ServiceCreate
) -> Service:
    """Create a new service for a tenant."""
    svc = Service(
        tenant_id=tenant_id,
        type=payload.type,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        currency=payload.currency,
        capacity=payload.capacity,
        attributes=payload.attributes,
        image_urls=payload.image_urls,
        status=payload.status,
        display_order=payload.display_order,
    )
    db.add(svc)
    db.commit()
    db.refresh(svc)
    return svc


def update_service(
    db: DBSession, *, tenant_id: str, service_id: str, payload: ServiceUpdate
) -> Service | None:
    """Partially update a service. Returns None if not found."""
    svc = get_service(db, tenant_id=tenant_id, service_id=service_id)
    if svc is None:
        return None
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(svc, key, value)
    db.commit()
    db.refresh(svc)
    return svc


def delete_service(db: DBSession, *, tenant_id: str, service_id: str) -> bool:
    """Soft-delete a service by setting status=inactive. Returns True if found."""
    svc = get_service(db, tenant_id=tenant_id, service_id=service_id)
    if svc is None:
        return False
    svc.status = "inactive"
    db.commit()
    return True
