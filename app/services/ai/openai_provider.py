"""OpenAI provider (stub).

Activate by setting AI_PROVIDER=openai and OPENAI_API_KEY=xxx.
"""

from app.core.config import settings
from app.services.ai.provider import AIProvider, AIMessage, AIResponse


class OpenAIProvider(AIProvider):
    """OpenAI Chat Completions adapter."""

    name = "openai"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = "gpt-4o-mini"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def chat(
        self,
        messages: list[AIMessage],
        *,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AIResponse:
        """Send a chat request to OpenAI."""
        if not self.is_available():
            raise RuntimeError("OpenAI API key not configured")

        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Install openai to use OpenAI provider") from exc

        client = OpenAI(api_key=self.api_key)

        api_messages = []
        if system:
            api_messages.append({"role": "system", "content": system})
        for m in messages:
            api_messages.append({"role": m.role, "content": m.content})

        resp = client.chat.completions.create(
            model=self.model,
            messages=api_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content or ""
        tokens = getattr(resp.usage, "total_tokens", 0) if resp.usage else 0
        return AIResponse(
            content=content,
            provider="openai",
            model=self.model,
            tokens_used=tokens,
        )
