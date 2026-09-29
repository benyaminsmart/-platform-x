"""Public API v1 (Phase 14, Step 3).

Prefix: /api/v1

Authentication: X-API-Key header (tenant-scoped).
The tenant is ALWAYS derived from the API key, never from any header.

Scopes:
  read:services   -> GET /api/v1/services[/{id}]
  read:bookings   -> GET /api/v1/bookings[/{id}]
  read:reviews    -> GET /api/v1/reviews
  read:analytics  -> GET /api/v1/analytics/summary

All endpoints are read-only in this phase.
"""

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.api.deps_api_key import get_api_key, require_scope
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.api_key import APIKey
from app.models.booking import Booking
from app.models.review import Review
from app.models.service import Service
from app.models.tenant import Tenant
from app.services import review_service


router = APIRouter(prefix="/api/v1", tags=["public-api-v1"])


# ---------- Schemas ----------


class MeResponse(BaseModel):
    tenant_id: str
    tenant_slug: str
    tenant_name: str
    key_prefix: str
    scopes: list[str]


class ServiceItem(BaseModel):
    id: str
    type: str
    name: str
    description: str | None
    price: str
    currency: str
    capacity: int | None
    status: str


class PaginatedServices(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ServiceItem]


class BookingItem(BaseModel):
    id: str
    booking_type: str
    service_name: str
    check_in: str
    check_out: str | None
    guests: int
    total_amount: str
    currency: str
    status: str
    payment_status: str
    created_at: str | None


