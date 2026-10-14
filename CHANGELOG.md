# Changelog

All notable changes to Platform-X are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to a semantic versioning scheme pre-1.0
(0.x.y) and post-1.0 (1.x.y).

> **Note for buyers:** this changelog summarizes the full evolution from
> the first working core (v0.1.0) to the sale-ready release (v1.0.17).
> For a complete git history, run `git log --oneline` (639 commits) and
> `git tag` (85 tags).

---

## [1.0.17] — 2026-10-14 — Investment Memo

### Added
- `docs/17-INVESTMENT-MEMO.md` — M&A-style memorandum (AED 5M+ floor).
- Buyer docs numbers synced: 1,509 tests, 252 Python files, 34,342 lines.

## [1.0.16] — 2026-10-14 — PostgreSQL Verified

### Added
- `docs/21-PG-VERIFICATION.md` — full verification report.
- Verified all 33 Alembic migrations on real PostgreSQL 18.2:
  - upgrade head, downgrade -1, re-upgrade head.
  - seed_all runs cleanly (20 tenants, 19 services, 1 admin).
  - API smoke test (health + tenants list) returns 200.

### Notes
- Uses `pg8000` on Termux (psycopg2/psycopg3 have no Android wheels).
  On Ubuntu 22.04, `psycopg2-binary` works normally.

## [1.0.15] — 2026-10-14 — Payment Test Mode Guide

### Added
- `docs/20-PAYMENT-TEST-MODE.md` — buyer guide for Stripe test-mode
  and Telr sandbox integration (env vars, webhook setup, end-to-end
  flow, known gaps).

## [1.0.14] — 2026-10-14 — Stripe Integration Tests

### Added
- `tests/test_stripe_integration.py` — 7 tests replicating Stripe's
  HMAC signature scheme end-to-end (valid, tampered, wrong secret,
  expired timestamp, missing header, malformed header, rotated v1).

### Changed
- HANDOFF test count: 1,502 -> 1,509.

## [1.0.13] — 2026-10-14 — License + Authors

### Added
- `AUTHORS.md` — Owner, methodology, transfer clause reference.
- `LICENSE` § TRANSFER ON SALE — explicit IP transfer on sale.
- README "License & Authors" section.

## [1.0.12] — 2026-10-14 — Phase 24 Clarified

### Changed
- Phase 24 (Cross-Business Rewards) marked POST-SALE across HANDOFF,
  `docs/16-MASTER-ROADMAP.md`, `docs/13-FUTURE-PHASES.md`.
- `docs/13-FUTURE-PHASES.md` marked as historical snapshot.

## [1.0.11] — 2026-10-14 — INTEGRATION-READY Labels

### Changed
- README: new "INTEGRATION-READY Features" section.
- MASTER-ROADMAP: B1 (Voice Booking) and B14 (Local Experiences)
  annotated as mock data / provider.
- docs/16 explicitly labels AI provider, payment provider, and
  installments as switchable.

## [1.0.10] — 2026-10-13 — verify-handoff.sh

### Added
- `scripts/verify-handoff.sh` — 6 automated consistency checks:
  version line, test count, Section 0.5 staleness, phase registration,
  Last updated, working tree.
- `--quick` mode skips pytest.

## [1.0.9] — 2026-10-13 — Docs Sync

### Changed
- Test count synced 1,487 -> 1,502 across:
  - Quickstart, HANDOFF, and 5 buyer-facing docs.
- Added verification date + runtime to the Test Count section.

## [1.0.8] — 2026-10-12 — Security Complete (Phase 89)

### Added
- `app/core/webhook_signature.py` — HMAC-SHA256 verification:
  - generic `X-PlatformX-Signature: sha256=<hex>`
  - Stripe `t=<ts>,v1=<hex>` with 300s tolerance
- 2FA for platform admins (TOTP via pyotp):
  - `POST /platform/auth/2fa/setup`, `/verify`, `/disable`, `/login`
  - `create_mfa_token()` with 5-minute lifetime
  - 2FA events recorded in audit_log
- Tests: 7 webhook signature + 8 admin 2FA.

### Changed
- `POST /payments/webhook/{provider}` verifies signature before
  accepting any payload. Mock provider gated by `ENABLE_MOCK_PAYMENTS`.
- Security checklist: 12/17 verified in code, 5 buyer-driven.

### Fixed
- Closed the last two real security gaps after Phase 68
  (webhook signature, admin 2FA).

## [1.0.0] — 2026-10-04 — Sale Ready

### Added
- Stage 5 (Production Readiness, Phases 81–85):
  - Deploy scripts, PostgreSQL migration prep, smoke test,
    buyer documentation, production env config.
- Stage 6 (Sales Preparation, Phases 86–88):
  - Handover package, sales assets, final audit + cleanup.

### Notes
- 1,487 tests passing at this point.
- Tagged v1.0.0-sale-ready.

---

## Pre-1.0 — Evolution Summary

> 80 releases from v0.1.0 to v0.99 grouped by development wave.
> Full per-tag detail available via `git log` and `git tag`.

### Wave 4 — Rewards, Referrals, and Blue-Ocean (v0.43.0 → v0.99.0)

Major themes:
- Rewards & Referral engine (Stage 4, Phases 75–80) — immutable
  ledger, server-authoritative, idempotent.
- AI depth: Voice Booking, Trip Memory, Budget Optimizer, Group
  Coordinator, Auto-Repricing.
- Blue-ocean features: Price Locks, Smart Waitlist, Trust Score,
  Instant Refund AI, Family Mode, Multi-Business Bundles.
- Split payment / installments.
- Multi-property dashboard.
- Production audit (Stage 3, Phases 66–69).

### Wave 3 — Feature Completeness (v0.30.0 → v0.42.0)

Major themes:
- Rooms, rate plans, promotions.
- Reviews, messaging, group booking.
- Nearby, recent searches, price alerts.
- Loyalty redemption, AI location, AI trip memory.

### Wave 2 — AI Foundation (v0.10.0 → v0.29.0)

Major themes:
- AI Business Assistant (pricing coach).
- Dynamic pricing rules.
- Leaderboard with AI scoring.
- Content writer, marketing copilot.
- Occupancy, market insights, review responder.
- Public API + webhooks.

### Wave 1 — Core Platform (v0.1.0 → v0.9.0)

Major themes:
- Booking lifecycle (search → intent → confirmation).
- Frontend (Jinja templates).
- Multi-tenant architecture.
- Admin panel.
- i18n (EN / AR / FIL / HI).
- Notifications.
- Business owner tools.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| Added | new features |
| Changed | changes in existing behavior |
| Deprecated | features marked for removal |
| Removed | features removed |
| Fixed | bug fixes |
| Security | security-relevant changes |

---

## Conventions

- `vX.Y.Z-name` — tag format (semantic version + short label).
- Pre-1.0 (0.x.y): fast iteration, breaking changes allowed.
- 1.0+: stable API, semver respected.
- Full git history: 639 commits, 85 tags.
