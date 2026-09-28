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