class PaginatedBookings(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[BookingItem]


class ReviewItem(BaseModel):
    id: str
    rating: int
    title: str | None
    content: str
    sentiment: str | None
    language: str
    status: str
    verified: bool
    created_at: str | None


class PaginatedReviews(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ReviewItem]


class AnalyticsSummary(BaseModel):
    period_days: int
    total_bookings: int
    confirmed_bookings: int
    paid_bookings: int
    total_revenue_aed: float
    active_services: int
    published_reviews: int
    avg_rating: float


# ---------- Helpers ----------


def _tenant_of(db: DBSession, api_key: APIKey) -> Tenant:
    t = db.query(Tenant).filter(Tenant.id == api_key.tenant_id).one_or_none()
    if t is None or t.status != "active":
        raise HTTPException(status_code=404, detail="Tenant not found or inactive")
    return t


# ---------- Endpoints ----------


@router.get("/me", response_model=MeResponse)
@limiter.limit("100/minute")
def get_me(
    request: Request,
    api_key: APIKey = Depends(get_api_key),
    db: DBSession = Depends(get_db),
) -> MeResponse:
    t = _tenant_of(db, api_key)
    return MeResponse(
        tenant_id=t.id,
        tenant_slug=t.slug,
        tenant_name=t.name,
        key_prefix=api_key.prefix,
        scopes=list(api_key.scopes or []),
    )


# ---------- Services ----------


@router.get(
    "/services",
    response_model=PaginatedServices,
    dependencies=[Depends(require_scope("read:services"))],
)
@limiter.limit("100/minute")
def list_services(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    api_key: APIKey = Depends(get_api_key),
    db: DBSession = Depends(get_db),
) -> PaginatedServices:
    t = _tenant_of(db, api_key)
    q = db.query(Service).filter(Service.tenant_id == t.id)
    if status_filter:
        q = q.filter(Service.status == status_filter)
    total = q.count()
    rows = (
        q.order_by(Service.display_order, Service.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedServices(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            ServiceItem(
                id=s.id,
                type=s.type,
                name=s.name,
                description=s.description,
                price=str(s.price),
                currency=s.currency,
                capacity=s.capacity,
                status=s.status,
            )
            for s in rows
        ],
    )


@router.get(
    "/services/{service_id}",
    response_model=ServiceItem,
    dependencies=[Depends(require_scope("read:services"))],
)
@limiter.limit("100/minute")
def get_service(
    request: Request,
    service_id: str,
    api_key: APIKey = Depends(get_api_key),
    db: DBSession = Depends(get_db),
) -> ServiceItem:
    t = _tenant_of(db, api_key)
    s = (
        db.query(Service)
        .filter(Service.id == service_id, Service.tenant_id == t.id)
        .one_or_none()
    )
    if s is None:
        raise HTTPException(status_code=404, detail="Service not found")
    return ServiceItem(
        id=s.id,
        type=s.type,
        name=s.name,
        description=s.description,
        price=str(s.price),
        currency=s.currency,
        capacity=s.capacity,
        status=s.status,
    )


# ---------- Bookings ----------


@router.get(
    "/bookings",
    response_model=PaginatedBookings,
    dependencies=[Depends(require_scope("read:bookings"))],
)
@limiter.limit("100/minute")
def list_bookings(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    api_key: APIKey = Depends(get_api_key),
    db: DBSession = Depends(get_db),
) -> PaginatedBookings:
    t = _tenant_of(db, api_key)
    q = db.query(Booking).filter(Booking.tenant_id == t.id)
    if status_filter:
        q = q.filter(Booking.status == status_filter)
    total = q.count()
    rows = (
        q.order_by(Booking.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedBookings(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            BookingItem(
                id=b.id,
                booking_type=b.booking_type,
                service_name=b.service_name,
                check_in=str(b.check_in),
                check_out=str(b.check_out) if b.check_out else None,
                guests=b.guests,
                total_amount=str(b.total_amount),
                currency=b.currency,
                status=b.status,
                payment_status=b.payment_status,
                created_at=b.created_at.isoformat() if b.created_at else None,
            )
            for b in rows
        ],
    )


@router.get(
    "/bookings/{booking_id}",
    response_model=BookingItem,
    dependencies=[Depends(require_scope("read:bookings"))],
)
@limiter.limit("100/minute")
def get_booking(
    request: Request,
    booking_id: str,
    api_key: APIKey = Depends(get_api_key),
    db: DBSession = Depends(get_db),
) -> BookingItem:
    t = _tenant_of(db, api_key)
    b = (
        db.query(Booking)
        .filter(Booking.id == booking_id, Booking.tenant_id == t.id)
        .one_or_none()
    )
    if b is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return BookingItem(
        id=b.id,
        booking_type=b.booking_type,
        service_name=b.service_name,
        check_in=str(b.check_in),
        check_out=str(b.check_out) if b.check_out else None,
        guests=b.guests,
        total_amount=str(b.total_amount),
        currency=b.currency,
        status=b.status,
        payment_status=b.payment_status,
        created_at=b.created_at.isoformat() if b.created_at else None,
    )


# ---------- Reviews ----------


@router.get(
    "/reviews",
    response_model=PaginatedReviews,
    dependencies=[Depends(require_scope("read:reviews"))],
)
@limiter.limit("100/minute")
def list_reviews(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    api_key: APIKey = Depends(get_api_key),
    db: DBSession = Depends(get_db),
) -> PaginatedReviews:
    t = _tenant_of(db, api_key)
    q = db.query(Review).filter(Review.tenant_id == t.id, Review.status == "published")
    total = q.count()
    rows = (
        q.order_by(Review.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedReviews(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            ReviewItem(
                id=r.id,
                rating=r.rating,
                title=r.title,
                content=r.content_polished or r.content,
                sentiment=r.sentiment,
                language=r.language,
                status=r.status,
                verified=r.verified,
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
            for r in rows
        ],
    )


# ---------- Analytics ----------


@router.get(
    "/analytics/summary",
    response_model=AnalyticsSummary,
    dependencies=[Depends(require_scope("read:analytics"))],
)
@limiter.limit("60/minute")
def analytics_summary(
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
    api_key: APIKey = Depends(get_api_key),
    db: DBSession = Depends(get_db),
) -> AnalyticsSummary:
    t = _tenant_of(db, api_key)
    cutoff = date.today() - timedelta(days=days)

    total_bookings = (
        db.query(Booking)
        .filter(Booking.tenant_id == t.id, Booking.check_in >= cutoff)
        .count()
    )
    confirmed = (
        db.query(Booking)
        .filter(
            Booking.tenant_id == t.id,
            Booking.check_in >= cutoff,
            Booking.status == "confirmed",
        )
        .count()
    )
    paid_rows = (
        db.query(Booking)
        .filter(
            Booking.tenant_id == t.id,
            Booking.check_in >= cutoff,
            Booking.payment_status == "paid",
        )
        .all()
    )
    total_revenue = sum(float(b.total_amount or 0) for b in paid_rows)

    active_services = (
        db.query(Service)
        .filter(Service.tenant_id == t.id, Service.status == "active")
        .count()
    )

    rev_summary = review_service.tenant_review_summary(db, t)

    return AnalyticsSummary(
        period_days=days,
        total_bookings=total_bookings,
        confirmed_bookings=confirmed,
        paid_bookings=len(paid_rows),
        total_revenue_aed=round(total_revenue, 2),
        active_services=active_services,
        published_reviews=rev_summary.get("total", 0),
        avg_rating=rev_summary.get("avg_rating", 0.0),
    )
