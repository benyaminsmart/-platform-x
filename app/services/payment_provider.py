"""Payment provider abstraction + mock implementation.

The real provider (Telr) will implement the same interface later.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class ProviderIntent:
    """Result of creating an intent at the provider."""

    provider_reference: str
    redirect_url: str


class PaymentProvider:
    """Abstract payment provider interface."""

    name: str = "abstract"

    def create_intent(
        self, *, amount: Decimal, currency: str, method: str, description: str
    ) -> ProviderIntent:  # pragma: no cover - interface only
        raise NotImplementedError


class MockPaymentProvider(PaymentProvider):
    """Deterministic in-process provider for local development and demo."""

    name = "mock"

    def create_intent(
        self, *, amount: Decimal, currency: str, method: str, description: str
    ) -> ProviderIntent:
        ref = f"mock_{secrets.token_urlsafe(12).replace('-', '').replace('_', '')[:16]}"
        # In demo, hitting this URL finalizes the payment.
        redirect_url = f"/payments/mock/confirm/{ref}"
        return ProviderIntent(provider_reference=ref, redirect_url=redirect_url)


def get_payment_provider() -> PaymentProvider:
    """Return the configured payment provider."""
    # Only mock for now; switch by config later.
    return MockPaymentProvider()
