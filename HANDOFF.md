# Platform-X — Project Handoff

> Complete reference for AI assistants, developers, and buyers.
> This document replaces all previous HANDOFF versions.
> For historical snapshots see `docs/ARCHIVE-HANDOFF-v1.0.18.md`.

**Version:** v1.0.20-quickstart-sync
**Last updated:** 2026-10-14
**Status:** SALE-READY (buyer-driven Stage 7 pending)
**Owner:** Benjamin Bahoush (platformx2026@gmail.com)

---

## 1. Executive Summary

Platform-X is an **AI-first, multi-tenant hospitality platform** — a
production-shaped codebase ready for immediate deployment by a buyer
with hospitality operations and licensing in the MENA region.

**What is being sold:** the complete platform — source code, tests,
documentation, deployment scripts, architectural design, AI workflow
methodology, and handover commitment until the buyer's platform is live.

**What is NOT included (buyer's responsibility):** brand name, domain,
VPS, payment provider account, AI provider key, hospitality operating
license, and ongoing operations.

**Asking price:** AED 5,000,000 minimum (~USD 1.36M).
**Full sales documents:** `docs/17-INVESTMENT-MEMO.md`.

---

## 2. Project State (quick reference)

| Metric | Value |
|--------|-------|
| Version | v1.0.18-changelog |
| Python files | 252 |
| Lines of Python | 34,342 |
| Automated tests | 1,509 (all passing) |
| Test runtime | ~60s parallel |
| Models | 46 |
| Endpoints | 220+ |
| Templates | 82 |
| Migrations | 33 (verified on PostgreSQL 18.2) |
| Features shipped | 79 |
| Git tags | 85 |
| Git commits | 639 |

**Full test suite:** `pytest tests/ -n auto` — 1,509 pass, ~60s.

**HANDOFF verification:** `bash scripts/verify-handoff.sh` — 6 checks.

---

## 3. Roadmap Zero-to-Sale (7 stages)

The full end-to-end roadmap lives in `docs/16-MASTER-ROADMAP.md`.
Summary:

| Stage | Goal | Status |
|-------|------|--------|
| 0 | Strategic foundation | COMPLETE |
| 1 | Core platform | COMPLETE |
| 2 | Feature waves 1–4 (parity + blue-ocean) | COMPLETE |
| 3 | Production audit (security, perf, bugs) | COMPLETE |
| 4 | Rewards & Referral Engine | COMPLETE |
| 5 | Production Readiness (deploy, PostgreSQL, docs) | COMPLETE |
| 6 | Sales Preparation (handover, pitch, cleanup) | COMPLETE |
| 7 | Post-sale (buyer-driven) | PENDING BUYER |

**Phase 89 (Security Completion, 2026-10-12)** closed the last two
security gaps: payment webhook HMAC-SHA256 signature verification, and
TOTP 2FA for platform admins.

**Phase 24 (Cross-Business Rewards)** is marked POST-SALE — not in the
current scope. Buyer may activate it in Stage 7 if desired.

---

## 4. What is Built

79 features shipped. Full list in `docs/16-MASTER-ROADMAP.md`.

### 4.1 Core platform
- Multi-tenant architecture (subdomain or custom domain per tenant)
- Booking lifecycle: search → intent → confirmation → receipt
- Orders, payments, notifications
- Rewards & referral engine (immutable ledger, server-authoritative)
- Public API + webhooks + per-tenant API keys
- Multi-language: EN / AR / FIL / HI

### 4.2 AI capabilities (15+)
AI Business Assistant, Content Writer, Marketing Copilot,
Review Writer + Responder, Guest Assistant, Voice Booking,
Trip Memory, Budget Optimizer, Group Coordinator, Location
Recommender, Receptionist, Upsell Engine, Auto-Repricing,
Business Leaderboard Scoring.

### 4.3 Blue-ocean features
Predictive Price Locks, Smart Waitlist, Trust Score per Business,
Multi-Business Bundle Deals, Deep Peer Benchmark, Instant Refund AI,
Family & Kids Mode, Split Payment / Installments, Live Local
Experiences, Voice Booking.

### 4.4 INTEGRATION-READY features (mock data/provider)
- AI Voice Booking — transcript input only (voice→text deferred)
- Local Experiences — mock event data (haversine + AI logic are real)
- AI Provider — switchable via `AI_PROVIDER` env
- Payment Provider — switchable via `PAYMENT_PROVIDER` env
- Installments — mock payment capture (ledger logic is real)

See `README.md` § "INTEGRATION-READY Features" for details.

---

## 5. Technology

| Layer | Technology |
|-------|-----------|
| Language | Python 3.13 |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite (dev) / PostgreSQL 18.2 (prod, verified) |
| Migrations | Alembic (33 revisions) |
| Templates | Jinja2 (82 files) |
| Auth | JWT (access + refresh) + TOTP 2FA for admins |
| Webhooks | HMAC-SHA256 (generic + Stripe) |
| AI providers | Gemini / OpenAI (switchable) |
| Payments | Telr / Stripe (abstraction ready) |
| Deployment | Nginx + systemd (scripts provided) |

**PostgreSQL driver note:** on Termux, `pg8000` is used (pure Python).
On Ubuntu 22.04, `psycopg2-binary` works normally. See
`docs/21-PG-VERIFICATION.md` for details.

---

## 6. Security Posture

Verified Phase 89 (v1.0.8-security-complete). 12/17 checklist items
verified in code. Remaining 5 are buyer-driven.

| Check | Status | Evidence |
|-------|--------|----------|
| Rate limiting | PASS | `app/core/rate_limit.py`, 40+ API files |
| Security headers | PASS | `app/core/security_headers.py` |
| JWT refresh | PASS | `app/api/auth.py` rotation + revocation |
| Password policy | PASS | `app/schemas/auth.py` (min 8, strength validator, bcrypt) |
| Account lockout | PASS | `app/services/user_service.py` (5 / 15 min) |
| Session revocation | PASS | `app/api/auth.py` revoke_by_token |
| CSRF | N/A | JWT header-based; no cookies |
| XSS audit | PASS | 0 issues (grep on safe filter, Markup, autoescape) |
| SQL injection audit | PASS | 0 raw SQL; SQLAlchemy ORM only |
| CORS restricted | PASS | `app/core/config.py` rejects localhost in prod |
| 2FA for admins | PASS | Phase 89 Step 2 (TOTP via pyotp) |
| Audit logs | PASS | `app/api/platform_admin.py` + AuditLog model |
| Payment webhook signature | PASS | Phase 89 Step 1 (HMAC-SHA256 + Stripe) |
| HTTPS enforced | BUYER | VPS + certbot |
| Secrets in secure store | BUYER | `.env` on VPS |
| Backup strategy | BUYER | VPS cron + scripts/deploy/backup.sh |
| PCI compliance | BUYER | Provider-dependent (Telr/Stripe) |

---

## 7. Test Coverage

- **1,509 automated tests**, all passing.
- **~60 seconds** parallel runtime (pytest-xdist).
- Full suite: `pytest tests/ -n auto`.
- Test categories: unit, integration, API, security, rewards ledger.

**PostgreSQL verification:** all tests pass on real PG 18.2 after
migration. See `docs/21-PG-VERIFICATION.md`.

---

## 8. Sale Package (buyer-facing documents)

| Document | Purpose |
|----------|---------|
| `docs/17-INVESTMENT-MEMO.md` | M&A-style memorandum (AED 5M+ floor) |
| `CHANGELOG.md` | Full project evolution v0.1.0 → v1.0.18 |
| `LICENSE` | Proprietary + TRANSFER ON SALE clause |
| `AUTHORS.md` | Owner + methodology |
| `docs/20-PAYMENT-TEST-MODE.md` | Stripe / Telr integration guide |
| `docs/21-PG-VERIFICATION.md` | PostgreSQL verification report |
| `docs/buyer/` | 12 buyer-facing documents |
| `docs/16-MASTER-ROADMAP.md` | Full 7-stage roadmap |
| `docs/15-AI-PLAYBOOK.md` | AI-driven development methodology |

### Buyer docs index (`docs/buyer/`)
ASSET-INVENTORY, BUYER-GUIDE, DEPLOY-GUIDE, DEPLOYMENT-STATUS,
HANDOVER-CHECKLIST, OPERATIONS, POSTGRES-MIGRATION, ROADMAP-FOR-BUYER,
SELLING-PITCH, TECH-DEBT-LIST, TECH-OVERVIEW, TRANSFER-GUIDE.

---

## 9. Known Gaps (honest disclosure)

- **No operating revenue** — Platform-X is a ready-to-deploy asset,
  not a running business.
- **No live tenants** — demos use seed data.
- **Stripe real-account end-to-end** not tested (signature integration
  tests pass; real account is buyer-driven).
- **Telr real integration** not tested (sandbox guide provided).
- **Voice Booking** accepts text transcripts, not raw voice input.
- **Local Experiences** uses mock event data (logic is real).
- **HTTPS, secrets, backup automation, PCI** — all buyer-driven.

Every gap is documented. No hidden issues.

---

## 10. Buyer Checklist (Stage 7)

After purchase:

1. [ ] Purchase VPS (Ubuntu 22.04, min 2 vCPU / 4 GB RAM).
2. [ ] Purchase domain.
3. [ ] Run `bash scripts/deploy/install.sh <domain> <repo-url>`.
4. [ ] Fill `.env` (DB, JWT secret, payment keys, AI keys).
5. [ ] Run `alembic upgrade head`.
6. [ ] Run `python -m app.scripts.seed_all`.
7. [ ] Set up SSL: `certbot --nginx`.
8. [ ] Connect payment provider (Telr / Stripe).
9. [ ] Connect AI provider key.
10. [ ] Verify with `bash scripts/smoke_test.sh`.
11. [ ] Onboard first tenant.
12. [ ] Brand launch.

Full guide: `docs/buyer/DEPLOY-GUIDE.md`.

---

## 11. How to Work with This Codebase

Platform-X uses a documented **human-directed, AI-assisted workflow**.
A new AI session should read these files in order:

1. `docs/00-NEW-CHAT-QUICKSTART.md` — authoritative for behavior.
2. `HANDOFF.md` (this file) — authoritative for state.
3. `docs/15-AI-PLAYBOOK.md` — full methodology.
4. `PROJECT-RULES.md` — quality bar.
5. `WORKING-METHOD.md` — user's workflow rules.

**Per-step workflow (mandatory):**

1. Write code + tests together.
2. `bash scripts/step.sh --test <path> --message "<msg>" --label <lbl>`
3. `bash scripts/handoff.sh "<desc>" <sha> "<msg>"`
4. At phase close: `bash scripts/verify-handoff.sh`

**Golden rules:**
- Backup before every change.
- One step at a time; test after each step.
- Commit only on green tests.
- No features without roadmap approval.

---

## 12. File Index

### Root
`README.md`, `HANDOFF.md`, `CHANGELOG.md`, `LICENSE`, `AUTHORS.md`,
`PROJECT-RULES.md`, `WORKING-METHOD.md`, `AI-CONTEXT.md`,
`SECRETS.md`, `Makefile`, `requirements.txt`, `alembic.ini`,
`pytest.ini`, `.env.example`.

### Core code
- `app/api/` — 40+ route modules
- `app/core/` — config, security, rate_limit, webhook_signature
- `app/models/` — 46 SQLAlchemy models
- `app/schemas/` — Pydantic schemas
- `app/services/` — business logic
- `app/scripts/` — seed scripts
- `app/static/`, `app/templates/`, `app/translations/`, `app/web/`

### Deployment
- `deploy/nginx.conf`, `deploy/platform-x.service`
- `scripts/deploy/install.sh`, `update.sh`, `backup.sh`, `restore.sh`
- `scripts/step.sh`, `handoff.sh`, `verify-handoff.sh`, `backup-full.sh`
- `scripts/smoke_test.sh`

### Documentation
- `docs/00-NEW-CHAT-QUICKSTART.md` → `docs/21-PG-VERIFICATION.md`
- `docs/buyer/` — 12 buyer docs
- `docs/ARCHIVE-HANDOFF-v1.0.18.md` — full historical HANDOFF

### Tests
`tests/` — 1,509 tests across 200+ modules

### Migrations
`alembic/versions/` — 33 revisions

---

## 13. Historical Milestones (summary)

- v0.1.0-core — first working booking flow.
- v0.5.0-security — JWT, rate limits, password policy.
- v0.10.0-ai-foundation — AI provider abstraction.
- v0.20.0-public-api — OpenAPI + webhooks + API keys.
- v0.21.0-wave0-part-a — foundation for waves.
- v0.35.0–v0.42.0 — Wave 2 (AI depth) + Wave 3 (blue-ocean).
- v0.43.0-ai-receptionist — Wave 2 complete.
- v0.51.0-voice-booking — Voice Booking shipped.
- v0.52.0-local-experiences — Local Experiences shipped.
- v0.60.0-rewards-complete — Rewards & Referral Engine.
- v1.0.0-sale-ready — Stages 5 + 6 complete.
- v1.0.8-security-complete — Phase 89 (webhook sig + 2FA).
- v1.0.9–v1.0.13 — docs sync, verify-handoff.sh, mock labels,
  Phase 24 clarity, LICENSE + AUTHORS.
- v1.0.14–v1.0.15 — Stripe integration tests + payment guide.
- v1.0.16 — PostgreSQL verified on real PG 18.2.
- v1.0.17 — Investment Memorandum.
- v1.0.18 — CHANGELOG + HANDOFF rewrite (this file).

---

## 14. How to Regenerate This HANDOFF

To regenerate the current HANDOFF state from the repo, run:

    cd ~/platform-x && bash scripts/ctx-print.sh

This prints: Quickstart, HANDOFF strategic sections, tags,
last commits, test status, and the "READY TO START" block.

---

**End of HANDOFF.**

For historical detail, see `docs/ARCHIVE-HANDOFF-v1.0.18.md`.
For sale inquiries, see `docs/17-INVESTMENT-MEMO.md`.
