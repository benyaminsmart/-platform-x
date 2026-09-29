"""AI Review Writer + Responder (Phase 28, Step 2).

Two responsibilities:
1) polish_review: turn a guest's raw text into a clear, respectful review
2) respond_to_review: write a professional business reply

Constraints:
- AI never invents facts (amenities, prices, awards).
- AI must not promise discounts unless explicitly in context.
- Deterministic fallbacks always available.
"""

import json
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.review import Review
from app.models.tenant import Tenant
from app.services.ai import service as ai_service


SUPPORTED_LANGUAGES = {"en", "ar", "fil", "hi"}
_LANGUAGE_NAMES = {
    "en": "English", "ar": "Arabic (Modern Standard)",
    "fil": "Filipino (Tagalog)", "hi": "Hindi",
}


def _safe_ai(prompt: str) -> str | None:
    try:
        result = ai_service.chat(prompt, history=[])
        return (result or {}).get("content", "").strip() or None
    except Exception:
        return None


def _clean(s: str, max_len: int = 2000) -> str:
    return (s or "").strip()[:max_len]


# ---------- Review Writer ----------


def _fallback_polish(text: str, rating: int) -> str:
    text = _clean(text)
    if text.endswith((".", "!", "?")):
        return text
    return text + "."


def polish_review(
    db: DBSession,
    *,
    tenant: Tenant,
    raw_text: str,
    rating: int,
    language: str = "en",
) -> dict[str, Any]:
    """Return {'content': str, 'provider': 'ai'|'fallback'}."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")

    raw_text = _clean(raw_text, max_len=2000)
    if len(raw_text) < 5:
        raise ValueError("raw_text is too short")

    lang = _LANGUAGE_NAMES[language]
    prompt = f"""You are a careful review editor for Platform-X.

TASK: Rewrite the guest's raw text into a clear, respectful, believable review.

RULES:
- Write in {lang}.
- Keep 2-5 sentences. No emojis. No bullet lists.
- Do NOT invent facts (no fake amenities, awards, or prices).
- Preserve the guest's actual opinion and rating direction (rating = {rating}/5).
- Do not add offers or promises.
- Return ONLY the polished review text, nothing else.

GUEST'S RAW TEXT:
\"\"\"{raw_text}\"\"\""""

    polished = _safe_ai(prompt)
    provider = "ai"
    if not polished:
        polished = _fallback_polish(raw_text, rating)
        provider = "fallback"

    return {"content": _clean(polished, max_len=1500), "provider": provider}


# ---------- Review Responder ----------


_TONES = {"professional", "friendly", "warm"}


def _fallback_respond(review: Review, tenant: Tenant) -> str:
    if review.sentiment == "negative":
        return (
            f"Thank you for your feedback. We are sorry to hear about your experience at "
            f"{tenant.name}. Your comments help us improve, and we would like to make "
            "things right. Please reach out to us directly so we can assist."
        )
    if review.sentiment == "positive":
        return (
            f"Thank you so much for your kind words about {tenant.name}. "
            "We are delighted you enjoyed your visit and look forward to welcoming you again."
        )
    return (
        f"Thank you for taking the time to share your experience at {tenant.name}. "
        "We appreciate your feedback and hope to see you again soon."
    )


def respond_to_review(
    db: DBSession,
    *,
    tenant: Tenant,
    review: Review,
    language: str = "en",
    tone: str = "professional",
) -> dict[str, Any]:
    """Return {'response': str, 'provider': 'ai'|'fallback'}."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")
    if tone not in _TONES:
        raise ValueError(f"tone must be one of: {sorted(_TONES)}")

    lang = _LANGUAGE_NAMES[language]

    prompt = f"""You are the business owner replying to a guest review on Platform-X.

BUSINESS: {tenant.name}
RATING: {review.rating}/5
SENTIMENT: {review.sentiment or "unknown"}
GUEST'S REVIEW:
\"\"\"{review.content}\"\"\"

TASK: Write a short, warm, professional reply in {lang}.

RULES:
- 2-4 sentences. No emojis. No bullet lists.
- Tone: {tone}.
- If the sentiment is negative: acknowledge the concern, apologize sincerely,
  and invite the guest to contact you. Do NOT promise specific compensations.
- If positive: thank the guest and invite them back.
- If neutral: thank them for the feedback.
- NEVER invent facts, policies, or discounts.
- Return ONLY the reply text."""
    response = _safe_ai(prompt)
    provider = "ai"
    if not response:
        response = _fallback_respond(review, tenant)
        provider = "fallback"

    return {"response": _clean(response, max_len=1500), "provider": provider}
