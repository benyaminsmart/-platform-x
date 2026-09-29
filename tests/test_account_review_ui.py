"""Tests for write-review UI in account (Phase 39, Step 3)."""
from pathlib import Path


def test_account_js_has_write_review() -> None:
    js = Path("app/static/js/account.js").read_text(encoding="utf-8")
    assert "px-review-btn" in js
    assert "handleWriteReview" in js
    assert "showReviewModal" in js
    assert "/reviews" in js
    assert "/photos" in js
    assert "reviewable" in js
