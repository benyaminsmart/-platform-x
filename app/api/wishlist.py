"""Wishlist API (Phase 33, Step 2).

Auth: user JWT (any tenant).
Routes:
  GET    /wishlist              list all
  POST   /wishlist              add { service_id, note? }
  DELETE /wishlist/{service_id} remove
  GET    /wishlist/check/{service_id} check membership
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.services import wishlist_service


router = APIRouter(prefix="/wishlist", tags=["wishlist"])


class WishlistAddRequest(BaseModel):
    service_id: str = Field(min_length=1, max_length=36)
    note: str | None = Field(default=None, max_length=500)


class WishlistItem(BaseModel):
    wishlist_id: str
    service_id: str
    service_name: str
    service_type: str
    price: float
    currency: str
    tenant_id: str
    tenant_slug: str
    tenant_name: str
    location: str | None
    rating: float | None
    cover_image: str | None
    note: str | None
    added_at: str | None


class WishlistAddResponse(BaseModel):
    status: str
    service_id: str


class CheckResponse(BaseModel):
    service_id: str
    is_wishlisted: bool


@router.get("", response_model=list[WishlistItem])
@limiter.limit("60/minute")
def list_wishlist(
    request: Request,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[WishlistItem]:
    return [WishlistItem(**x) for x in wishlist_service.list_wishlist(db, user_id=user.id)]


@router.post("", response_model=WishlistAddResponse)
@limiter.limit("30/minute")
def add_wishlist(
    request: Request,
    payload: WishlistAddRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> WishlistAddResponse:
    w, status_str = wishlist_service.add_to_wishlist(
        db, user_id=user.id, service_id=payload.service_id, note=payload.note
    )
    if status_str == "not_found":
        raise HTTPException(status_code=404, detail="Service not found")
    return WishlistAddResponse(status=status_str, service_id=payload.service_id)


@router.delete("/{service_id}", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
def remove_wishlist(
    request: Request,
    service_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> dict:
    ok = wishlist_service.remove_from_wishlist(db, user_id=user.id, service_id=service_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Not in wishlist")
    return {"service_id": service_id, "removed": True}


@router.get("/check/{service_id}", response_model=CheckResponse)
@limiter.limit("60/minute")
def check_wishlist(
    request: Request,
    service_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> CheckResponse:
    return CheckResponse(
        service_id=service_id,
        is_wishlisted=wishlist_service.is_wishlisted(db, user_id=user.id, service_id=service_id),
    )
