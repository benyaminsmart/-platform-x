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
