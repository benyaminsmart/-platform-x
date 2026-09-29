"""Business Marketing API (Phase 25, Step 4).

Prefix: /business/api/marketing

Design:
- Read operations open to all business roles.
- Send + segment-user-list restricted to owner/manager.
- Send is blocked unless EMAIL_ENABLED=true and RESEND_API_KEY is set
  (see app.core.config + app.services.email_service).
- AI is grounded in real tenant data; never invents discounts.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services import email_service
from app.services import marketing as marketing_service
from app.services.ai import campaign_writer, discount_suggester


router = APIRouter(prefix="/business/api/marketing", tags=["business-marketing"])

_WRITE_ROLES = {"owner", "manager"}


# ---------- Schemas ----------


class SegmentInfo(BaseModel):
    name: str
    count: int
    sample_emails: list[str] = []
    top20_threshold_aed: float | None = None


class SegmentsResponse(BaseModel):
    segments: list[SegmentInfo]
    totals: dict[str, Any]


class SegmentCustomersResponse(BaseModel):
    segment: str
    count: int
    emails: list[str]


class LanguageRequest(BaseModel):
    language: str = Field(default="en", pattern="^(en|ar|fil|hi)$")


class GenerateCampaignRequest(BaseModel):
    segment: str
    goal: str = Field(min_length=2, max_length=300)
    language: str = Field(default="en", pattern="^(en|ar|fil|hi)$")


class SuggestDiscountsRequest(BaseModel):
    language: str = Field(default="en", pattern="^(en|ar|fil|hi)$")
    segments: list[str] | None = None


class SendCampaignRequest(BaseModel):
    segment: str
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=8000)
    language: str = Field(default="en", pattern="^(en|ar|fil|hi)$")


class SendCampaignResponse(BaseModel):
    attempted: int
    sent: int
    failed: int
    email_enabled: bool
    dry_run: bool
    note: str | None = None


class MarketingConfigResponse(BaseModel):
    email_enabled: bool
    from_email: str | None = None
    from_name: str | None = None


# ---------- Helpers ----------


def _require_write_role(user: User) -> None:
    if user.business_role not in _WRITE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only owner or manager can perform this action",
        )


# ---------- Endpoints ----------


@router.get("/config", response_model=MarketingConfigResponse)
@limiter.limit("60/minute")
def get_marketing_config(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
) -> MarketingConfigResponse:
    """Return whether real email sending is enabled."""
    enabled = bool(settings.EMAIL_ENABLED and settings.RESEND_API_KEY)
    return MarketingConfigResponse(
        email_enabled=enabled,
        from_email=settings.EMAIL_FROM if enabled else None,
        from_name=settings.EMAIL_FROM_NAME if enabled else None,
    )


@router.get("/segments", response_model=SegmentsResponse)
@limiter.limit("30/minute")
def get_segments(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> SegmentsResponse:
    """Return customer segmentation summary for the current tenant."""
    out = marketing_service.segment_customers(db, tenant)
    segments = [
        SegmentInfo(name=name, **data)
        for name, data in sorted(out["segments"].items())
    ]
    return SegmentsResponse(segments=segments, totals=out["totals"])


@router.get("/segments/{segment}", response_model=SegmentCustomersResponse)
@limiter.limit("20/minute")
def get_segment_users(
    request: Request,
    segment: str,
    limit: int = 200,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> SegmentCustomersResponse:
    """Return the customer emails in a segment (owner/manager only)."""
    _require_write_role(user)
    if segment not in marketing_service.SEGMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"segment must be one of: {', '.join(sorted(marketing_service.SEGMENTS))}",
        )
    rows = marketing_service.get_segment_customers(db, tenant, segment, limit=max(1, min(limit, 500)))
    return SegmentCustomersResponse(
        segment=segment,
        count=len(rows),
        emails=[r["email"] for r in rows],
    )


@router.post("/campaigns/suggest")
@limiter.limit("10/minute")
def suggest_campaigns(
    request: Request,
    payload: LanguageRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict[str, Any]:
    """AI suggests 3-5 grounded campaigns for this tenant."""
    try:
        out = campaign_writer.suggest_campaigns(db, tenant=tenant, language=payload.language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return out


@router.post("/campaigns/generate")
@limiter.limit("10/minute")
def generate_campaign(
    request: Request,
    payload: GenerateCampaignRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict[str, Any]:
    """AI generates one campaign targeted at a specific segment."""
    try:
        out = campaign_writer.generate_campaign(
            db, tenant=tenant,
            segment=payload.segment, goal=payload.goal, language=payload.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return out


@router.post("/discounts/suggest")
@limiter.limit("10/minute")
def suggest_discounts(
    request: Request,
    payload: SuggestDiscountsRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> dict[str, Any]:
    """AI suggests platform-policy-bounded discounts per segment."""
    if payload.segments:
        for s in payload.segments:
            if s not in marketing_service.SEGMENTS:
                raise HTTPException(
                    status_code=400,
                    detail=f"unknown segment: {s}",
                )
    try:
        out = discount_suggester.suggest_discounts(
            db, tenant=tenant, language=payload.language, segment_filter=payload.segments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return out


@router.post("/campaigns/send", response_model=SendCampaignResponse)
@limiter.limit("5/minute")
def send_campaign(
    request: Request,
    payload: SendCampaignRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db: DBSession = Depends(get_db),
) -> SendCampaignResponse:
    """Send a campaign email to a segment.

    Restricted to owner/manager. If EMAIL_ENABLED is false, this is a dry run:
    the endpoint returns 200 with sent=0, dry_run=True, and no emails leave.
    """
    _require_write_role(user)

    if payload.segment not in marketing_service.SEGMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"segment must be one of: {', '.join(sorted(marketing_service.SEGMENTS))}",
        )

    rows = marketing_service.get_segment_customers(db, tenant, payload.segment, limit=500)
    emails = [r["email"] for r in rows if r.get("email")]

    email_on = email_service.is_enabled()

    if not email_on:
        return SendCampaignResponse(
            attempted=len(emails),
            sent=0,
            failed=0,
            email_enabled=False,
            dry_run=True,
            note="Email sending is disabled (EMAIL_ENABLED=false). Configure Resend to send for real.",
        )

    sent = 0
    failed = 0
    for to in emails:
        ok = email_service.send_email(
            to=to,
            subject=payload.subject,
            html=payload.body.replace("\n", "<br>"),
            text=payload.body,
        )
        if ok:
            sent += 1
        else:
            failed += 1

    return SendCampaignResponse(
        attempted=len(emails),
        sent=sent,
        failed=failed,
        email_enabled=True,
        dry_run=False,
        note=None,
    )
