"""Google Gemini provider — via Interactions API (REST).

Uses the new Interactions endpoint (v1beta/interactions).
Activate by setting AI_PROVIDER=gemini and GEMINI_API_KEY=xxx.
"""

import requests

from app.core.config import settings
from app.services.ai.provider import AIProvider, AIMessage, AIResponse


class GeminiProvider(AIProvider):
    """Google Gemini API adapter (Interactions API)."""

    name = "gemini"
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = (api_key or settings.GEMINI_API_KEY).strip()
        self.model = "gemini-3.1-flash-lite"

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
        """Send a chat request to Gemini via Interactions API."""
        if not self.is_available():
            raise RuntimeError("Gemini API key not configured")

        # Build input as a list of content blocks
        # The Interactions API takes either a single text input, or a list of user_input messages.
        # For simplicity, we send the last user message as input and prefix system + history as text.
        history_text = ""
        last_user_text = ""
        for m in messages:
            if m.role == "user":
                last_user_text = m.content
            elif m.role == "assistant":
                history_text += f"Assistant: {m.content}\n"

        if history_text:
            full_input = f"Conversation so far:\n{history_text}\nUser: {last_user_text}"
        else:
            full_input = last_user_text

        if system:
            full_input = f"[System instructions: {system}]\n\n{full_input}"

        payload = {
            "model": self.model,
            "input": full_input,
        }

        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(
                self.BASE_URL,
                json=payload,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            body = ""
            if hasattr(exc, "response") and exc.response is not None:
                try:
                    body = exc.response.text[:300]
                except Exception:
                    pass
            raise RuntimeError(f"Gemini request failed: {exc} | {body}") from exc

        content = self._extract_text(data)
        usage = data.get("usage", {})
        tokens = usage.get("total_tokens", 0)

        return AIResponse(
            content=content,
            provider="gemini",
            model=self.model,
            tokens_used=tokens,
        )

    @staticmethod
    def _extract_text(data: dict) -> str:
        """Extract the assistant text from the Interactions response."""
        # Preferred: use output_text if present
        if isinstance(data.get("output_text"), str):
            return data["output_text"]

        # Otherwise, walk steps
        parts = []
        for step in data.get("steps", []):
            if step.get("type") == "model_output":
                for block in step.get("content", []):
                    if block.get("type") == "text":
                        parts.append(block.get("text", ""))
        return "".join(parts) or "(no response)"
