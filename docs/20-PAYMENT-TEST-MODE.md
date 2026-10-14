# Platform-X — Payment Test Mode Guide

> **Audience:** Buyer (Stage 7) or developer verifying payment integration.
> **Goal:** Connect a real payment provider in test mode and run one
> end-to-end payment flow (checkout → webhook → confirmation).

---

## 0. Current state (as of v1.0.14)

| Layer | Status |
|-------|--------|
| Payment abstraction (`PaymentProvider`) | Implemented |
| Mock provider (dev/demo) | Implemented |
| Webhook signature — generic HMAC-SHA256 | Implemented (Phase 89) |
| Webhook signature — Stripe scheme | Implemented (Phase 89) |
| Stripe signature integration tests | 7 tests pass (C4/A, v1.0.14) |
| Real Stripe end-to-end flow | Buyer-driven (Stage 7) |
| Real Telr end-to-end flow | Buyer-driven (Stage 7) |

**What this means:** the code is ready. The buyer only needs to add
API keys and point a public URL at the webhook endpoint.

---

## 1. Environment variables

All payment settings live in `.env`. The relevant keys (see `.env.example`):

    PAYMENT_PROVIDER=mock              # mock | telr | stripe
    STRIPE_SECRET_KEY=                 # from Stripe dashboard (test mode)
    STRIPE_WEBHOOK_SECRET=             # from Stripe webhook endpoint (test mode)
    TELR_STORE_ID=                     # from Telr dashboard (sandbox)
    TELR_AUTH_KEY=                     # from Telr dashboard (sandbox)
    PAYMENT_WEBHOOK_SECRET=            # generic secret for non-Stripe providers
    WEBHOOK_SIGNATURE_ENFORCED=true    # never set to false in production
    ENABLE_MOCK_PAYMENTS=false         # must be false in production

**Important:** `ENABLE_MOCK_PAYMENTS=true` in production causes
`app/core/config.py` to raise a `ValueError` at startup.

---

## 2. Stripe — test mode (recommended first)

### 2.1 Create a Stripe account

1. Go to https://dashboard.stripe.com/register
2. Complete signup (test mode is free — no card needed).
3. In the dashboard, make sure the Test mode toggle is ON.

### 2.2 Get your API keys

1. Go to Developers → API keys.
2. Copy the Secret key (starts with `sk_test_...`).
3. Put it in `.env`:

       STRIPE_SECRET_KEY=sk_test_...

### 2.3 Set up the webhook endpoint

Stripe must POST events to a publicly reachable URL.

**Option A — Production (VPS with domain):**
1. Go to Developers → Webhooks → Add endpoint.
2. URL: `https://<your-domain>/payments/webhook/stripe`
3. Events to listen: `payment_intent.succeeded`, `payment_intent.payment_failed`.
4. Copy the Signing secret (starts with `whsec_...`).
5. Put it in `.env`:

       STRIPE_WEBHOOK_SECRET=whsec_...

**Option B — Local dev (Stripe CLI):**
1. Install the Stripe CLI: https://stripe.com/docs/stripe-cli
2. Run:

       stripe login
       stripe listen --forward-to localhost:8000/payments/webhook/stripe

3. The CLI prints a `whsec_...`. Put it in `.env`.

**Option C — Cloudflare Tunnel (no VPS):**
1. Install `cloudflared`.
2. Run: `cloudflared tunnel --url http://localhost:8000`
3. Use the printed `https://...trycloudflare.com` URL as your webhook URL.
4. Add it to Stripe dashboard (as in Option A).

### 2.4 Switch the provider

In `.env`:

    PAYMENT_PROVIDER=stripe

Restart the app:

    systemctl restart platform-x   # on VPS
    # or: uvicorn app.main:app --reload   # in dev

### 2.5 Run one end-to-end payment

1. Create a booking as a logged-in user.
2. Go to checkout. Stripe test card: `4242 4242 4242 4242`, any future
   expiry, any CVC.
3. Stripe will POST a `payment_intent.succeeded` event to your webhook.
4. Verify:
   - Your server log shows `POST /payments/webhook/stripe 200`.
   - The payment in the DB has `status=success`.

**If signature fails (401):**
- Check `STRIPE_WEBHOOK_SECRET` matches what Stripe dashboard shows.
- Check the server clock is correct (Stripe tolerance is 300s).
- Check `WEBHOOK_SIGNATURE_ENFORCED=true` and the secret is not empty.

---

## 3. Telr — sandbox

1. Register at https://telr.com (sandbox account is free).
2. Get Store ID and Auth Key from the dashboard.
3. Put in `.env`:

       TELR_STORE_ID=...
       TELR_AUTH_KEY=...
       PAYMENT_PROVIDER=telr

4. Configure Telr to POST to `https://<your-domain>/payments/webhook/telr`.
5. Set `PAYMENT_WEBHOOK_SECRET` to the shared secret Telr will use
   (if Telr supports custom headers) — otherwise Telr's own signature
   scheme will be added in a follow-up (see "Known gaps" below).

---

## 4. Verifying signature verification locally (no provider account)

If you want to verify the signature math without a Stripe account, run:

    pytest tests/test_webhook_signature.py tests/test_stripe_integration.py -v

14 tests cover: valid, invalid, missing, tampered body, wrong secret,
expired timestamp, malformed header, rotated v1.

---

## 5. Known gaps (Stage 7)

- **Stripe event → internal schema adapter** is not yet implemented.
  Our webhook endpoint expects `{provider_reference, status}`. Real
  Stripe events use a different shape. The adapter is a ~30-line
  function that maps `event.data.object` to our schema. Add it in
  `app/api/payments.py` before going live with Stripe.
- **Telr signature scheme** (if Telr uses its own, not generic HMAC)
  is not implemented. Check Telr docs when integrating.
- **Refund webhooks** — `charge.refunded` is not handled yet. Add
  alongside `payment_intent.*`.

---

## 6. Rollback / safety

- To disable webhooks temporarily: set `WEBHOOK_SIGNATURE_ENFORCED=false`
  in `.env` and restart. Do not leave this in production.
- To revert to mock: set `PAYMENT_PROVIDER=mock` and
  `ENABLE_MOCK_PAYMENTS=true` (dev only).

---

## 7. Acceptance criteria for Stage 7

- [ ] Stripe test-mode account created and keys in `.env`.
- [ ] Webhook endpoint registered in Stripe dashboard.
- [ ] One end-to-end payment: checkout → webhook → DB `status=success`.
- [ ] Webhook signature verified (no 401 in logs).
- [ ] `PAYMENT_PROVIDER` set to a real provider.
- [ ] `ENABLE_MOCK_PAYMENTS=false`.
