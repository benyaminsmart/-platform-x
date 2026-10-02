"""AI Campaign Writer — suggest email/in-app campaigns for a tenant.

Design:
- AI sees ONLY aggregated segment data (counts, sample sizes), never real emails.
- AI cannot invent discounts: only ones already defined on the tenant are usable.
- Grounded in real bookings + segments + business context.
- Deterministic fallback: returns 3 generic-but-safe campaigns.
"""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.models.tenant import Tenant
from app.core.logging_config import get_logger
from app.services import marketing as marketing_service
from app.services.ai import service as ai_service
from app.services.ai.business_context import build_business_context, context_to_prompt


SUPPORTED_LANGUAGES = {"en", "ar", "fil", "hi"}
SUPPORTED_CHANNELS = {"email", "in_app"}
MAX_CAMPAIGNS = 5
MIN_CAMPAIGNS = 3

_LANGUAGE_NAMES = {
    "en": "English", "ar": "Arabic (Modern Standard)",
    "fil": "Filipino (Tagalog)", "hi": "Hindi",
}


# ---------- Helpers ----------



logger = get_logger(__name__)

def _safe_ai(prompt: str) -> str | None:
    try:
        result = ai_service.chat(prompt, history=[])
        return (result or {}).get("content", "").strip() or None
    except Exception:
        return None


def _extract_json(s: str) -> dict[str, Any] | None:
    try:
        return json.loads(s)
    except Exception:
        logger.warning("Campaign writer parse failed", exc_info=True)
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[start : i + 1])
                except Exception:
                    return None
    return None


def _norm_campaign(c: dict[str, Any], valid_segments: set[str]) -> dict[str, Any] | None:
    if not isinstance(c, dict):
        return None
    name = (c.get("name") or "").strip()[:120]
    if not name:
        return None
    seg = (c.get("target_segment") or "").strip()
    if seg not in valid_segments:
        seg = "past_bookers"
    channel = (c.get("channel") or "email").strip().lower()
    if channel not in SUPPORTED_CHANNELS:
        channel = "email"
    subject = (c.get("subject") or "").strip()[:200] or None
    body = (c.get("body") or "").strip()[:4000] or None
    rationale = (c.get("rationale") or "").strip()[:500] or None
    return {
        "name": name,
        "target_segment": seg,
        "channel": channel,
        "subject": subject,
        "body": body,
        "rationale": rationale,
    }


# ---------- Fallback ----------


def _fallback_campaigns(tenant: Tenant, segments: dict[str, Any], language: str) -> list[dict[str, Any]]:
    """Safe, generic campaigns if AI unavailable."""
    out = [
        {
            "name": "Welcome back — special offer",
            "target_segment": "inactive_90d",
            "channel": "email",
            "subject": f"We miss you at {tenant.name}",
            "body": "We haven't seen you in a while. Come back and enjoy a special welcome-back offer on your next booking.",
            "rationale": "Re-engage customers who haven't booked in over 90 days.",
        },
        {
            "name": "Loyalty thank-you",
            "target_segment": "loyalty_gold_plus",
            "channel": "email",
            "subject": f"Thank you for being a top guest at {tenant.name}",
            "body": "As one of our most loyal guests, we'd like to thank you with an exclusive perk on your next visit.",
            "rationale": "Reward your best customers and keep them coming back.",
        },
        {
            "name": "New guests welcome",
            "target_segment": "new_30d",
            "channel": "email",
            "subject": f"A warm welcome to {tenant.name}",
            "body": "Thanks for your recent booking! Here's a special offer to make your next visit even better.",
            "rationale": "Convert first-time guests into repeat customers.",
        },
    ]
    # Add a high-value campaign if the segment is not empty
    if segments.get("high_value", {}).get("count", 0) > 0:
        out.append({
            "name": "VIP exclusive",
            "target_segment": "high_value",
            "channel": "email",
            "subject": f"An exclusive invitation from {tenant.name}",
            "body": "Because you're one of our top guests, we'd like to invite you to an exclusive experience.",
            "rationale": "Recognize top spenders with VIP treatment.",
        })
    return out[:MAX_CAMPAIGNS]


# ---------- Prompt ----------


def _build_suggest_prompt(
    tenant: Tenant,
    segments: dict[str, Any],
    totals: dict[str, Any],
    context_text: str,
    language: str,
) -> str:
    lang = _LANGUAGE_NAMES.get(language, "English")
    segs_desc = "\n".join(
        f"  - {name}: {data['count']} customers"
        for name, data in segments.items()
    )
    return f"""You are a marketing strategist for a small business on Platform-X.

CONTEXT:
{context_text}

CUSTOMER SEGMENTS (real numbers):
{segs_desc}

Total customers: {totals['customers']} · All-time revenue: {totals['all_time_revenue']} AED

TASK: Suggest 3 to {MAX_CAMPAIGNS} concrete, ready-to-send marketing campaigns
for this business. Write everything in {lang}.

Return ONLY a valid JSON object in this exact shape:
{{"campaigns": [
  {{
    "name": "short campaign name",
    "target_segment": "one of: {', '.join(sorted(marketing_service.SEGMENTS))}",
    "channel": "email" or "in_app",
    "subject": "email subject (max 100 chars) or null for in_app",
    "body": "short body text (2-4 sentences, no emojis, no fake discounts)",
    "rationale": "why this campaign matters (1 sentence, in {lang})"
  }}
]}}

RULES:
- Do NOT invent specific discount percentages or prices unless they are already in the context.
- Focus on re-engagement, loyalty, and new-guest conversion.
- Segment must be exactly one of: {', '.join(sorted(marketing_service.SEGMENTS))}.
- Return at most {MAX_CAMPAIGNS} campaigns, at least {MIN_CAMPAIGNS}.
- Return ONLY the JSON, no extra text."""


