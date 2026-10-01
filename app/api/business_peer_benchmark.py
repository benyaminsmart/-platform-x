"""Business Peer Benchmark API (Phase 52, Step 2).

Prefix: /business/api/peer-benchmark

Returns anonymized peer comparison for the authenticated tenant.
Only aggregates. No peer identities. AI summary grounded in real numbers.

NOTE: no 'from __future__ import annotations' in this file.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.api.deps_business import get_business_tenant, get_current_business_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai import peer_benchmark as pb


router = APIRouter(prefix="/business/api/peer-benchmark", tags=["business-peer-benchmark"])


class MetricItem(BaseModel):
    metric: str
    self: float | None
    peer_median: float | None
    delta_pct: float | None
    sample_size: int
    unit: str


class BenchmarkResponse(BaseModel):
    category: str
    metrics: list[MetricItem]
    summary: str
    provider: str


def _ser(out: dict[str, Any]) -> BenchmarkResponse:
    return BenchmarkResponse(
        category=out["category"],
        metrics=[MetricItem(**m) for m in out["metrics"]],
        summary=out["summary"],
        provider=out["provider"],
    )


@router.get("", response_model=BenchmarkResponse)
@limiter.limit("30/minute")
def peer_benchmark(
    request: Request,
    language: str = Query(default="en", pattern="^(en|ar|fil|hi)$"),
    user: User = Depends(get_current_business_user),
    tenant: Tenant = Depends(get_business_tenant),
    db=Depends(get_db),
) -> BenchmarkResponse:
    try:
        out = pb.compute(db, tenant=tenant, language=language)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _ser(out)
