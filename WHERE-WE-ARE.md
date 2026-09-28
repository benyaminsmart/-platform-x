# Platform-X — Current Status

**Last updated:** 2026-09-28 (evening)

## Current Phase: 13 (Business Onboarding Tools) — NEXT (after Phase 12 for subdomains)

### Done:
- Step 1: Resend SDK installed
- Step 2: email_service.py + email templates + hooks
  - Welcome email on register
  - Booking confirmation email on payment
  - EMAIL_ENABLED=false by default (no-op)

### Waiting:
- Resend API Key (user needs to register at resend.com)
- Add to .env:
  - RESEND_API_KEY=re_xxx
  - EMAIL_FROM=onboarding@resend.dev
  - EMAIL_FROM_NAME=Platform-X
  - EMAIL_ENABLED=true
- Then restart: sv restart platform-x-api

### Remaining Phase 11 Steps:
- Step 3: Password Reset Flow
- Step 4: Notification Center UI (Account tab)
- Step 5: SMS Provider (Twilio)
- Step 6: User Notification Preferences
- Step 7: Milestone Close (v0.8.0-notifications)

## Phase Order (as decided by user):
1. Phase 11 — Notifications (in progress)
2. Phase 10 — Payment Production (Telr/Stripe) — needs Business Account
3. Phase 13 — Business Onboarding Tools
4. Phase 14 — API + Webhooks + SDK
5. Phase 17 — AI Assistant
6. Phase 8 — Rewards + Referral (when user provides plan)
7. Phase 12 — VPS + Domain + Named Tunnel (needs purchase)
8. Phase 15 — Trianon Migration
9. Phase 16 — Mobile App

## Tags:
- v0.7.0-i18n (last)
- v0.6.0-admin
- v0.5.0-security
- v0.4.0-full-flow
- v0.3.0-polish
- v0.2.0-frontend
- v0.1.0-core

## Live URL:
https://statement-lee-med-fraction.trycloudflare.com

## After any Termux restart:
cd ~/platform-x && sv up platform-x-api && sv up platform-x-tunnel && sleep 20 && bash start-platform.sh
