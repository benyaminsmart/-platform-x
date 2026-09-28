"""AI provider factory — picks the provider based on config.

Currently only mock is implemented. Real providers (Gemini, OpenAI)
will be added here without changing the rest of the app.
"""

from functools import lru_cache

from app.core.config import settings
from app.services.ai.mock_provider import MockProvider
from app.services.ai.provider import AIProvider


@lru_cache(maxsize=4)
def get_ai_provider(name: str | None = None) -> AIProvider:
    """Return the configured AI provider."""
    chosen = (name or settings.AI_PROVIDER or "mock").lower()

    if chosen == "mock":
        return MockProvider()

    # Fallback: future providers land here. Right now everything is mock.
    # if chosen == "gemini": return GeminiProvider(api_key=settings.GEMINI_API_KEY)
    # if chosen == "openai": return OpenAIProvider(api_key=settings.OPENAI_API_KEY)

    return MockProvider()
