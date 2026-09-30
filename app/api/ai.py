"""AI endpoints — chat, pricing coach, demand forecast, market insights.

Public (Layer 1):
  GET  /ai/health      — health check
  POST /ai/chat        — public chat (guests)

Business (Layer 3):
  POST /business/api/ai/chat             — business-scoped chat
  POST /business/api/ai/pricing/analyze  — pricing analysis (metrics + AI advice)
  POST /business/api/ai/pricing/suggest  — pricing suggestions (deterministic + AI rationale)
  POST /business/api/ai/demand/forecast  — 30-day demand forecast
  POST /business/api/ai/insights         — anonymized market insights

Design principle: numbers are computed in Python from real DB data.
The AI is used ONLY as an interpreter/advisor, grounded in those numbers.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai import pricing_coach
from app.services.ai import service as ai_service
from app.services.ai.business_context import build_business_context, context_to_prompt

router = APIRouter(prefix="/ai", tags=["ai"])
business_router = APIRouter(prefix="/business/api/ai", tags=["business-ai"])


# ---------- Schemas ----------


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    content: str
    provider: str
    model: str | None = None
    tokens_used: int = 0


class CoachResponse(BaseModel):
    """Structured response: deterministic metrics + AI advice."""
    metrics: dict[str, Any]
    advice: str


# ---------- Helpers ----------


def _require_ai_enabled() -> None:
    if not settings.AI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI is currently disabled",
        )


# ---------- Public (Layer 1) ----------


@router.get("/health")
def ai_health() -> dict[str, Any]:
    """AI health check."""
    return ai_service.health()


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
def ai_chat(
    request: Request,
    payload: ChatRequest,
) -> ChatResponse:
    """Public AI chat for guests."""
    _require_ai_enabled()
    history = [h.model_dump() for h in payload.history][-10:]
    result = ai_service.chat(payload.message, history=history)
    return ChatResponse(**result)


# ---------- Business (Layer 3) ----------


@business_router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
def business_ai_chat(
    request: Request,
    payload: ChatRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db=Depends(get_db),
) -> ChatResponse:
    """Business-scoped AI chat with REAL grounded context from the tenant."""
    _require_ai_enabled()
    history = [h.model_dump() for h in payload.history][-10:]

    # Inject real business context (Phase 21, Step 1)
    ctx = build_business_context(db, tenant)
    context_block = (
        "You are the AI assistant for the following business. Ground all "
        "answers in this data. Never invent numbers or competitor names.\n\n"
        + context_to_prompt(ctx)
    )

    result = ai_service.chat(
        payload.message,
        history=[{"role": "user", "content": context_block}] + history,
    )
    return ChatResponse(**result)


@business_router.post("/pricing/analyze", response_model=CoachResponse)
@limiter.limit("20/minute")
def business_pricing_analyze(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db=Depends(get_db),
) -> CoachResponse:
    """Analyze current pricing: per-type stats + position vs anonymized cohort."""
    _require_ai_enabled()
    out = pricing_coach.analyze_pricing(db, tenant)
    return CoachResponse(**out)


@business_router.post("/pricing/suggest", response_model=CoachResponse)
@limiter.limit("20/minute")
def business_pricing_suggest(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db=Depends(get_db),
) -> CoachResponse:
    """Deterministic pricing suggestions + AI rationale."""
    _require_ai_enabled()
    out = pricing_coach.suggest_pricing(db, tenant)
    return CoachResponse(**out)


@business_router.post("/demand/forecast", response_model=CoachResponse)
@limiter.limit("20/minute")
def business_demand_forecast(
    request: Request,
    days: int = 30,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db=Depends(get_db),
) -> CoachResponse:
    """30-day (adjustable 7-90) demand forecast + AI interpretation."""
    _require_ai_enabled()
    out = pricing_coach.forecast_demand(db, tenant, days=days)
    return CoachResponse(**out)


@business_router.post("/insights", response_model=CoachResponse)
@limiter.limit("20/minute")
def business_market_insights(
    request: Request,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db=Depends(get_db),
) -> CoachResponse:
    """Anonymized platform market insights for this business's category."""
    _require_ai_enabled()
    out = pricing_coach.market_insights(db, tenant)
    return CoachResponse(**out)


# ---------- Content Writer (Phase 23) ----------


class ContentWriteRequest(BaseModel):
    language: str = Field(default="en", pattern="^(en|ar|fil|hi)$")
    tone: str = Field(default="professional", pattern="^(professional|friendly|luxury|playful)$")


class ServiceDescriptionResponse(BaseModel):
    description: str
    language: str
    tone: str
    provider: str


class TaglineResponse(BaseModel):
    tagline: str
    language: str
    provider: str


class ImageKeywordsResponse(BaseModel):
    keywords: list[str]
    query: str
    unsplash_search_url: str
    unsplash_source_url: str


class ApplyDescriptionRequest(ContentWriteRequest):
    """Generate a description and save it to the service."""


def _get_tenant_service(db, tenant: Tenant, service_id: str) -> Service:
    s = (
        db.query(Service)
        .filter(Service.id == service_id, Service.tenant_id == tenant.id)
        .one_or_none()
    )
    if s is None:
        raise HTTPException(status_code=404, detail="Service not found")
    return s


