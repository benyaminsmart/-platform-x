"""Regression tests: business_ai.html must use the --adm-* design tokens.

These tests prevent re-introducing hardcoded light colors that break the
dark admin theme (a real bug fixed in Phase 21).
"""

import re

from fastapi.testclient import TestClient


# Light-theme colors that must NOT be hardcoded in the business AI page.
FORBIDDEN_LIGHT_COLORS = [
    "#faf8f5",
    "#ffffff",
    "#fff",
    "#111111",
    "#111",
    "#6b7280",
    "#e5e7eb",
    "#166534",
    "#991b1b",
    "#b45309",
    "background: white",
    "background:white",
]


def test_business_ai_page_uses_adm_tokens(client: TestClient) -> None:
    r = client.get("/business/ai")
    assert r.status_code == 200
    html = r.text
    # Must reference the dark admin tokens at least for the main surfaces
    assert "var(--adm-surface" in html
    assert "var(--adm-text" in html
    assert "var(--adm-line" in html
    assert "var(--adm-muted" in html


def test_business_ai_page_no_hardcoded_light_colors(client: TestClient) -> None:
    r = client.get("/business/ai")
    html = r.text.lower()

    # Extract only inline style attributes and the <style> block to avoid
    # false positives in text content or comments.
    style_block_match = re.search(r"<style>(.*?)</style>", html, re.DOTALL)
    style_block = style_block_match.group(1) if style_block_match else ""

    inline_styles = " ".join(re.findall(r'style="([^"]*)"', html))

    combined = style_block + " " + inline_styles

    found = [c for c in FORBIDDEN_LIGHT_COLORS if c in combined]
    assert not found, (
        "Hardcoded light colors found in business_ai.html "
        f"(breaks dark admin theme): {found}"
    )
