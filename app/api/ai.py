"""AI endpoints — chat and health.

Public:
  POST /ai/chat        — public chat (guests)
  GET  /ai/health      — health check

Business:
  POST /business/api/ai/chat  — business-scoped (stricter rate limit)
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.config import settings
from app.core.rate_limit import LIMITS, limiter
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai import service as ai_service

router = APIRouter(prefix="/ai", tags=["ai"])
business_router = APIRouter(prefix="/business/api/ai", tags=["business-ai"])


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


def _require_ai_enabled() -> None:
    if not settings.AI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI is currently disabled",
        )


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
    history = [h.model_dump() for h in payload.history][-10:]  # last 10 messages
    result = ai_service.chat(payload.message, history=history)
    return ChatResponse(**result)


@business_router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
def business_ai_chat(
    request: Request,
    payload: ChatRequest,
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
) -> ChatResponse:
    """Business-scoped AI chat."""
    _require_ai_enabled()
    history = [h.model_dump() for h in payload.history][-10:]
    # Prepend business context (mocked for now)
    context_msg = f"[Business context: {tenant.name} ({tenant.slug})]"
    result = ai_service.chat(
        payload.message,
        history=[{"role": "user", "content": context_msg}] + history,
    )
    return ChatResponse(**result)
