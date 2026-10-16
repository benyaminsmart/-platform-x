# Platform-X — Technical Due Diligence Package

> **Audience:** The buyer's engineering team, CTO, or technical advisor.
> **Purpose:** A single, evidence-based technical dossier so a serious
> technical evaluator can assess Platform-X without reading the entire
> repository.
>
> **Principle:** Every claim in this document is traceable to a file,
> a test, or a git tag. Nothing here is marketing language.
>
> **Version:** v1.0.32-docs-final
> **Last updated:** 2026-10-16

---

## 1. Executive technical summary

| Item | Value |
|------|-------|
| Language | Python 3.13.13 |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite (dev) / PostgreSQL 18.2 (production, verified) |
| Migrations | Alembic — 33 revisions |
| Templates | Jinja2 — 82 files |
| Python files | 252 |
| Python lines | 34,342 |
| Automated tests | 1,509 — all passing |
| Test runtime | ~60 seconds parallel |
| Models | 46 SQLAlchemy models |
| API endpoints | 220+ |
| Dependencies | 36 (see `requirements.txt`) |
| Deployment | Nginx + systemd (scripts provided) |

**Test verification command:**

    pytest tests/ -n auto

**Expected output:** `1509 passed, ... in ~60s`.

---

## 2. Architecture overview

### 2.1 Application layout

    app/
    ├── api/            40+ route modules (one per domain)
    ├── core/           config, security, rate_limit, webhook_signature,
    │                   security_headers, logging_config
    ├── db/             SQLAlchemy engine, session, base
    ├── models/         46 SQLAlchemy models
    ├── schemas/        Pydantic v2 schemas
    ├── services/       business logic (booking, payment, reward, AI)
    ├── scripts/        seed scripts
    ├── static/         static assets
    ├── templates/      82 Jinja2 templates
    ├── translations/   i18n (EN, AR, FIL, HI)
    ├── web/            web-specific routes
    └── main.py         FastAPI application factory

Detailed architecture: `docs/01-ARCHITECTURE.md`.

### 2.2 Multi-tenancy model

- Each tenant has a `tenant_id` (UUID).
- Data isolation is enforced at the application layer (every query
  filters by tenant).
- Routing: each tenant is served on a subdomain or custom domain.
- Tenant admin can configure branding, services, and staff.

Detailed model: `docs/08-DATA-MODEL.md`.

### 2.3 Authentication and authorization

- **Users:** JWT with access token (30 min) + refresh token (30 days).
- **Admins:** JWT + optional TOTP 2FA (Phase 89).
- **API keys:** per-tenant API keys for the public API.
- **Roles:** admin, business owner, staff, guest.
- **Session revocation:** `revoke_by_token` rotates sessions on refresh.

Detailed security: `docs/10-SECURITY.md`.

### 2.4 Webhook architecture

- **Outbound:** tenant-configured webhooks signed with HMAC-SHA256
  (`X-PlatformX-Signature: sha256=<hex>`).
- **Inbound (payments):** `/payments/webhook/{provider}` verifies
  HMAC before accepting. Generic scheme + Stripe scheme (t=<ts>,v1=<hex>).
- Implementation: `app/core/webhook_signature.py` (Phase 89).

---

## 3. Technology stack details

### 3.1 Core dependencies (36 total)

Top-level frameworks and libraries:

| Category | Library | Purpose |
|----------|---------|---------|
| Web framework | FastAPI | HTTP routing, OpenAPI |
| ASGI server | Uvicorn | Production runtime |
| ORM | SQLAlchemy 2.0 | Data access |
| Migrations | Alembic | Schema versioning |
| Validation | Pydantic v2 | Schemas, config |
| Templating | Jinja2 | Server-side rendering |
| Auth | python-jose[cryptography] | JWT signing |
| Password | bcrypt | Password hashing |
| Rate limiting | slowapi | Per-route limits |
| 2FA | pyotp | TOTP |
| Email | resend | Transactional email |
| Testing | pytest + pytest-xdist | Parallel test execution |
| HTTP client | httpx | Outbound calls |
| DB driver | pg8000 (Termux) / psycopg2 (Ubuntu) | PostgreSQL |

Full list: `requirements.txt`.

### 3.2 Why these choices

