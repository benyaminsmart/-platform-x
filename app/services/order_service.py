"""Order service — DB operations for orders."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.models.order import Order
from app.schemas.order import OrderCreate

_CANCELLABLE = {"pending", "preparing"}


def create_order(
    db: DBSession, *, tenant_id: str, user_id: str, payload: OrderCreate
) -> Order:
    """Create a new order."""
    order = Order(
        tenant_id=tenant_id,
        user_id=user_id,
        service_type=payload.service_type,
        service_name=payload.service_name,
        quantity=payload.quantity,
        amount=payload.amount,
        currency=payload.currency,
        status="pending",
        payment_status="pending",
        notes=payload.notes,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_order(
    db: DBSession, *, user_id: str, order_id: str, tenant_id: str | None = None
) -> Order | None:
    """Return an order owned by the user. tenant_id optional (cross-tenant when None)."""
    conditions = [Order.id == order_id, Order.user_id == user_id]
    if tenant_id is not None:
        conditions.append(Order.tenant_id == tenant_id)
    stmt = select(Order).where(*conditions)
    return db.execute(stmt).scalar_one_or_none()


def list_orders(
    db: DBSession,
    *,
    user_id: str,
    tenant_id: str | None = None,
    status_filter: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[Order], int]:
    """Return (orders, total) with filters and pagination.

    If tenant_id is None, returns orders across all tenants for the user.
    """
    filters = [Order.user_id == user_id]
    if tenant_id is not None:
        filters.append(Order.tenant_id == tenant_id)
    if status_filter:
        filters.append(Order.status == status_filter)

    total = db.execute(
        select(func.count()).select_from(Order).where(*filters)
    ).scalar_one()

    stmt = (
        select(Order)
        .where(*filters)
        .order_by(Order.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all()), total


def cancel_order(
    db: DBSession, *, user_id: str, order_id: str, tenant_id: str | None = None
) -> Order | None:
    """Cancel an order if allowed. Raises ValueError otherwise. None if not found."""
    order = get_order(db, user_id=user_id, order_id=order_id, tenant_id=tenant_id)
    if order is None:
        return None
    if order.status not in _CANCELLABLE:
        raise ValueError(f"Order in status '{order.status}' cannot be cancelled")
    order.status = "cancelled"
    db.commit()
    db.refresh(order)
    return order


def mark_delivered(
    db: DBSession, *, tenant_id: str, order_id: str
) -> Order | None:
    """Mark an order as delivered. Admin helper."""
    order = db.execute(
        select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if order is None:
        return None
    order.status = "delivered"
    order.delivered_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)
    return order
