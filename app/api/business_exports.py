"""Business exports API (Phase 34, Step 1).

Prefix: /business/api/exports
All endpoints require business auth. Owner/manager only.

NOTE: no 'from __future__ import annotations'.
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session as DBSession

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services import reports_service


router = APIRouter(prefix="/business/api/exports", tags=["business-exports"])

_WRITE_ROLES = {"owner", "manager"}


def _require(user: User) -> None:
    if user.business_role not in _WRITE_ROLES:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Only owner or manager can export")


def _csv_response(text: str, filename: str) -> Response:
    return Response(
        content=text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/bookings.csv")
@limiter.limit("10/minute")
def export_bookings(
    request: Request,
    days: int = Query(default=90, ge=1, le=3650),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> Response:
    _require(user)
    text = reports_service.bookings_csv(db, tenant, days=days)
    return _csv_response(text, f"bookings-{tenant.slug}.csv")


@router.get("/customers.csv")
@limiter.limit("10/minute")
def export_customers(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> Response:
    _require(user)
    text = reports_service.customers_csv(db, tenant)
    return _csv_response(text, f"customers-{tenant.slug}.csv")


@router.get("/revenue.csv")
@limiter.limit("10/minute")
def export_revenue(
    request: Request,
    days: int = Query(default=90, ge=1, le=3650),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> Response:
    _require(user)
    text = reports_service.revenue_summary_csv(db, tenant, days=days)
    return _csv_response(text, f"revenue-{tenant.slug}.csv")
