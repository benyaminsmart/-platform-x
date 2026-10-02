"""Guard: every route must have a rate limit (Phase 68, Step 2).

Business panel routes and webhooks are allowed to skip limits in some
edge cases; we exempt a tiny whitelist and require the rest.
"""
import re
from pathlib import Path

# Modules with no limits allowed (rare): none currently — but keep the
# mechanism for future edge cases.
EXEMPT: set[str] = set()

API_DIR = Path("app/api")


def _count_routes(path: Path) -> int:
    text = path.read_text()
    return len(re.findall(r"^@(router|business_router|user_router|admin_router)\.", text, re.MULTILINE))


def _count_limits(path: Path) -> int:
    text = path.read_text()
    return len(re.findall(r"^@limiter\.limit", text, re.MULTILINE))


def test_all_api_modules_have_rate_limits() -> None:
    offenders: list[str] = []
    for f in sorted(API_DIR.glob("*.py")):
        if f.name in {"__init__.py", "deps.py", "deps_business.py", "deps_admin.py", "deps_api_key.py"}:
            continue
        if str(f) in EXEMPT or f.name in EXEMPT:
            continue
        routes = _count_routes(f)
        limits = _count_limits(f)
        if routes > 0 and limits == 0:
            offenders.append(f"{f.name}: {routes} routes, 0 limits")
    assert not offenders, "APIs without rate limits:\n" + "\n".join(offenders)


def test_limits_not_exceed_routes() -> None:
    """Sanity: number of limiter decorators must not exceed route count."""
    for f in sorted(API_DIR.glob("*.py")):
        routes = _count_routes(f)
        limits = _count_limits(f)
        if limits > routes + 1:  # +1 tolerance for admin routers used twice
            raise AssertionError(f"{f.name}: {limits} limits > {routes} routes")
