"""Google Gemini provider (stub).

Activate by setting AI_PROVIDER=gemini and GEMINI_API_KEY=xxx.
This implementation is ready; it will only be called when configured.
"""

from app.core.config import settings
from app.services.ai.provider import AIProvider, AIMessage, AIResponse


class GeminiProvider(AIProvider):
    """Google Gemini API adapter."""

    name = "gemini"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = "gemini-2.0-flash"

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
        """Send a chat request to Gemini."""
        if not self.is_available():
            raise RuntimeError("Gemini API key not configured")

        try:
            import google.generativeai as genai  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Install google-generativeai to use Gemini") from exc

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model, system_instruction=system)

        # Build conversation
        contents = []
        for m in messages:
            role = "user" if m.role == "user" else "model"
            contents.append({"role": role, "parts": [m.content]})

        resp = model.generate_content(
            contents,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )
        content = getattr(resp, "text", "") or ""
        return AIResponse(
            content=content,
            provider="gemini",
            model=self.model,
        )
