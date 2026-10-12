"""Payment endpoints — intent, webhook, detail, mock confirm."""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_tenant, get_current_user
from app.core.config import settings
from app.core.rate_limit import LIMITS, limiter
from app.core.webhook_signature import verify_provider_webhook
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.payment import (
    PaymentIntentRequest,
    PaymentIntentResponse,
    PaymentPublic,
)
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post(
    "/intent",
    response_model=PaymentIntentResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(LIMITS["payment_intent"])
def create_intent(
    request: Request,
    payload: PaymentIntentRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> PaymentIntentResponse:
    """Create a payment intent for a booking or order."""
    try:
        payment, redirect_url = payment_service.create_intent(
            db, tenant_id=tenant.id, user_id=user.id, payload=payload
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return PaymentIntentResponse(
        payment_id=payment.id,
        provider=payment.provider,
        provider_reference=payment.provider_reference,
        status=payment.status,
        amount=payment.amount,
        currency=payment.currency,
        redirect_url=redirect_url,
    )


@router.get("/{payment_id}", response_model=PaymentPublic)
def get_payment(
    payment_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> PaymentPublic:
    """Return a payment owned by the current user."""
    payment = payment_service.get_payment(
        db, tenant_id=tenant.id, user_id=user.id, payment_id=payment_id
    )
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return PaymentPublic.model_validate(payment)


@router.post("/webhook/{provider}")
async def provider_webhook(
    provider: str,
    request: Request,
    db: DBSession = Depends(get_db),
) -> JSONResponse:
    """Receive provider webhook.

    Verifies the HMAC-SHA256 signature before accepting the payload.
    Generic providers use X-PlatformX-Signature: sha256=<hex>.
    Stripe uses Stripe-Signature: t=<ts>,v1=<hex>.
    """
    raw_body = await request.body()

    # Dev-only: mock provider is gated by ENABLE_MOCK_PAYMENTS and
    # never accepts traffic in production. Skip signature checks for it.
    is_mock = provider.lower() == "mock"
    if is_mock and not settings.ENABLE_MOCK_PAYMENTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    if settings.WEBHOOK_SIGNATURE_ENFORCED and not is_mock:
        secret = (
            settings.STRIPE_WEBHOOK_SECRET
            if provider.lower() == "stripe"
            else settings.PAYMENT_WEBHOOK_SECRET
        )
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Webhook signature secret not configured",
            )
        verify_provider_webhook(
            provider=provider,
            request=request,
            body=raw_body,
            secret=secret,
        )
    try:
        body: dict[str, Any] = json.loads(raw_body)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body"
        )

    ref = body.get("provider_reference")
    new_status = body.get("status")
    if not ref or new_status not in {"success", "failed", "refunded"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider_reference and valid status are required",
        )

    if new_status == "success":
        payment = payment_service.mark_success(db, provider_reference=ref, raw=body)
    elif new_status == "failed":
        payment = payment_service.mark_failed(db, provider_reference=ref, raw=body)
    else:  # refunded
        payment = payment_service.mark_success(db, provider_reference=ref, raw=body)
        if payment is not None:
            payment.status = "refunded"
            db.commit()
            db.refresh(payment)

    if payment is None:
        return JSONResponse({"received": True, "unknown_reference": True})
    return JSONResponse({"received": True, "payment_status": payment.status})


@router.get("/mock/confirm/{provider_reference}")
def mock_confirm(
    provider_reference: str,
    db: DBSession = Depends(get_db),
) -> JSONResponse:
    """Dev-only confirmation endpoint used by MockPaymentProvider redirects.

    Disabled in production via ENABLE_MOCK_PAYMENTS flag.
    """
    if not settings.ENABLE_MOCK_PAYMENTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )
    payment = payment_service.mark_success(db, provider_reference=provider_reference)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown reference")
    return JSONResponse(
        {
            "status": "success",
            "payment_id": payment.id,
            "provider_reference": provider_reference,
        }
    )
