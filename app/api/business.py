"""Business owner endpoints — auth + dashboard data."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.booking import Booking
from app.models.order import Order
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/business/api", tags=["business"])


@router.post("/auth/login")
@limiter.limit("20/minute")
def business_login(
    request: Request,
    payload: dict,
    db: DBSession = Depends(get_db),
) -> dict:
    """Business owner login (email + password + X-Tenant-Slug header)."""
    email = (payload.get("email") or "").lower().strip()
    password = payload.get("password") or ""
    tenant_slug = request.headers.get("x-tenant-slug", "").strip().lower()

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")

    # Resolve tenant
    if not tenant_slug:
        raise HTTPException(status_code=400, detail="Tenant slug required (X-Tenant-Slug)")
    tenant = db.query(Tenant).filter(
        Tenant.slug == tenant_slug,
        Tenant.status == "active",
    ).one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Business not found")

    # Find user
    user = db.query(User).filter(
        User.tenant_id == tenant.id,
        User.email == email,
        User.status == "active",
    ).one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.business_role:
        raise HTTPException(status_code=403, detail="Not a business account")

    token = create_access_token(user.id, tenant_id=tenant.id, extra_claims={"actor": "business"})
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.get("/me")
def business_me(
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
) -> dict:
    """Current business user profile."""
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "tenant_slug": tenant.slug,
        "business_role": user.business_role,
    }


@router.get("/dashboard")
def business_dashboard(
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict:
    """Business dashboard stats."""
    # Counts
    total_bookings = db.query(func.count(Booking.id)).filter(Booking.tenant_id == tenant.id).scalar() or 0
    confirmed = db.query(func.count(Booking.id)).filter(
        Booking.tenant_id == tenant.id,
        Booking.status == "confirmed",
    ).scalar() or 0
    total_orders = db.query(func.count(Order.id)).filter(Order.tenant_id == tenant.id).scalar() or 0
    total_services = db.query(func.count(Service.id)).filter(
        Service.tenant_id == tenant.id,
        Service.status == "active",
    ).scalar() or 0

    # Revenue (sum of paid bookings + orders)
    rev_bookings = db.query(func.coalesce(func.sum(Booking.total_amount), 0)).filter(
        Booking.tenant_id == tenant.id,
        Booking.payment_status == "paid",
    ).scalar() or 0
    rev_orders = db.query(func.coalesce(func.sum(Order.amount), 0)).filter(
        Order.tenant_id == tenant.id,
        Order.payment_status == "paid",
    ).scalar() or 0
    revenue = float(rev_bookings) + float(rev_orders)

    return {
        "tenant": {"id": tenant.id, "name": tenant.name, "slug": tenant.slug},
        "stats": {
            "total_bookings": total_bookings,
            "confirmed_bookings": confirmed,
            "total_orders": total_orders,
            "active_services": total_services,
            "revenue_aed": round(revenue, 2),
        },
    }


# ---------- Services (Business-scoped) ----------


from pydantic import BaseModel, Field  # noqa: E402
from typing import Any  # noqa: E402


class BusinessServiceCreate(BaseModel):
    type: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    price: float = Field(ge=0)
    currency: str = Field(default="AED", max_length=10)
    capacity: int | None = Field(default=None, ge=0)
    attributes: dict[str, Any] = Field(default_factory=dict)
    image_urls: list[str] = Field(default_factory=list)
    status: str = Field(default="active", max_length=50)
    display_order: int = Field(default=0, ge=0)


class BusinessServiceUpdate(BaseModel):
    type: str | None = None
    name: str | None = None
    description: str | None = None
    price: float | None = Field(default=None, ge=0)
    currency: str | None = None
    capacity: int | None = Field(default=None, ge=0)
    attributes: dict[str, Any] | None = None
    image_urls: list[str] | None = None
    status: str | None = None
    display_order: int | None = None


@router.get("/services")
def list_business_services(
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> list[dict]:
    """List all services for the current business (including inactive)."""
    rows = db.query(Service).filter(Service.tenant_id == tenant.id).order_by(Service.display_order, Service.name).all()
    return [
        {
            "id": s.id,
            "type": s.type,
            "name": s.name,
            "description": s.description,
            "price": str(s.price),
            "currency": s.currency,
            "capacity": s.capacity,
            "attributes": s.attributes,
            "image_urls": s.image_urls,
            "status": s.status,
            "display_order": s.display_order,
        }
        for s in rows
    ]


@router.post("/services", status_code=201)
def create_business_service(
    payload: BusinessServiceCreate,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict:
    """Create a new service for this business."""
    from decimal import Decimal
    svc = Service(
        tenant_id=tenant.id,
        type=payload.type,
        name=payload.name,
        description=payload.description,
        price=Decimal(str(payload.price)),
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
    return {"id": svc.id, "message": "Service created"}


@router.patch("/services/{service_id}")
def update_business_service(
    service_id: str,
    payload: BusinessServiceUpdate,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict:
    """Update a service (only this tenant's services)."""
    from decimal import Decimal
    svc = db.query(Service).filter(
        Service.id == service_id,
        Service.tenant_id == tenant.id,
    ).one_or_none()
    if svc is None:
        raise HTTPException(status_code=404, detail="Service not found")

    updates = payload.model_dump(exclude_unset=True)
    for k, v in updates.items():
        if k == "price" and v is not None:
            svc.price = Decimal(str(v))
        else:
            setattr(svc, k, v)
    db.commit()
    return {"id": svc.id, "message": "Service updated"}


@router.delete("/services/{service_id}")
def delete_business_service(
    service_id: str,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict:
    """Soft-delete a service (set status=inactive)."""
    svc = db.query(Service).filter(
        Service.id == service_id,
        Service.tenant_id == tenant.id,
    ).one_or_none()
    if svc is None:
        raise HTTPException(status_code=404, detail="Service not found")
    svc.status = "inactive"
    db.commit()
    return {"id": svc.id, "message": "Service deactivated"}


# ---------- Bookings Inbox ----------


@router.get("/bookings")
def list_business_bookings(
    status_filter: str | None = None,
    page: int = 1,
    limit: int = 50,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict:
    """List all bookings received by this business."""
    from sqlalchemy import desc
    q = db.query(Booking).filter(Booking.tenant_id == tenant.id)
    if status_filter:
        q = q.filter(Booking.status == status_filter)
    total = q.count()
    rows = q.order_by(desc(Booking.created_at)).offset((page - 1) * limit).limit(limit).all()

    # Get user emails
    user_ids = list({b.user_id for b in rows})
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    return {
        "total": total,
        "items": [
            {
                "id": b.id,
                "service_name": b.service_name,
                "booking_type": b.booking_type,
                "check_in": str(b.check_in),
                "check_out": str(b.check_out) if b.check_out else None,
                "guests": b.guests,
                "total_amount": str(b.total_amount),
                "currency": b.currency,
                "status": b.status,
                "payment_status": b.payment_status,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "customer_email": (users.get(b.user_id).email if users.get(b.user_id) else None),
                "customer_name": (
                    (users[b.user_id].first_name + " " + users[b.user_id].last_name)
                    if b.user_id in users else None
                ),
            }
            for b in rows
        ],
    }


@router.patch("/bookings/{booking_id}/status")
def update_booking_status(
    booking_id: str,
    payload: dict,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict:
    """Change status of a booking (e.g. confirmed, checked_in, checked_out, cancelled)."""
    new_status = (payload.get("status") or "").strip()
    allowed = {"pending", "confirmed", "checked_in", "checked_out", "cancelled"}
    if new_status not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use one of: {', '.join(allowed)}")
    b = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.tenant_id == tenant.id,
    ).one_or_none()
    if b is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    b.status = new_status
    db.commit()
    return {"id": b.id, "status": b.status}


# ---------- Customers ----------


@router.get("/customers")
def list_business_customers(
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> list[dict]:
    """List distinct customers who have booked with this business."""
    from sqlalchemy import func
    # Get user_ids with booking counts
    rows = (
        db.query(Booking.user_id, func.count(Booking.id).label("cnt"))
        .filter(Booking.tenant_id == tenant.id)
        .group_by(Booking.user_id)
        .order_by(func.count(Booking.id).desc())
        .all()
    )
    if not rows:
        return []
    user_ids = [r[0] for r in rows]
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}
    counts = {r[0]: r[1] for r in rows}
    return [
        {
            "id": uid,
            "email": users[uid].email if uid in users else None,
            "name": (users[uid].first_name + " " + users[uid].last_name) if uid in users else None,
            "phone": users[uid].phone if uid in users else None,
            "language": users[uid].language if uid in users else None,
            "points": users[uid].points if uid in users else 0,
            "tier": users[uid].tier if uid in users else None,
            "bookings_count": counts.get(uid, 0),
        }
        for uid in user_ids
        if uid in users
    ]
