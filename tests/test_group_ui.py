"""Tests for group UI in account (Phase 40, Step 4)."""
from pathlib import Path


def test_account_js_has_group_ui() -> None:
    js = Path("app/static/js/account.js").read_text(encoding="utf-8")
    assert "px-group-btn" in js
    assert "openGroupModal" in js
    assert "/group" in js
    assert "data-mkpaid" in js
    assert "data-rm" in js
