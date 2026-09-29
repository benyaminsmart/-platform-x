"""Recompute business scores for a period.

Usage:
  python -m app.scripts.recompute_scores                  # current month
  python -m app.scripts.recompute_scores --previous       # previous month
  python -m app.scripts.recompute_scores --all-history    # current + previous (default: current)

Idempotent: safe to run multiple times.
"""

import argparse
import sys

from app.db.session import SessionLocal
from app.services import leaderboard as lb_service
from app.services import scoring_engine


def _run(period: str) -> dict:
    if period == "current":
        ps, pe = scoring_engine.current_period()
    elif period == "previous":
        ps, pe = scoring_engine.previous_period()
    else:
        raise ValueError(f"unknown period: {period}")

    with SessionLocal() as db:
        out = lb_service.recompute_scores(db, period_start=ps, period_end=pe)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Recompute business scores")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--previous", action="store_true", help="recompute previous month")
    group.add_argument("--all", action="store_true", help="recompute current + previous")
    args = parser.parse_args()

    periods: list[str] = []
    if args.all:
        periods = ["previous", "current"]
    elif args.previous:
        periods = ["previous"]
    else:
        periods = ["current"]

    failed = False
    for p in periods:
        try:
            out = _run(p)
            print(
                f"[{p}] period {out['period_start']}..{out['period_end']} "
                f"tenants={out['tenants_total']} "
                f"created={out['created']} updated={out['updated']} "
                f"ranks={out['ranks_assigned']}"
            )
        except Exception as exc:
            print(f"[{p}] FAILED: {exc}", file=sys.stderr)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
