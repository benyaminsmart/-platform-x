"""Tests for AI Group Coordinator UI integration (Phase 59, Step 3).

account.js is a static asset; assert on its content for the wiring.
"""
from pathlib import Path


def _js() -> str:
    return Path("app/static/js/account.js").read_text()


def test_ai_coord_button_present() -> None:
    js = _js()
    assert "AI Coordinate" in js
    assert "-ai-panel" in js


def test_ai_coord_endpoint_called() -> None:
    js = _js()
    assert "/group/coordinate" in js


def test_ai_coord_handles_statuses() -> None:
    js = _js()
    assert "not_group" in js
    assert "too_small" in js
    assert "Suggested activities" in js
