"""AI provider interface.

Any AI provider (mock, Gemini, OpenAI, Claude) must implement this
interface so the rest of the app stays provider-agnostic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AIMessage:
    """A single message in a conversation."""
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class AIResponse:
    """Response from an AI provider."""
    content: str
    provider: str
    model: str | None = None
    tokens_used: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class AIProvider(ABC):
    """Abstract base for all AI providers."""

    name: str = "abstract"

    @abstractmethod
    def chat(
        self,
        messages: list[AIMessage],
        *,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AIResponse:
        """Send a conversation and return an assistant response."""
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider is configured and ready."""
        raise NotImplementedError
