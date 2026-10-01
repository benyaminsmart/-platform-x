"""User AI endpoints — Layer 2 (Account-scoped AI)."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user, get_user_home_tenant
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.ai_chat import AIChatMessage
from app.models.service import Service
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
    tenant: Tenant = Depends(get_user_home_tenant),
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
    tenant: Tenant = Depends(get_user_home_tenant),
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
    tenant: Tenant = Depends(get_user_home_tenant),
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


class PlanRequest(BaseModel):
    """Request a multi-day travel plan."""
    destination: str = Field(min_length=2, max_length=100)
    days: int = Field(ge=1, le=14)
    budget: float | None = Field(default=None, ge=0)
    currency: str = Field(default="AED", max_length=10)
    preferences: str | None = Field(default=None, max_length=500)


class PlanResponse(BaseModel):
    plan: str
    provider: str
    model: str | None = None
    tokens_used: int = 0
    suggestions: list[dict] = []


@router.post("/plan", response_model=PlanResponse)
@limiter.limit("10/minute")
def account_ai_plan(
    request: Request,
    payload: PlanRequest,
    tenant: Tenant = Depends(get_user_home_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> PlanResponse:
    """Generate a multi-day travel itinerary."""
    if not settings.AI_ENABLED:
        raise HTTPException(status_code=503, detail="AI disabled")

    # Gather available businesses as context
    services = (
        db.query(Service)
        .filter(Service.tenant_id == tenant.id, Service.status == "active")
        .limit(20)
        .all()
    )
    services_text = "\n".join(
        f"- {s.type}: {s.name} ({s.price} {s.currency})" for s in services
    )

    prompt = f"""Create a {payload.days}-day travel plan for {payload.destination}.
Budget: {payload.budget or 'flexible'} {payload.currency}.
User preferences: {payload.preferences or 'none specified'}.

Available on Platform-X (for reference only — suggest similar):
{services_text or 'No services listed'}

Format the plan clearly with:
- Day 1, Day 2, etc.
- Hotel suggestion for the stay
- Morning / Afternoon / Evening activities
- Restaurant suggestions
- Estimated total cost

