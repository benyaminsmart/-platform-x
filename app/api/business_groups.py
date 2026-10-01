"""Business Group API (Phase 58, Step 2).

Prefix: /business/api/groups

Endpoints:
  GET    /                              list owner's groups
  POST   /                              create a group
  GET    /{group_id}                    group detail + aggregate metrics
  POST   /{group_id}/attach             attach a tenant (by slug)
  DELETE /{group_id}/members/{slug}     detach a tenant
  DELETE /{group_id}                    delete a group (detaches members)

Auth: business user (owner/manager). Group ownership is verified by user id.

NOTE: no 'from __future__ import annotations' in this file.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps_business import get_current_business_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.services import business_group_service as bgs


router = APIRouter(prefix="/business/api/groups", tags=["business-groups"])


class MemberItem(BaseModel):
    id: str
    slug: str
    name: str
    category: str | None = None


class GroupItem(BaseModel):
    id: str
    slug: str
    name: str
    members_count: int
    members: list[MemberItem] = []


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class AttachRequest(BaseModel):
    tenant_slug: str = Field(min_length=1, max_length=100)


class MetricsBlock(BaseModel):
    members_count: int
    services_count: int
    bookings_30d: int
    revenue_30d: str
    avg_rating: float | None
    currency: str | None


class GroupDetail(BaseModel):
    id: str
    slug: str
    name: str
    members: list[MemberItem]
    metrics: MetricsBlock


def _ser_group(g: dict) -> GroupItem:
    return GroupItem(
        id=g["id"], slug=g["slug"], name=g["name"],
        members_count=g["members_count"],
        members=[MemberItem(**m) for m in g["members"]],
    )


@router.get("", response_model=list[GroupItem])
@limiter.limit("60/minute")
def list_groups(
    request: Request,
    user: User = Depends(get_current_business_user),
    db: DBSession = Depends(get_db),
) -> list[GroupItem]:
    return [_ser_group(g) for g in bgs.list_groups(db, owner_user_id=user.id)]


@router.post("", response_model=GroupItem, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_group(
    request: Request,
    payload: GroupCreate,
    user: User = Depends(get_current_business_user),
    db: DBSession = Depends(get_db),
) -> GroupItem:
    g, st = bgs.create_group(db, owner_user_id=user.id, name=payload.name)
    if st == "bad_name":
        raise HTTPException(status_code=422, detail="Name is required")
    rows = bgs.list_groups(db, owner_user_id=user.id)
    for r in rows:
        if r["id"] == g.id:
            return _ser_group(r)
    raise HTTPException(status_code=500, detail="Group created but not found")


@router.get("/{group_id}", response_model=GroupDetail)
@limiter.limit("60/minute")
def group_detail(
    request: Request,
    group_id: str,
    user: User = Depends(get_current_business_user),
    db: DBSession = Depends(get_db),
) -> GroupDetail:
    rows = bgs.list_groups(db, owner_user_id=user.id)
    target = next((r for r in rows if r["id"] == group_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Group not found")
    metrics = bgs.aggregate_metrics(db, group_id=group_id, window_days=30)
    return GroupDetail(
        id=target["id"],
        slug=target["slug"],
        name=target["name"],
        members=[MemberItem(**m) for m in target["members"]],
        metrics=MetricsBlock(**metrics),
    )


@router.post("/{group_id}/attach", response_model=GroupItem)
@limiter.limit("30/minute")
def attach_tenant(
    request: Request,
    group_id: str,
    payload: AttachRequest,
    user: User = Depends(get_current_business_user),
    db: DBSession = Depends(get_db),
) -> GroupItem:
    t, st = bgs.attach_tenant(
        db, owner_user_id=user.id, group_id=group_id,
        tenant_slug=payload.tenant_slug,
    )
    if st == "not_found":
        raise HTTPException(status_code=404, detail="Group not found")
    if st == "tenant_not_found":
        raise HTTPException(status_code=404, detail="Tenant not found")
    if st == "not_owner":
        raise HTTPException(status_code=403, detail="You do not own this tenant")
    rows = bgs.list_groups(db, owner_user_id=user.id)
    for r in rows:
        if r["id"] == group_id:
            return _ser_group(r)
    raise HTTPException(status_code=500, detail="Attached but group not found")


@router.delete("/{group_id}/members/{tenant_slug}")
@limiter.limit("30/minute")
def detach_tenant(
    request: Request,
    group_id: str,
    tenant_slug: str,
    user: User = Depends(get_current_business_user),
    db: DBSession = Depends(get_db),
) -> dict:
    ok = bgs.detach_tenant(
        db, owner_user_id=user.id, group_id=group_id, tenant_slug=tenant_slug,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")
    return {"detached": True, "tenant_slug": tenant_slug}


@router.delete("/{group_id}")
@limiter.limit("30/minute")
def delete_group(
    request: Request,
    group_id: str,
    user: User = Depends(get_current_business_user),
    db: DBSession = Depends(get_db),
) -> dict:
    ok = bgs.delete_group(db, owner_user_id=user.id, group_id=group_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"deleted": True, "group_id": group_id}
