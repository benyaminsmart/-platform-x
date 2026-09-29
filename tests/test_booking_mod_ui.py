"""Tests for booking modification UI (Phase 35, Step 3)."""
from pathlib import Path


def test_account_js_has_modify() -> None:
    js = Path("app/static/js/account.js").read_text(encoding="utf-8")
    assert "px-mod-btn" in js
    assert "handleModify" in js
    assert "showModifyModal" in js
    assert "/modify-preview" in js
    assert "/modify" in js
    assert "refreshPreview" in js