- **FastAPI** — async-first, Pydantic v2 native, automatic OpenAPI.
- **SQLAlchemy 2.0** — modern typed ORM, dialect-agnostic.
- **PostgreSQL** — production-grade, standard for multi-tenant SaaS.
- **Alembic** — standard migration tool for SQLAlchemy.
- **Jinja2** — server-rendered templates; no JS build step required.
- **pg8000** (Termux only) — pure-Python PostgreSQL driver, since
  psycopg2 and psycopg3 have no Android wheels.
- **psycopg2-binary** (Ubuntu) — standard production driver; wheels
  available for linux/amd64 and linux/arm64.

---

## 4. Verification evidence

### 4.1 Test suite

- **1,509 tests**, all passing.
- Runtime: ~60 seconds parallel (pytest-xdist).
- Categories: unit, integration, API, security, rewards ledger,
  webhook signature, 2FA.
- Command: `pytest tests/ -n auto`.
- Report: `docs/12-TESTING.md`.

### 4.2 PostgreSQL verification

- All 33 Alembic migrations run cleanly on real PostgreSQL 18.2.
- Upgrade + downgrade + re-upgrade tested.
- Seed data verified (20 tenants, 19 services, 1 admin).
- API smoke test: `/health` 200, `/tenants` 20 items.
- Report: `docs/21-PG-VERIFICATION.md`.

### 4.3 Security verification (Phase 89)

- Payment webhook signature verification (HMAC-SHA256, generic + Stripe).
- TOTP 2FA for platform admins (setup, verify, disable, login).
- XSS audit: 0 issues (grep on unsafe filters, autoescape).
- SQL injection audit: 0 issues (SQLAlchemy ORM only).
- 12/17 security checklist items verified in code.
- Report: `docs/10-SECURITY.md`.

### 4.4 Stripe signature integration tests

- 7 tests replicate Stripe's exact HMAC scheme.
- Cover: valid, tampered, wrong secret, expired, missing, malformed,
  rotated v1.
- Report: `docs/20-PAYMENT-TEST-MODE.md`.

### 4.5 HANDOFF consistency

- `scripts/verify-handoff.sh` runs 7 automated checks:
  version lines, test count, checklist state, phase registration,
  Last updated, working tree, Quickstart drift.
- Currently 6/6 pass (or 7/7 with full pytest).

---

## 5. Deployment

### 5.1 Target environment

- **OS:** Ubuntu 22.04 LTS
- **Minimum VPS:** 2 vCPU, 4 GB RAM, 40 GB SSD
- **Web server:** Nginx (config provided in `deploy/nginx.conf`)
- **Process manager:** systemd (unit provided in `deploy/platform-x.service`)
- **Database:** PostgreSQL 18.2 (or 14+)
- **Python:** 3.13

### 5.2 Deployment steps

    1. Provision VPS (Ubuntu 22.04).
    2. Install: git, python3.13, python3.13-venv, postgresql, nginx, certbot.
    3. Clone repository to /opt/platform-x.
    4. Run: bash scripts/deploy/install.sh <domain> <repo-url>
    5. Fill .env with secrets (DB password, JWT secret, etc.).
    6. Run: alembic upgrade head
    7. Run: python -m app.scripts.seed_all
    8. Configure Nginx + SSL (certbot --nginx).
    9. Start: systemctl start platform-x

Full guide: `docs/buyer/DEPLOY-GUIDE.md`.

### 5.3 Backup and restore

- `scripts/deploy/backup.sh` — full backup (DB + files).
- `scripts/deploy/restore.sh` — restore from backup.
- Recommendation: cron daily + weekly to external storage.

---

## 6. Operational vs. buyer-driven features

Critical for the buyer's technical team to understand what works
out of the box and what requires the buyer's own accounts.

### 6.1 Fully operational (works immediately after deploy)

| Feature | Notes |
|---------|-------|
| Multi-tenant booking flow | All templates, routes, tests pass |
| Rewards & referral engine | Immutable ledger, server-authoritative |
| Public API + webhooks | HMAC-SHA256 signing (outbound) |
| Webhook signature verification (inbound) | Generic + Stripe |
| Admin panel + 2FA | TOTP via pyotp |
| Rate limiting | 40+ API files |
| Audit logs | All admin actions logged |
| i18n | EN, AR, FIL, HI |
| Database migrations | 33 revisions verified on PG 18.2 |

