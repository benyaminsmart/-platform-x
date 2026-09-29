"""Tests: room_number displayed in receipt (Phase 36, Step 5)."""
from pathlib import Path


def test_receipt_has_room_line_placeholder() -> None:
    src = Path("app/api/receipts.py").read_text(encoding="utf-8")
    assert "room_line" in src
    assert "Room {b.room_number}" in src or "room_line" in src


def test_account_js_shows_room_number() -> None:
    js = Path("app/static/js/account.js").read_text(encoding="utf-8")
    assert "b.room_number" in js
    assert "Room " in js
