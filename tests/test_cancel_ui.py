"""Tests for cancellation UI in account.js (Phase 30, Step 5c)."""
from pathlib import Path


def test_account_js_has_cancel_ui() -> None:
    js = Path("app/static/js/account.js").read_text(encoding="utf-8")
    assert "px-cancel-btn" in js
    assert "handleCancel" in js
    assert "refund-preview" in js
    assert "cancel-with-refund" in js
    assert "showCancelModal" in js


def test_account_js_cancel_buttons_bound() -> None:
    js = Path("app/static/js/account.js").read_text(encoding="utf-8")
    assert "querySelectorAll(\".px-cancel-btn\")" in js
