"""Tests for Instant Refund AI UI integration in account.js (Phase 54, Step 3).

The account.js file is served as a static asset. We assert on its
content to ensure the AI refund preview wiring is in place.
"""
from pathlib import Path


def _account_js() -> str:
    return Path("app/static/js/account.js").read_text()


def test_ai_refund_button_present() -> None:
    js = _account_js()
    assert "-ai" in js  # button id suffix
    assert "AI Refund Preview" in js


def test_ai_refund_endpoint_called() -> None:
    js = _account_js()
    assert "/ai-refund" in js


def test_ai_refund_body_renders_suggestion() -> None:
    js = _account_js()
    assert "Suggested:" in js
    assert "Base policy:" in js
    assert "Informational only" in js
