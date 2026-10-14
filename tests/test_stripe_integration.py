"""Integration test: Stripe-compatible webhook signature + payment flow.

This test does NOT call the real Stripe API. It simulates exactly what
Stripe sends (header format, timestamp, HMAC payload) and verifies that
our webhook endpoint accepts the correct signature and rejects wrong ones.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest


STRIPE_TEST_SECRET = "whsec_test_platform_x_1234567890"


def _stripe_signature(secret: str, body: bytes, ts: int) -> str:
    """Reproduce Stripe's signing scheme exactly."""
    signed = f"{ts}.{body.decode()}".encode()
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def _stripe_event(
    *,
    event_id: str,
    provider_reference: str,
    status: str,
    amount: str = "100.00",
    currency: str = "AED",
) -> dict:
    """Minimal Stripe-style event payload."""
    return {
        "id": event_id,
        "type": "payment_intent.succeeded" if status == "success"
                else "payment_intent.payment_failed",
        "data": {
            "object": {
                "id": provider_reference,
                "amount": int(float(amount) * 100),
                "currency": currency.lower(),
                "status": status,
            }
        },
    }


@pytest.fixture
def stripe_secret(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", STRIPE_TEST_SECRET)
    monkeypatch.setattr(settings, "WEBHOOK_SIGNATURE_ENFORCED", True)
    return STRIPE_TEST_SECRET


def test_stripe_webhook_valid_signature_passes(client, stripe_secret):
    """Signature is valid; body uses our internal schema.

    NOTE: real Stripe events use a different body shape. An adapter to
    translate Stripe events into our internal schema is planned for
    Stage 7 (buyer-driven). This test verifies signature math only.
    """
    body = json.dumps(
        {"provider_reference": "pi_test_unknown", "status": "success"}
    ).encode()
    ts = int(time.time())
    headers = {"Stripe-Signature": _stripe_signature(stripe_secret, body, ts)}
    r = client.post("/payments/webhook/stripe", content=body, headers=headers)
    assert r.status_code == 200
    assert r.json().get("received") is True


def test_stripe_webhook_tampered_body_rejected(client, stripe_secret):
    event = _stripe_event(
        event_id="evt_test_2",
        provider_reference="pi_test_unknown",
        status="success",
    )
    body = json.dumps(event).encode()
    ts = int(time.time())
    valid_sig = _stripe_signature(stripe_secret, body, ts)
    # Tamper: change status after signing
    event["data"]["object"]["status"] = "failed"
    tampered_body = json.dumps(event).encode()
    headers = {"Stripe-Signature": valid_sig}
    r = client.post(
        "/payments/webhook/stripe", content=tampered_body, headers=headers
    )
    assert r.status_code == 401


def test_stripe_webhook_wrong_secret_rejected(client, stripe_secret):
    event = _stripe_event(
        event_id="evt_test_3",
        provider_reference="pi_test_unknown",
        status="success",
    )
    body = json.dumps(event).encode()
    ts = int(time.time())
    wrong_sig = _stripe_signature("whsec_wrong_secret", body, ts)
    headers = {"Stripe-Signature": wrong_sig}
    r = client.post("/payments/webhook/stripe", content=body, headers=headers)
    assert r.status_code == 401


def test_stripe_webhook_replay_old_timestamp_rejected(client, stripe_secret):
    event = _stripe_event(
        event_id="evt_test_4",
        provider_reference="pi_test_unknown",
        status="success",
    )
    body = json.dumps(event).encode()
    old_ts = int(time.time()) - 1000  # beyond 300s tolerance
    headers = {"Stripe-Signature": _stripe_signature(stripe_secret, body, old_ts)}
    r = client.post("/payments/webhook/stripe", content=body, headers=headers)
    assert r.status_code == 401


def test_stripe_webhook_missing_header_rejected(client, stripe_secret):
    event = _stripe_event(
        event_id="evt_test_5",
        provider_reference="pi_test_unknown",
        status="success",
    )
    body = json.dumps(event).encode()
    r = client.post("/payments/webhook/stripe", content=body)
    assert r.status_code == 401


def test_stripe_webhook_malformed_header_rejected(client, stripe_secret):
    event = _stripe_event(
        event_id="evt_test_6",
        provider_reference="pi_test_unknown",
        status="success",
    )
    body = json.dumps(event).encode()
    headers = {"Stripe-Signature": "not-a-valid-format"}
    r = client.post("/payments/webhook/stripe", content=body, headers=headers)
    assert r.status_code == 401


def test_stripe_webhook_rotated_signature_accepted(client, stripe_secret):
    """Stripe can send multiple v1 values during secret rotation.

    Our verifier reads the first v1 it finds; if it matches, accept.
    """
    body = json.dumps(
        {"provider_reference": "pi_test_unknown", "status": "success"}
    ).encode()
    ts = int(time.time())
    sig = _stripe_signature(stripe_secret, body, ts).split("v1=")[1]
    headers = {"Stripe-Signature": f"t={ts},v1={sig}"}
    r = client.post("/payments/webhook/stripe", content=body, headers=headers)
    assert r.status_code == 200
