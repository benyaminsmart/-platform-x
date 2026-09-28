"""User AI endpoints — Layer 2 (Account-scoped AI)."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_tenant, get_current_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.ai_chat import AIChatMessage
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai import service as ai_service

router = APIRouter(prefix="/account/api/ai", tags=["account-ai"])


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    use_history: bool = True


class ChatResponse(BaseModel):
    content: str
    provider: str
    model: str | None = None
    tokens_used: int = 0


@router.get("/history")
def get_history(
    limit: int = 50,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[dict]:
    """Return the last N messages (user + assistant)."""
    rows = (
        db.query(AIChatMessage)
        .filter(
            AIChatMessage.tenant_id == tenant.id,
            AIChatMessage.user_id == user.id,
            AIChatMessage.layer == "user",
        )
        .order_by(AIChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "provider": m.provider,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
    ]


@router.delete("/history")
def clear_history(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> dict:
    """Clear the user's AI chat history."""
    db.query(AIChatMessage).filter(
        AIChatMessage.tenant_id == tenant.id,
        AIChatMessage.user_id == user.id,
        AIChatMessage.layer == "user",
    ).delete()
    db.commit()
    return {"message": "History cleared"}


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
def account_ai_chat(
    request: Request,
    payload: ChatRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ChatResponse:
    """AI chat with user context (bookings, rewards, language)."""
    if not settings.AI_ENABLED:
        raise HTTPException(status_code=503, detail="AI disabled")

    # Load history from DB if requested
    history: list[dict] = []
    if payload.use_history:
        rows = (
            db.query(AIChatMessage)
            .filter(
                AIChatMessage.tenant_id == tenant.id,
                AIChatMessage.user_id == user.id,
                AIChatMessage.layer == "user",
            )
            .order_by(AIChatMessage.created_at.desc())
            .limit(10)
            .all()
        )
        rows.reverse()
        history = [{"role": m.role, "content": m.content} for m in rows]

    # Save user message
    db.add(AIChatMessage(
        tenant_id=tenant.id,
        user_id=user.id,
        layer="user",
        role="user",
        content=payload.message,
    ))
    db.commit()

    # Build context prompt
    context_prompt = (
        f"[User context] name={user.first_name} {user.last_name}, "
        f"language={user.language}, points={user.points}, tier={user.tier}, "
        f"tenant={tenant.name}"
    )

    # Call AI
    result = ai_service.chat(
        payload.message,
        history=[{"role": "user", "content": context_prompt}] + history,
    )

    # Save assistant message
    db.add(AIChatMessage(
        tenant_id=tenant.id,
        user_id=user.id,
        layer="user",
        role="assistant",
        content=result["content"],
        provider=result.get("provider"),
        tokens_used=result.get("tokens_used", 0),
    ))
    db.commit()

    return ChatResponse(**result)