Keep it concise. 4-6 lines per day."""

    result = ai_service.chat(prompt)

    # Save to history
    db.add(AIChatMessage(
        tenant_id=tenant.id,
        user_id=user.id,
        layer="user",
        role="user",
        content=f"[Travel Plan Request] {payload.days} days in {payload.destination}",
    ))
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

    return PlanResponse(
        plan=result["content"],
        provider=result["provider"],
        model=result.get("model"),
        tokens_used=result.get("tokens_used", 0),
    )


class BookRequest(BaseModel):
    """Request to book via AI."""
    message: str = Field(min_length=2, max_length=2000)


class BookResponse(BaseModel):
    content: str
    provider: str
    booking_id: str | None = None
    booking_created: bool = False
    tokens_used: int = 0


@router.post("/book", response_model=BookResponse)
@limiter.limit("10/minute")
def account_ai_book(
    request: Request,
    payload: BookRequest,
    tenant: Tenant = Depends(get_user_home_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> BookResponse:
    """AI Booking Agent — natural language → real booking.

    Flow:
    1. Send user's message to Gemini with the book_service tool.
    2. If Gemini calls the tool → execute booking.
    3. Send result back to Gemini for final reply.
    """
    if not settings.AI_ENABLED:
        raise HTTPException(status_code=503, detail="AI disabled")

    from app.core.config import settings as _s
    if _s.AI_PROVIDER != "gemini":
        raise HTTPException(status_code=503, detail="Booking agent requires Gemini provider")

    from app.services.ai.booking_tool import BOOKING_TOOL, BookingToolError, execute_book_service
    from app.services.ai.factory import get_ai_provider
    from app.services.ai.provider import AIMessage

    provider = get_ai_provider()
    system = (
        "You are Platform-X Booking Agent. When the user asks to book a service, "
        "collect the service name, check-in date (YYYY-MM-DD), check-out date if applicable, "
        "and number of guests. Only call the book_service tool once you have these details. "
        "If some details are missing, ask for them first. "
        "Available service names for this tenant: " +
        ", ".join([s.name for s in db.query(Service).filter(Service.tenant_id == tenant.id).limit(10)])
    )

    messages = [AIMessage(role="user", content=payload.message)]

    try:
        # First call — may return function_call
        data = provider.chat(messages, system=system, tools=[BOOKING_TOOL])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI error: {exc}") from exc

    interaction_id = data.get("id")
    function_calls = provider.extract_function_calls(data)

    if not function_calls:
        # No tool call — just return the text (AI is asking for more info)
        return BookResponse(
            content=provider._extract_text(data),
            provider="gemini",
            tokens_used=data.get("usage", {}).get("total_tokens", 0),
        )

    # Execute the (first) tool call
    call = function_calls[0]
    try:
        result = execute_book_service(db, tenant_id=tenant.id, user=user, args=call["arguments"])
    except BookingToolError as exc:
        result = {"ok": False, "error": str(exc)}

    # Send result back to Gemini for final reply
    try:
        final_data = provider.continue_with_function_result(
            previous_interaction_id=interaction_id,
            call_id=call["id"],
            name=call["name"],
            result=result,
            tools=[BOOKING_TOOL],
            system=system,
        )
        final_text = provider._extract_text(final_data)
        tokens = final_data.get("usage", {}).get("total_tokens", 0)
    except Exception as exc:
        final_text = (
            f"Booking created. ID: {result.get('booking_id')}. "
            f"Total: {result.get('total')} {result.get('currency')}. "
            "Please proceed to payment."
        ) if result.get("ok") else f"Could not book: {result.get('error')}"
        tokens = 0

    # Save to history
    db.add(AIChatMessage(
        tenant_id=tenant.id, user_id=user.id, layer="user",
        role="user", content=payload.message,
    ))
    db.add(AIChatMessage(
        tenant_id=tenant.id, user_id=user.id, layer="user",
        role="assistant", content=final_text, provider="gemini", tokens_used=tokens,
    ))
    db.commit()

    return BookResponse(
        content=final_text,
        provider="gemini",
        booking_id=result.get("booking_id") if result.get("ok") else None,
        booking_created=bool(result.get("ok")),
        tokens_used=tokens,
    )


# ---------- AI Trip Memory (Phase 46, Step 2) ----------


class TripMemoryResponse(BaseModel):
    profile: dict
    recap: str
    suggestions: list[dict] = []
    provider: str


@router.get("/memory", response_model=TripMemoryResponse)
@limiter.limit("30/minute")
def account_ai_memory(
    request: Request,
    language: str = "en",
    tenant: Tenant = Depends(get_user_home_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> TripMemoryResponse:
    """Return the user's AI Trip Memory profile + personalized recap."""
    if not settings.AI_ENABLED:
        raise HTTPException(status_code=503, detail="AI disabled")
    if language not in {"en", "ar", "fil", "hi"}:
        raise HTTPException(status_code=422, detail="Unsupported language")

    from app.services.ai import trip_memory
    try:
        out = trip_memory.summarize(db, user_id=user.id, language=language)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return TripMemoryResponse(**out)

# ---------- AI Voice Booking (Phase 64, Step 2) ----------


class VoiceRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=4000)
    language: str = Field(default="en", pattern="^(en|ar|fil|hi)$")


class VoiceIntent(BaseModel):
    category: str | None = None
    city: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    guests: int | None = None
    raw: str = ""


class VoiceMatch(BaseModel):
    service_id: str
    service_name: str
    tenant_slug: str
    tenant_name: str
    price: float
    currency: str
    category: str | None = None
    rating: float | None = None


class VoiceResponse(BaseModel):
    status: str
    intent: dict
    matches: list[dict] = []
    reply: str
    provider: str


@router.post("/voice", response_model=VoiceResponse)
@limiter.limit("15/minute")
def account_ai_voice(
    request: Request,
    payload: VoiceRequest,
    tenant: Tenant = Depends(get_user_home_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> VoiceResponse:
    """Parse a spoken (transcribed) booking request.

    Mock integration: user sends text. Real voice→text is deferred.
    Read-only: does not create a Booking.
    """
    if not settings.AI_ENABLED:
        raise HTTPException(status_code=503, detail="AI disabled")

    from app.services.ai import voice_booking
    try:
        out = voice_booking.voice_request(
            db, transcript=payload.transcript, language=payload.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return VoiceResponse(**out)

