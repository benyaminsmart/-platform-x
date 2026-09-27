"""Analytics endpoints.

POST /analytics/events — public (frontend tracking); user optional
GET  /analytics/summary — tenant admin view (platform admin for now)
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_tenant
from app.api.deps_admin import get_current_admin
from app.db.session import get_db
from app.models.platform_admin import PlatformAdmin
from app.models.tenant import Tenant
from app.schemas.analytics import AnalyticsEventCreate, AnalyticsEventPublic
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post(
    "/events",
    response_model=AnalyticsEventPublic,
    status_code=status.HTTP_201_CREATED,
)
def track_event(
    payload: AnalyticsEventCreate,
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    db: DBSession = Depends(get_db),
) -> AnalyticsEventPublic:
    """Record an analytics event (public endpoint).

    User attribution is optional; the frontend may send an authenticated
    request later when user_id extraction is wired.
    """
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    event = analytics_service.track(
        db,
        tenant_id=tenant.id,
        event_type=payload.event_type,
        metadata=payload.metadata,
        ip_address=ip,
        user_agent=ua,
    )
    return AnalyticsEventPublic.model_validate(event)


@router.get("/summary")
def tenant_summary(
    tenant: Tenant = Depends(get_current_tenant),
    admin: PlatformAdmin = Depends(get_current_admin),
    db: DBSession = Depends(get_db),
) -> dict:
    """Return top event counts for the current tenant (admin only)."""
    return {
        "tenant_id": tenant.id,
        "total_events": analytics_service.total_events(db, tenant_id=tenant.id),
        "top_events": [
            {"event_type": t, "count": c}
            for t, c in analytics_service.counts_by_type(db, tenant_id=tenant.id)
        ],
    }
