"""AI provider factory — picks the provider based on config.

Supported providers:
- mock   (default, no API key required)
- gemini (needs GEMINI_API_KEY + google-generativeai installed)
- openai (needs OPENAI_API_KEY + openai installed)

If the requested provider isn't available, fall back to mock so the
platform always responds gracefully.
"""

from functools import lru_cache

from app.core.config import settings
from app.services.ai.mock_provider import MockProvider
from app.services.ai.provider import AIProvider


@lru_cache(maxsize=4)
def get_ai_provider(name: str | None = None) -> AIProvider:
    """Return the configured AI provider (with safe fallback to mock)."""
    chosen = (name or settings.AI_PROVIDER or "mock").lower()

    if chosen == "gemini":
        from app.services.ai.gemini_provider import GeminiProvider
        p = GeminiProvider()
        if p.is_available():
            return p
        # fall through to mock
    if chosen == "openai":
        from app.services.ai.openai_provider import OpenAIProvider
        p = OpenAIProvider()
        if p.is_available():
            return p
        # fall through to mock

    return MockProvider()
