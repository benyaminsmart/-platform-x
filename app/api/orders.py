"""Order endpoints (auth required)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_tenant, get_current_user
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.order import OrderCreate, OrderPublic
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderPublic, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> OrderPublic:
    """Create a new order."""
    order = order_service.create_order(
        db, tenant_id=tenant.id, user_id=user.id, payload=payload
    )
    return OrderPublic.model_validate(order)


@router.get("", response_model=PaginatedResponse[OrderPublic])
def list_my_orders(
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    all_tenants: Annotated[bool, Query(alias="all")] = False,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> PaginatedResponse[OrderPublic]:
    """List current user's orders. Pass ?all=true for cross-tenant."""
    items, total = order_service.list_orders(
        db,
        tenant_id=None if all_tenants else tenant.id,
        user_id=user.id,
        status_filter=status_filter,
        page=page,
        limit=limit,
    )
    return PaginatedResponse[OrderPublic](
        items=[OrderPublic.model_validate(o) for o in items],
        total=total,
        page=page,
        page_size=limit,
    )


@router.get("/{order_id}", response_model=OrderPublic)
def get_order(
    order_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> OrderPublic:
    """Return an order by id."""
    order = order_service.get_order(
        db, user_id=user.id, order_id=order_id, tenant_id=None
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return OrderPublic.model_validate(order)


@router.post("/{order_id}/cancel", response_model=OrderPublic)
def cancel_order(
    order_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> OrderPublic:
    """Cancel an order if allowed."""
    try:
        order = order_service.cancel_order(
            db, user_id=user.id, order_id=order_id, tenant_id=None
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return OrderPublic.model_validate(order)