### 6.2 INTEGRATION-READY (works with mock, needs buyer's account)

| Feature | What is mock | What is real |
|---------|--------------|--------------|
| AI provider | Default replies | Full integration layer; switch to Gemini/OpenAI via env |
| Payment provider | Provider selection | Full abstraction; Telr/Stripe/PayTabs ready |
| AI Voice Booking | Voice→text input | Intent parsing, search, AI polish |
| Local Experiences | Event data | Haversine distance, AI recommendation |
| Installments | Payment capture | Ledger, scheduling logic |

### 6.3 Buyer-driven (requires buyer's accounts/licenses)

| Item | Why |
|------|-----|
| VPS / hosting | Buyer's own account |
| Domain | Buyer's own purchase |
| Payment provider account | Buyer's KYC with Telr/Stripe/PayTabs |
| AI provider key | Buyer's account (Gemini/OpenAI) |
| SSL certificate | Free via Let's Encrypt on buyer's VPS |
| Hospitality operating license | Per-jurisdiction |
| HTTPS enforcement | Nginx + certbot on buyer's VPS |
| Secrets management | `.env` on buyer's VPS |
| Backup automation | Cron on buyer's VPS |
| PCI compliance | Provider's responsibility (Telr/Stripe) |

### 6.4 Known technical gaps

| Gap | Impact | Effort to close |
|-----|--------|-----------------|
| Stripe event → internal schema adapter | Stripe events won't parse without ~30 lines of adapter | ~1 hour |
| Telr signature scheme | If Telr uses custom scheme, needs research | ~2–4 hours |
| Refund webhook handling (`charge.refunded`) | Not handled | ~2 hours |
| Voice→text (real voice input) | Voice Booking accepts text only | External service integration |

Documented in `docs/20-PAYMENT-TEST-MODE.md` §5 and
`docs/buyer/TECH-DEBT-LIST.md`.

---

## 7. Code quality and maintainability

### 7.1 Code organization

- One module per domain in `app/api/`.
- Business logic in `app/services/` (not in routes).
- Schemas separate from models (Pydantic v2 vs SQLAlchemy).
- Config centralized in `app/core/config.py`.
- No `from __future__ import annotations` where it breaks Pydantic
  (documented pitfall).

### 7.2 Testing discipline

- Every feature has tests.
- Tests run in parallel (~60s).
- Fixtures use globally unique slugs/emails for xdist safety.
- No flaky tests (verified across multiple runs).

### 7.3 Logging

- Structured logging via `app/core/logging_config.py`.
- Request IDs propagated.
- No secrets logged.

### 7.4 Documentation

- Every architectural decision in `docs/06-DECISIONS.md`.
- Every phase in `docs/16-MASTER-ROADMAP.md`.
- Methodology in `docs/15-AI-PLAYBOOK.md`.

---

## 8. Dependencies and licensing

### 8.1 Direct dependencies

36 packages in `requirements.txt`. All are widely used,
production-grade, and permissively licensed (MIT, Apache 2.0,
BSD). No GPL or copyleft dependencies.

Full audit: `docs/29-LICENSE-AUDIT.md` (to be created).

### 8.2 Third-party assets

- **Icons / fonts:** standard open-source (Inter, system fonts).
- **Images:** no copyrighted third-party images shipped.
- **AI-generated code:** documented in `AUTHORS.md`.

---

## 9. Handover and support

- **Handover:** seller supports buyer's team until platform is
  deployed and declared live (not time-boxed).
- **Emergency support:** 12 months after go-live for seller-authored
  code.
- **Documentation transfer:** all docs, including the AI-driven
  development methodology.
- **Optional paid service:** remote activation on the buyer's VPS.

See `docs/18-SALE-AGREEMENT.md` for the full term sheet.

---

## 10. Contact

- **Email:** platformx2026@gmail.com
- **Subject:** "Platform-X — Technical Due Diligence"

---

## Document control

- **Version:** 1.0
- **Date:** 2026-10-16
- **Author:** Benjamin Bahoush (with AI assistance)
- **Status:** Ready for buyer's technical team
