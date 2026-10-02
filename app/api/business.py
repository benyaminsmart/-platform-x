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


# ---------- Staff Management ----------


import secrets as _secrets  # noqa: E402


@router.get("/staff")
def list_business_staff(
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> list[dict]:
    """List staff members (business_role set) of this tenant."""
    rows = db.query(User).filter(
        User.tenant_id == tenant.id,
        User.business_role.isnot(None),
    ).order_by(User.created_at).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "business_role": u.business_role,
            "status": u.status,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in rows
    ]


@router.post("/staff", status_code=201)
def create_business_staff(
    payload: dict,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict:
    """Create a new staff account under this business (owner only)."""
    from app.core.security import hash_password

    if user.business_role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can add staff")

    email = (payload.get("email") or "").lower().strip()
    password = payload.get("password") or ""
    first_name = (payload.get("first_name") or "").strip()
    last_name = (payload.get("last_name") or "").strip()
    role = (payload.get("business_role") or "staff").strip()

    if not email or not password or not first_name or not last_name:
        raise HTTPException(status_code=400, detail="email, password, first_name, last_name required")
    if role not in {"manager", "staff"}:
        raise HTTPException(status_code=400, detail="business_role must be manager or staff")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    existing = db.query(User).filter(
        User.tenant_id == tenant.id,
        User.email == email,
    ).one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered for this business")

    new_user = User(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        business_role=role,
        referral_code=_secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:10].upper(),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "message": "Staff account created"}


@router.delete("/staff/{staff_id}")
def delete_business_staff(
    staff_id: str,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict:
    """Deactivate a staff account (owner only). Cannot deactivate self."""
    if user.business_role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can manage staff")
    if staff_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    target = db.query(User).filter(
        User.id == staff_id,
        User.tenant_id == tenant.id,
        User.business_role.isnot(None),
    ).one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Staff not found")
    target.status = "suspended"
    db.commit()
    return {"id": target.id, "message": "Staff deactivated"}

# ---------- Business Settings (Phase 66, Step 1) ----------

from pydantic import BaseModel as _BM, Field as _F


class SettingsResponse(_BM):
    slug: str
    name: str
    tagline: str | None = None
    location: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    currency: str | None = None
    default_language: str | None = None
    languages: list[str] = []
    amenities: list[str] = []
    branding: dict = {}
    hours: dict = {}


class SettingsUpdate(_BM):
    tagline: str | None = _F(default=None, max_length=300)
    location: str | None = _F(default=None, max_length=200)
    phone: str | None = _F(default=None, max_length=40)
    email: str | None = _F(default=None, max_length=255)
    website: str | None = _F(default=None, max_length=300)
    currency: str | None = _F(default=None, max_length=10)
    default_language: str | None = _F(default=None, max_length=10)
    languages: list[str] | None = None
    amenities: list[str] | None = None
    branding: dict | None = None
    hours: dict | None = None


def _config_to_response(tenant: Tenant) -> SettingsResponse:
    cfg = tenant.config or {}
    contact = cfg.get("contact") or {}
    return SettingsResponse(
        slug=tenant.slug,
        name=tenant.name,
        tagline=cfg.get("tagline"),
        location=cfg.get("location"),
        phone=contact.get("phone"),
        email=contact.get("email"),
        website=contact.get("website"),
        currency=cfg.get("currency"),
        default_language=cfg.get("default_language"),
        languages=cfg.get("languages") or [],
        amenities=cfg.get("amenities") or [],
        branding=cfg.get("branding") or {},
        hours=cfg.get("hours") or {},
    )


@router.get("/settings", response_model=SettingsResponse)
def get_business_settings(
    tenant: Tenant = Depends(get_business_tenant),
    user: User = Depends(get_current_business_user),
) -> SettingsResponse:
    return _config_to_response(tenant)


@router.patch("/settings", response_model=SettingsResponse)
def update_business_settings(
    payload: SettingsUpdate,
    tenant: Tenant = Depends(get_business_tenant),
    user: User = Depends(get_current_business_user),
    db: DBSession = Depends(get_db),
) -> SettingsResponse:
    if user.business_role not in {"owner", "manager"}:
        raise HTTPException(status_code=403, detail="Only owner or manager can update settings")

    cfg = dict(tenant.config or {})
    contact = dict(cfg.get("contact") or {})

    data = payload.model_dump(exclude_unset=True)
    if "tagline" in data:
        cfg["tagline"] = data["tagline"]
    if "location" in data:
        cfg["location"] = data["location"]
    if "currency" in data:
        cfg["currency"] = data["currency"]
    if "default_language" in data:
        cfg["default_language"] = data["default_language"]
    if "languages" in data:
        cfg["languages"] = data["languages"]
    if "amenities" in data:
        cfg["amenities"] = data["amenities"]
    if "branding" in data:
        cfg["branding"] = data["branding"] or {}
    if "hours" in data:
        cfg["hours"] = data["hours"] or {}
    if "phone" in data:
        contact["phone"] = data["phone"]
    if "email" in data:
        contact["email"] = data["email"]
    if "website" in data:
        contact["website"] = data["website"]
    cfg["contact"] = contact

    tenant.config = cfg
    db.commit()
    db.refresh(tenant)
    return _config_to_response(tenant)