@business_router.post(
    "/content/service/{service_id}",
    response_model=ServiceDescriptionResponse,
)
@limiter.limit("15/minute")
def business_generate_service_description(
    request: Request,
    service_id: str,
    payload: ContentWriteRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db=Depends(get_db),
) -> ServiceDescriptionResponse:
    """Generate an appealing description for a service (does not save)."""
    from app.services.ai import content_writer

    _require_ai_enabled()
    service = _get_tenant_service(db, tenant, service_id)

    try:
        out = content_writer.write_service_description(
            db, tenant=tenant, service=service,
            language=payload.language, tone=payload.tone,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ServiceDescriptionResponse(**out)


@business_router.post(
    "/content/service/{service_id}/apply",
    response_model=ServiceDescriptionResponse,
)
@limiter.limit("15/minute")
def business_apply_service_description(
    request: Request,
    service_id: str,
    payload: ContentWriteRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db=Depends(get_db),
) -> ServiceDescriptionResponse:
    """Generate a description and SAVE it to the service.

    Restricted to owner/manager.
    """
    from app.services.ai import content_writer

    _require_ai_enabled()
    if user.business_role not in {"owner", "manager"}:
        raise HTTPException(status_code=403, detail="Only owner or manager can save content")

    service = _get_tenant_service(db, tenant, service_id)

    try:
        out = content_writer.write_service_description(
            db, tenant=tenant, service=service,
            language=payload.language, tone=payload.tone,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    service.description = out["description"]
    db.commit()
    return ServiceDescriptionResponse(**out)


@business_router.post("/content/tagline", response_model=TaglineResponse)
@limiter.limit("15/minute")
def business_generate_tagline(
    request: Request,
    payload: ContentWriteRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db=Depends(get_db),
) -> TaglineResponse:
    """Generate a tagline for the current business (does not save)."""
    from app.services.ai import content_writer

    _require_ai_enabled()
    try:
        out = content_writer.write_business_tagline(
            db, tenant=tenant, language=payload.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TaglineResponse(tagline=out["tagline"], language=out["language"], provider="ai")


@business_router.post(
    "/content/image-keywords/{service_id}",
    response_model=ImageKeywordsResponse,
)
@limiter.limit("30/minute")
def business_suggest_image_keywords(
    request: Request,
    service_id: str,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db=Depends(get_db),
) -> ImageKeywordsResponse:
    """Suggest image keywords + Unsplash URLs for a service (no external call)."""
    from app.services.ai import content_writer

    service = _get_tenant_service(db, tenant, service_id)
    out = content_writer.suggest_image_keywords(tenant, service)
    return ImageKeywordsResponse(**out)


# ---------- Content Importer (Phase 23, Step 3) ----------


class ImportTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    default_type: str = Field(default="room", max_length=50)
    language: str = Field(default="en", pattern="^(en|ar|fil|hi)$")


class ImportCandidate(BaseModel):
    name: str
    type: str
    description: str | None = None
    price: str | None = None
    currency: str = "AED"
    capacity: int | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class ImportPreviewResponse(BaseModel):
    candidates: list[ImportCandidate]
    provider: str
    count: int


class ImportBulkCreateRequest(BaseModel):
    candidates: list[ImportCandidate] = Field(min_length=1, max_length=100)


class ImportBulkCreateResponse(BaseModel):
    created: int
    skipped: list[dict[str, Any]]
    service_ids: list[str]


@business_router.post(
    "/content/import/preview",
    response_model=ImportPreviewResponse,
)
@limiter.limit("10/minute")
def business_content_import_preview(
    request: Request,
    payload: ImportTextRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db=Depends(get_db),
) -> ImportPreviewResponse:
    """Parse free text into candidate services (preview, no DB writes)."""
    from app.services.ai import content_importer

    _require_ai_enabled()
    try:
        out = content_importer.parse_services_from_text(
            db, tenant=tenant,
            text=payload.text,
            default_type=payload.default_type,
            language=payload.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ImportPreviewResponse(**out)


@business_router.post(
    "/content/import/create",
    response_model=ImportBulkCreateResponse,
)
@limiter.limit("10/minute")
def business_content_import_create(
    request: Request,
    payload: ImportBulkCreateRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db=Depends(get_db),
) -> ImportBulkCreateResponse:
    """Create services from a list of candidates (owner/manager only)."""
    from app.services.ai import content_importer

    if user.business_role not in {"owner", "manager"}:
        raise HTTPException(status_code=403, detail="Only owner or manager can import services")

    out = content_importer.bulk_create_services(
        db, tenant=tenant,
        candidates=[c.model_dump() for c in payload.candidates],
        user_id=user.id,
    )
    return ImportBulkCreateResponse(**out)

# ---------- AI Location Recommender (Phase 45, Step 2) ----------


class LocationRecommendRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    radius_km: float = Field(default=10.0, ge=0.1, le=200)
    category: str | None = Field(default=None, max_length=50)
    language: str = Field(default="en", pattern="^(en|ar|fil|hi)$")


class LocationRecommendResponse(BaseModel):
    attractions: list[dict]
    services: list[dict]
    advice: str
    provider: str


@router.post("/location/recommend", response_model=LocationRecommendResponse)
@limiter.limit("15/minute")
def ai_location_recommend(
    request: Request,
    payload: LocationRecommendRequest,
    db=Depends(get_db),
) -> LocationRecommendResponse:
    """AI-powered location recommendation (public)."""
    from app.services.ai import location_recommender
    from app.api.deps import get_current_user as _gcu
    _require_ai_enabled()

    # Optional: detect authenticated user via header (best-effort, no dependency)
    user_id = None
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            from app.core.security import decode_access_token
            token = auth.split(" ", 1)[1].strip()
            data = decode_access_token(token)
            user_id = data.get("sub")
        except Exception:
            user_id = None

    try:
        out = location_recommender.recommend(
            db,
            lat=payload.lat, lng=payload.lng, radius_km=payload.radius_km,
            category=payload.category, user_id=user_id, language=payload.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LocationRecommendResponse(**out)

