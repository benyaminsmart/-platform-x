"""Partner application endpoints.

Public:
  POST /partners/apply — submit an application

Admin:
  GET /platform/applications — list applications
  PATCH /platform/applications/{id}/status — update status
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session as DBSession

from app.api.deps_admin import get_current_admin, require_role
from app.core.rate_limit import LIMITS, limiter
from app.db.session import get_db
from app.models.platform_admin import PlatformAdmin
from app.schemas.common import PaginatedResponse
from app.schemas.partner import (
    PartnerApplicationCreate,
    PartnerApplicationPublic,
    PartnerApplicationReceived,
)
from app.services import partner_service

router = APIRouter(tags=["partners"])


# ---------- Public ----------


@router.post(
    "/partners/apply",
    response_model=PartnerApplicationReceived,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(LIMITS["partner_apply"])
def submit_application(
    request: Request,
    payload: PartnerApplicationCreate,
    db: DBSession = Depends(get_db),
) -> PartnerApplicationReceived:
    """Submit a partner onboarding application."""
    application = partner_service.create_application(db, payload)
    return PartnerApplicationReceived(
        id=application.id,
        message="Application received. We'll be in touch within 2 business days.",
        email=application.email,
    )


# ---------- Admin ----------


@router.get(
    "/platform/applications",
    response_model=PaginatedResponse[PartnerApplicationPublic],
)
def list_applications(
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    admin: PlatformAdmin = Depends(get_current_admin),
    db: DBSession = Depends(get_db),
) -> PaginatedResponse[PartnerApplicationPublic]:
    """List all partner applications (admin only)."""
    items, total = partner_service.list_applications(
        db, status=status_filter, page=page, limit=limit
    )
    return PaginatedResponse[PartnerApplicationPublic](
        items=[PartnerApplicationPublic.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=limit,
    )
