"""UI consistency guard for the business panel (Phase 63, Step 1).

Goal: prevent regressions where future templates hardcode light theme
colors instead of using --adm-* design tokens.

Rules:
- The following patterns are FORBIDDEN in the business panel templates:
    background: #fff / #ffffff / #faf8f5   (hardcoded light backgrounds)
    background:#fff ...                    (same without space)
  EXCEPT when combined with `color: var(--adm-brand)` on the same line
  (white-on-brand is legitimate).
- Every new business template must reference at least one --adm-* token.
"""
from pathlib import Path

import pytest

TEMPLATES_DIR = Path("app/templates/business")

# Patterns that, if they appear at all, must not be preceded by "background"
_FORBIDDEN_BG = ("background: #fff", "background:#fff",
                 "background: #ffffff", "background:#ffffff",
                 "background: #faf8f5", "background:#faf8f5")


def _templates() -> list[Path]:
    return sorted(TEMPLATES_DIR.rglob("*.html"))


def test_no_hardcoded_light_backgrounds() -> None:
    offenders: list[str] = []
    for tpl in _templates():
        text = tpl.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            low = line.lower()
            for pat in _FORBIDDEN_BG:
                if pat in low:
                    offenders.append(f"{tpl}:{line_no}: {line.strip()}")
    assert not offenders, "Hardcoded light backgrounds:\n" + "\n".join(offenders)


# Templates that are placeholders (analytics/settings) or use only shared
# base classes (customers). They are scheduled for full --adm-* adoption
# in Phase 65 (Business Panel Polish).
_ADM_TOKEN_EXEMPT = {
    "app/templates/business/business_analytics.html",
    "app/templates/business/business_customers.html",
    "app/templates/business/business_settings.html",
}


def test_every_business_template_uses_adm_tokens() -> None:
    """Each business template that extends business_base.html must reference
    at least one --adm-* variable somewhere (style or inline).

    Placeholder templates listed in _ADM_TOKEN_EXEMPT are skipped until
    Phase 65 upgrades them.
    """
    missing: list[str] = []
    for tpl in _templates():
        rel = str(tpl).replace("\\", "/")
        if rel in _ADM_TOKEN_EXEMPT:
            continue
        text = tpl.read_text(encoding="utf-8")
        if "business_base.html" not in text:
            continue
        if "--adm-" not in text:
            missing.append(rel)
    assert not missing, "Templates without --adm-* token: " + ", ".join(missing)
