#!/usr/bin/env python3
"""Platform-X — PostgreSQL compatibility checker.

Scans the SQLAlchemy models and Alembic migrations for constructs that
are known to behave differently on PostgreSQL vs SQLite.

Usage: python scripts/check_postgres_compat.py
Exit code 0 = clean; 1 = issues found (see report).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ISSUES: list[str] = []
WARNINGS: list[str] = []


def scan(path: Path, pattern: str, message: str, warn_only: bool = False) -> None:
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if re.search(pattern, line):
            target = WARNINGS if warn_only else ISSUES
            target.append(f"{path}:{i}  {message}\n    > {line.strip()}")


def main() -> int:
    root = Path(".")
    models = list((root / "app" / "models").glob("*.py"))
    migrations = list((root / "alembic" / "versions").glob("*.py"))

    # 1. Check for SQLite-specific SQL in migrations
    for m in migrations:
        src = m.read_text()
        for pat, msg in [
            (r"PRAGMA", "PRAGMA is SQLite-only"),
            (r"server_default=sa\.text\('1'\)", "SQLite boolean default — PostgreSQL needs 'true' or '1'::boolean"),
            (r"server_default=sa\.text\('0'\)", "SQLite boolean default — PostgreSQL needs 'false' or '0'::boolean"),
            (r"AUTOINCREMENT", "AUTOINCREMENT is SQLite-only"),
        ]:
            if re.search(pat, src):
                ISSUES.append(f"{m}  {msg}")

    # 2. Check for JSON columns (fine on both, but note)
    for model in models:
        scan(model, r"JSONB", "JSONB is PostgreSQL-only (JSON is portable)", warn_only=True)

    # 3. Check for Numeric without precision
    for model in models:
        scan(model, r"Numeric\(\)", "Numeric without precision may differ on PG")

    # 4. Check for DateTime without timezone
    for model in models:
        scan(model, r"DateTime\(\)", "DateTime without timezone=True loses tz on PG", warn_only=True)

    # 5. Check for String without length (PostgreSQL is fine, but be explicit)
    for model in models:
        scan(model, r"String\(\)", "String without length — prefer explicit", warn_only=True)

    # 5b. Check for UniqueConstraint patterns that could break
    # (only inform if used inside __table_args__)
    for model in models:
        scan(model, r"sqlite_", "sqlite_ prefix is SQLite-only", warn_only=True)

    # Report
    print("=== PostgreSQL Compatibility Checker ===")
    print(f"Scanned {len(models)} models, {len(migrations)} migrations.")
    print()
    if ISSUES:
        print(f"BLOCKING ISSUES ({len(ISSUES)}):")
        for x in ISSUES:
            print("  " + x)
        print()
    if WARNINGS:
        print(f"WARNINGS ({len(WARNINGS)}):")
        for x in WARNINGS:
            print("  " + x)
        print()

    if not ISSUES and not WARNINGS:
        print("CLEAN — no compatibility issues found.")
        return 0
    if ISSUES:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