def _build_generate_prompt(
    tenant: Tenant,
    segment: str,
    goal: str,
    context_text: str,
    language: str,
    audience_size: int,
) -> str:
    lang = _LANGUAGE_NAMES.get(language, "English")
    return f"""You are a marketing copywriter for a small business on Platform-X.

CONTEXT:
{context_text}

TARGET SEGMENT: {segment} ({audience_size} customers)
GOAL: {goal}
LANGUAGE: {lang}

TASK: Write ONE ready-to-send email campaign to achieve the goal.

Return ONLY a valid JSON object in this exact shape:
{{"campaign": {{
  "name": "short campaign name",
  "target_segment": "{segment}",
  "channel": "email",
  "subject": "email subject (max 100 chars)",
  "body": "short body text (3-5 sentences, no emojis, no fake discounts)",
  "rationale": "why this approach works for this segment (1-2 sentences, in {lang})"
}}}}

RULES:
- Do NOT invent specific discount percentages or prices.
- If you want to mention an offer, refer to "your current offer" or "the best available rate".
- Return ONLY the JSON, no extra text."""


# ---------- Public API ----------


def suggest_campaigns(
    db: DBSession,
    *,
    tenant: Tenant,
    language: str = "en",
) -> dict[str, Any]:
    """Return {'campaigns': [...], 'provider': 'ai'|'fallback'}."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")

    seg_data = marketing_service.segment_customers(db, tenant)
    segments = seg_data["segments"]
    totals = seg_data["totals"]

    ctx = build_business_context(db, tenant)
    context_text = context_to_prompt(ctx)

    prompt = _build_suggest_prompt(tenant, segments, totals, context_text, language)
    raw = _safe_ai(prompt)

    campaigns: list[dict[str, Any]] = []
    provider = "fallback"

    if raw:
        parsed = _extract_json(raw)
        if parsed and isinstance(parsed.get("campaigns"), list):
            for c in parsed["campaigns"][:MAX_CAMPAIGNS]:
                nc = _norm_campaign(c, marketing_service.SEGMENTS)
                if nc:
                    # enrich with real audience size
                    seg = nc["target_segment"]
                    nc["estimated_reach"] = int(segments.get(seg, {}).get("count", 0))
                    campaigns.append(nc)
            if campaigns:
                provider = "ai"

    if not campaigns:
        fb = _fallback_campaigns(tenant, segments, language)
        for c in fb:
            c["estimated_reach"] = int(segments.get(c["target_segment"], {}).get("count", 0))
        campaigns = fb
        provider = "fallback"

    return {"campaigns": campaigns, "provider": provider}


def generate_campaign(
    db: DBSession,
    *,
    tenant: Tenant,
    segment: str,
    goal: str,
    language: str = "en",
) -> dict[str, Any]:
    """Return {'campaign': {...}, 'provider': 'ai'|'fallback'}."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of: {sorted(SUPPORTED_LANGUAGES)}")
    if segment not in marketing_service.SEGMENTS:
        raise ValueError(f"segment must be one of: {sorted(marketing_service.SEGMENTS)}")
    goal = (goal or "").strip()
    if not goal:
        raise ValueError("goal is required")

    audience = marketing_service.estimate_audience_size(db, tenant, segment)

    ctx = build_business_context(db, tenant)
    context_text = context_to_prompt(ctx)

    prompt = _build_generate_prompt(tenant, segment, goal, context_text, language, audience)
    raw = _safe_ai(prompt)

    campaign: dict[str, Any] | None = None
    provider = "fallback"

    if raw:
        parsed = _extract_json(raw)
        if parsed and isinstance(parsed.get("campaign"), dict):
            nc = _norm_campaign(parsed["campaign"], marketing_service.SEGMENTS)
            if nc and nc["target_segment"] == segment:
                nc["estimated_reach"] = audience
                campaign = nc
                provider = "ai"

    if campaign is None:
        campaign = {
            "name": f"Re-engagement: {goal[:60]}",
            "target_segment": segment,
            "channel": "email",
            "subject": f"An update from {tenant.name}",
            "body": (
                f"We have something special for you. {goal} "
                "Reply or book online to learn more."
            ),
            "rationale": "Safe fallback campaign; refine with AI when available.",
            "estimated_reach": audience,
        }

    return {"campaign": campaign, "provider": provider}
