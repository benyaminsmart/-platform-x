"""Google Gemini provider — via Interactions API (REST) with tools support."""

import json
import requests

from app.core.config import settings
from app.services.ai.provider import AIProvider, AIMessage, AIResponse


class GeminiProvider(AIProvider):
    """Google Gemini API adapter (Interactions API + function calling)."""

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
        tools: list[dict] | None = None,
    ) -> dict:
        """Send a chat request. Returns raw response dict.

        If tools is provided, the response may contain function_call steps.
        Caller is responsible for handling them.
        """
        if not self.is_available():
            raise RuntimeError("Gemini API key not configured")

        history_text = ""
        last_user_text = ""
        for m in messages:
            if m.role == "user":
                last_user_text = m.content
            elif m.role == "assistant":
                history_text += f"Assistant: {m.content}\n"

        full_input = (
            f"Conversation so far:\n{history_text}\nUser: {last_user_text}"
            if history_text
            else last_user_text
        )
        if system:
            full_input = f"[System instructions: {system}]\n\n{full_input}"

        payload = {"model": self.model, "input": full_input}
        if tools:
            payload["tools"] = tools

        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}

        try:
            resp = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=30)
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

        return data

    def chat_simple(
        self,
        messages: list[AIMessage],
        *,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AIResponse:
        """Simple chat (returns AIResponse, no tools)."""
        data = self.chat(messages, system=system, temperature=temperature, max_tokens=max_tokens)
        return AIResponse(
            content=self._extract_text(data),
            provider="gemini",
            model=self.model,
            tokens_used=data.get("usage", {}).get("total_tokens", 0),
        )

    @staticmethod
    def _extract_text(data: dict) -> str:
        """Extract assistant text from response."""
        if isinstance(data.get("output_text"), str):
            return data["output_text"]
        parts = []
        for step in data.get("steps", []):
            if step.get("type") == "model_output":
                for block in step.get("content", []):
                    if block.get("type") == "text":
                        parts.append(block.get("text", ""))
        return "".join(parts) or "(no response)"

    @staticmethod
    def extract_function_calls(data: dict) -> list[dict]:
        """Extract all function_call steps from a response."""
        calls = []
        for step in data.get("steps", []):
            if step.get("type") == "function_call":
                calls.append({
                    "id": step.get("id"),
                    "name": step.get("name"),
                    "arguments": step.get("arguments", {}),
                })
        return calls

    def continue_with_function_result(
        self,
        *,
        previous_interaction_id: str,
        call_id: str,
        name: str,
        result: dict,
        tools: list[dict],
        system: str | None = None,
    ) -> dict:
        """Send a function result back to Gemini for final answer."""
        # According to Gemini docs, we need to pass previous_interaction_id
        # and input with the function_result.
        payload = {
            "model": self.model,
            "previous_interaction_id": previous_interaction_id,
            "input": [
                {
                    "type": "function_result",
                    "name": name,
                    "call_id": call_id,
                    "result": [{"type": "text", "text": json.dumps(result)}],
                }
            ],
            "tools": tools,
        }
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        try:
            resp = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            body = ""
            if hasattr(exc, "response") and exc.response is not None:
                try:
                    body = exc.response.text[:300]
                except Exception:
                    pass
            raise RuntimeError(f"Gemini continue failed: {exc} | {body}") from exc
