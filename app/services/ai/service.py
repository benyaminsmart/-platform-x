"""High-level AI service for Platform-X.

Provides simple functions for chat and common tasks.
Uses the factory to pick the configured provider.
"""

from app.services.ai.factory import get_ai_provider
from app.services.ai.provider import AIMessage

SYSTEM_PROMPT = """You are Platform-X Assistant and AI Concierge.

Platform-X is a multi-tenant platform connecting hotels, restaurants,
travel agencies, and entertainment venues.

You help:
- Guests: discover and book experiences, check their bookings, understand rewards.
- Business owners: manage services, understand pricing, improve their listing.

As an AI Concierge, you also help guests DURING their trip:
- Recommend nearby restaurants or activities when asked
- Suggest what to do at different times of day
- Help find specific cuisines, amenities, or experiences
- Adapt suggestions to the guest location

Keep replies short, helpful, and friendly. Suggest concrete actions
with platform routes like /hotels, /restaurants, /travel, /entertainment,
/account, /partners/apply, /business/login.
"""


def chat(
    message: str,
    *,
    history: list[dict] | None = None,
    provider_name: str | None = None,
) -> dict:
    """Send a message to the AI and return the response."""
    provider = get_ai_provider(provider_name)

    messages: list[AIMessage] = []
    if history:
        for h in history:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append(AIMessage(role=role, content=content))

    messages.append(AIMessage(role="user", content=message))

    # Use chat_simple if provider supports it (gemini), else fallback to chat
    if hasattr(provider, "chat_simple"):
        response = provider.chat_simple(messages, system=SYSTEM_PROMPT)
        return {
            "content": response.content,
            "provider": response.provider,
            "model": response.model,
            "tokens_used": response.tokens_used,
        }

    response = provider.chat(messages, system=SYSTEM_PROMPT)
    return {
        "content": response.content,
        "provider": response.provider,
        "model": response.model,
        "tokens_used": response.tokens_used,
    }


def health() -> dict:
    """Return AI subsystem health."""
    provider = get_ai_provider()
    return {
        "enabled": True,
        "provider": provider.name,
        "available": provider.is_available(),
    }
