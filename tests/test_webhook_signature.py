"""Tests for payment webhook signature verification."""
from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest


def _generic_sig(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()


def _stripe_sig(secret: str, body: bytes, ts: int) -> str:
    signed = f"{ts}.{body.decode()}".encode()
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


@pytest.fixture
def webhook_secret(monkeypatch):
    from app.core.config import settings
    secret = "test_webhook_secret_123"
    monkeypatch.setattr(settings, "PAYMENT_WEBHOOK_SECRET", secret)
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", secret)
    monkeypatch.setattr(settings, "WEBHOOK_SIGNATURE_ENFORCED", True)
    return secret


def test_generic_webhook_invalid_signature_rejected(client, webhook_secret):
    body = json.dumps(
        {"provider_reference": "ref-1", "status": "failed"}
    ).encode()
    headers = {"X-PlatformX-Signature": "sha256=deadbeef"}
    r = client.post("/payments/webhook/telr", content=body, headers=headers)
    assert r.status_code == 401


def test_generic_webhook_missing_signature_rejected(client, webhook_secret):
    body = json.dumps(
        {"provider_reference": "ref-1", "status": "failed"}
    ).encode()
    r = client.post("/payments/webhook/telr", content=body)
    assert r.status_code == 401


def test_generic_webhook_valid_signature_reaches_body_validation(
    client, webhook_secret
):
    body = json.dumps(
        {"provider_reference": "ref-1", "status": "failed"}
    ).encode()
    headers = {"X-PlatformX-Signature": _generic_sig(webhook_secret, body)}
    r = client.post("/payments/webhook/telr", content=body, headers=headers)
    assert r.status_code in (200, 404)


def test_stripe_webhook_invalid_signature_rejected(client, webhook_secret):
    body = json.dumps(
        {"provider_reference": "ref-1", "status": "failed"}
    ).encode()
    headers = {"Stripe-Signature": "t=123,v1=deadbeef"}
    r = client.post("/payments/webhook/stripe", content=body, headers=headers)
    assert r.status_code == 401


def test_stripe_webhook_expired_timestamp_rejected(client, webhook_secret):
    body = json.dumps(
        {"provider_reference": "ref-1", "status": "failed"}
    ).encode()
    old_ts = int(time.time()) - 1000
    headers = {"Stripe-Signature": _stripe_sig(webhook_secret, body, old_ts)}
    r = client.post("/payments/webhook/stripe", content=body, headers=headers)
    assert r.status_code == 401


def test_webhook_secret_not_configured_returns_503(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "PAYMENT_WEBHOOK_SECRET", "")
    monkeypatch.setattr(settings, "WEBHOOK_SIGNATURE_ENFORCED", True)
    body = json.dumps(
        {"provider_reference": "ref-1", "status": "failed"}
    ).encode()
    headers = {"X-PlatformX-Signature": "sha256=whatever"}
    r = client.post("/payments/webhook/telr", content=body, headers=headers)
    assert r.status_code == 503


def test_signature_enforcement_can_be_disabled(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "WEBHOOK_SIGNATURE_ENFORCED", False)
    body = json.dumps(
        {"provider_reference": "ref-1", "status": "failed"}
    ).encode()
    r = client.post("/payments/webhook/telr", content=body)
    assert r.status_code in (200, 404)
