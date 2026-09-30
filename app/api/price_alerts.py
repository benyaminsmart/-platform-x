"""Price alerts API (Phase 43, Step 1).

  GET    /me/price-alerts
  POST   /me/price-alerts           {service_id, target_price}
  DELETE /me/price-alerts/{id}
  POST   /me/price-alerts/check     (on-demand evaluation)
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.services import price_alert_service


router = APIRouter(prefix="/me/price-alerts", tags=["price-alerts"])


class AlertItem(BaseModel):
    id: str
    service_id: str
    target_price: str
    active: bool
    last_seen_price: str | None
    notified_at: str | None
    created_at: str | None


class AlertCreate(BaseModel):
    service_id: str = Field(min_length=1, max_length=36)
    target_price: float = Field(gt=0)


class AlertCheckItem(BaseModel):
    id: str
    service_id: str
    service_name: str
    current_price: str
    target_price: str
    currency: str
    triggered: bool
    notified_at: str | None


def _ser(a) -> AlertItem:
    return AlertItem(
        id=a.id, service_id=a.service_id,
        target_price=str(a.target_price), active=bool(a.active),
        last_seen_price=(str(a.last_seen_price) if a.last_seen_price else None),
        notified_at=(a.notified_at.isoformat() if a.notified_at else None),
        created_at=(a.created_at.isoformat() if a.created_at else None),
    )


@router.get("", response_model=list[AlertItem])
@limiter.limit("60/minute")
def list_alerts(
    request: Request,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[AlertItem]:
    return [_ser(a) for a in price_alert_service.list_alerts(db, user_id=user.id)]


@router.post("", response_model=AlertItem, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_alert(
    request: Request,
    payload: AlertCreate,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> AlertItem:
    try:
        a = price_alert_service.create_alert(
            db, user_id=user.id, service_id=payload.service_id,
            target_price=payload.target_price,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _ser(a)


@router.delete("/{alert_id}")
@limiter.limit("30/minute")
def delete_alert(
    request: Request,
    alert_id: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> dict:
    ok = price_alert_service.delete_alert(db, user_id=user.id, alert_id=alert_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"deleted": True, "alert_id": alert_id}


@router.post("/check", response_model=list[AlertCheckItem])
@limiter.limit("10/minute")
def check_alerts(
    request: Request,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[AlertCheckItem]:
    rows = price_alert_service.check_alerts(db, user_id=user.id)
    return [AlertCheckItem(**r) for r in rows]
