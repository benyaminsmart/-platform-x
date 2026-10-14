# Platform-X — Investment Memorandum

> **Confidential — for serious acquisition inquiries only.**
> **Date:** 2026-10-14
> **Version:** 1.0
> **Contact:** platformx2026@gmail.com

---

## Executive Summary

**Platform-X** is an AI-first, multi-tenant hospitality platform — a
production-shaped codebase ready for immediate deployment by a buyer
with hospitality operations and licensing in the MENA region.

**What is being sold:** the complete platform — source code, tests,
documentation, deployment scripts, architectural design, AI workflow
methodology, and a handover commitment until the buyer's platform is
live.

**What is NOT included (buyer's responsibility):** brand name, domain,
VPS, payment provider account, AI provider key, hospitality operating
license, and ongoing operations.

**Asking price:** AED 5,000,000 minimum (~USD 1.36M).

**Why this matters:** Booking.com and Agoda operate on 15–20-year-old
data architectures. Retrofitting AI into them requires rebuilding their
data layer. Platform-X was designed AI-first from day one.

---

## 1. The Opportunity

### 1.1 Market context

> [PLACEHOLDER — seller to complete]
>
> Provide here: MENA hospitality market size, growth rate, digitization
> gap, AI adoption curve in regional hospitality. Cite sources
> (e.g., Statista, McKinsey, STR, Colliers, Knight Frank).

### 1.2 Why AI-first matters

> [PLACEHOLDER — seller to complete]
>
> Explain why legacy OTAs cannot pivot, and why an AI-first platform
> captures a structural advantage. Include 2–3 concrete examples.

### 1.3 Timing

> [PLACEHOLDER — seller to complete]
>
> Why now? Regulatory shifts (UAE/Saudi tourism vision), post-COVID
> recovery, AI cost curve, talent availability.

---

## 2. Product Overview

Platform-X is a **multi-tenant SaaS** for hospitality businesses:
hotels, restaurants, tour operators, entertainment providers, and
experience curators.

### 2.1 Core capabilities

- Multi-tenant architecture (subdomain or custom domain per tenant)
- Booking lifecycle: search → intent → confirmation → receipt
- Orders, payments, notifications
- Rewards & referral engine — immutable ledger, server-authoritative
- Public API + webhooks + per-tenant API keys
- Multi-language: English, Arabic, Filipino, Hindi

### 2.2 AI capabilities (15+)

1. AI Business Assistant (pricing coach)
2. AI Content Writer + onboarding
3. AI Marketing Copilot
4. AI Review Writer + Responder
5. AI Guest Assistant
6. AI Voice Booking (transcript input)
7. AI Trip Memory
8. AI Budget Optimizer
9. AI Group Coordinator
10. AI Location Recommender
11. AI Receptionist
12. AI Upsell Engine
13. AI Auto-Repricing
14. AI Review Responder
15. AI Business Leaderboard Scoring

### 2.3 Blue-ocean features

- Predictive Price Locks
- Smart Waitlist
- Trust Score per Business
- Multi-Business Bundle Deals
- Deep Peer Benchmark
- Instant Refund AI
- Family & Kids Mode
- Split Payment / Installments
- Live Local Experiences (mock data layer, real logic)
- Voice Booking (transcript input)

### 2.4 Business owner tools

- Multi-property dashboard
- Occupancy analytics
- Competitor insights
- Business leaderboard + AI scoring
- Public API + API keys + webhooks
- Export / reports

**79 features shipped in total.**

---

## 3. Technology

### 3.1 Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.13 |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite (dev) / PostgreSQL 18.2 (prod, verified) |
| Migrations | Alembic (33 revisions, all verified on real PG) |
| Templates | Jinja2 (82 files) |
| Auth | JWT (access + refresh) + TOTP 2FA for admins |
| Webhooks | HMAC-SHA256 (generic + Stripe) |
| AI providers | Gemini / OpenAI (switchable) |
| Payments | Telr / Stripe (abstraction ready) |
| Deployment | Nginx + systemd (scripts provided) |

### 3.2 Code metrics

- Python files: 252
- Lines of Python: 34,342
- Automated tests: **1,509 (all passing)**
- Test runtime: ~60s parallel
- Models: 46
- Endpoints: 220+
- Templates: 82
- Migrations: 33 (verified on PostgreSQL 18.2)

### 3.3 Quality

- PostgreSQL migration verified with upgrade + downgrade + re-upgrade.
- Seed scripts run cleanly (20 tenants, 19 services, 1 admin).
- All tests pass on a real PostgreSQL instance.
- See `docs/21-PG-VERIFICATION.md`.

### 3.4 Security posture

Verified Phase 89 (v1.0.8-security-complete):

- Rate limiting on 40+ API files
- Security headers middleware
- JWT with refresh + revocation
- Bcrypt password hashing
- Account lockout (5 attempts / 15 min)
- CORS restricted in production
- 2FA for platform admins (TOTP, pyotp)
- Payment webhook signature verification (HMAC-SHA256, generic + Stripe)
- XSS audit: 0 issues
- SQL injection audit: 0 issues
- Audit logs for admin actions

12/17 security checklist items verified in code. Remaining 5 are
buyer-driven (HTTPS, secrets-in-store, backup automation, PCI, and
production backups — all handled on the buyer's VPS).

---

## 4. Market Analysis

> [PLACEHOLDER — seller to complete]
>
> Sections to fill:
> - Total addressable market (TAM) in MENA hospitality tech
> - Serviceable addressable market (SAM) — number of hotels,
>   restaurants, tour operators in target countries
> - Serviceable obtainable market (SOM) — realistic 3-year capture
> - Competitor landscape (Booking.com, Agoda, local players)
> - Platform-X differentiation matrix
> - Regulatory landscape per country (UAE, KSA, Qatar, Kuwait)

---

## 5. Business Model

Platform-X generates revenue from **tenants** (hospitality businesses),
not from end-users. Guests use the platform for free.

### 5.1 Revenue streams

1. **Subscription** — monthly/yearly platform access per tenant tier
2. **Transaction commission** — % of each booking handled by Platform-X
3. **Premium features** — add-ons beyond the base plan
4. **Setup / onboarding fees** — one-time per new tenant

### 5.2 Tenant tiers (proposed)

| Tier | Target | Features | Price (AED/month, proposed) |
|------|--------|----------|------------------------------|
| Starter | Small hotels, independent restaurants | Bookings, basic analytics | [PLACEHOLDER] |
| Growth | Mid-size hotels, tour operators | + AI assistant, marketing | [PLACEHOLDER] |
| Enterprise | Hotel chains, multi-property | + API, webhooks, custom SLAs | [PLACEHOLDER] |

> [PLACEHOLDER — seller to complete pricing tiers]

---

## 6. Revenue Projections

> Three scenarios. Assumptions are explicit so the buyer can adjust.

### 6.1 Assumptions (common)

- Year 1 target: 30 tenants (Starter + Growth mix)
- Year 2 target: 120 tenants
- Year 3 target: 300 tenants
- Average subscription: AED 1,500/month (placeholder)
- Average commission: 3% of booking value
- Average booking value: AED 800
- Average bookings per tenant per month: 50
- Churn: 5% annually (low, B2B hospitality)

### 6.2 Conservative scenario

> [PLACEHOLDER — seller to complete with actual projections]

### 6.3 Realistic scenario

> [PLACEHOLDER — seller to complete with actual projections]

### 6.4 Optimistic scenario

> [PLACEHOLDER — seller to complete with actual projections]

### 6.5 Break-even analysis

> [PLACEHOLDER — seller to complete]

---

## 7. Unit Economics

> [PLACEHOLDER — seller to complete]
>
> Provide: CAC (customer acquisition cost), LTV (lifetime value),
> LTV/CAC ratio, payback period, ARPU (average revenue per tenant).

---

## 8. What the Buyer Gets

- **Source code** — 252 Python files, 34,342 lines
- **Tests** — 1,509 automated tests, all passing
- **Documentation** — HANDOFF.md + docs/00–21 + docs/buyer/ (12 files)
- **Deploy scripts** — Nginx, systemd, install/update/backup
- **Database migrations** — 33 Alembic revisions, verified on PostgreSQL
- **Architecture design** — decisions documented in docs/06-DECISIONS.md
- **AI workflow methodology** — the full development protocol
  (docs/15-AI-PLAYBOOK.md) as a transferable asset
- **Handover commitment** — seller supports buyer's team until the
  platform is live and operational; ongoing emergency support for
  seller-authored code thereafter
- **Optional paid activation service** — remote setup on the buyer's VPS

---

## 9. What the Buyer Provides

- **Brand name** — the buyer selects and owns the final brand
- **Domain** — purchased by the buyer
- **VPS / server** — Ubuntu 22.04, min 2 vCPU / 4 GB RAM
- **Hospitality operating license** — buyer's responsibility in target
  jurisdictions
- **Payment provider account** — Telr / Stripe / PayTabs, buyer's KYC
- **AI provider key** — Gemini / OpenAI, buyer's account
- **SSL certificate** — free via Let's Encrypt (on the buyer's VPS)
- **Ongoing operations** — sales, support, feature roadmap after handover

---

## 10. Valuation & Terms

### 10.1 Asking price

- **Floor:** AED 5,000,000 (~USD 1.36M)
- **Target range:** AED 5,000,000 – AED 7,000,000

### 10.2 Basis

- Complete codebase (34k+ lines, 1,509 tests, 79 features)
- Verified PostgreSQL migration + rollback
- Full security posture (webhook signatures, admin 2FA, audits)
- Documentation + deploy scripts + handover
- Legal transfer readiness (LICENSE § TRANSFER ON SALE)

### 10.3 Payment terms

> [PLACEHOLDER — seller to define: lump sum, milestones, escrow]

### 10.4 Transfer process

1. NDA signed
2. Read-only repository access for due diligence
3. Offer and negotiation
4. Sale agreement signed (IP transfer per LICENSE)
5. Payment via agreed method
6. Repository and asset transfer
7. Handover begins

---

## 11. Risk Factors

**Honest disclosure:**

- **No operating revenue yet.** Platform-X is a ready-to-deploy asset,
  not a running business. Revenue depends on the buyer's execution.
- **No live tenants yet.** All demos use seed data.
- **Payment provider integration** has been tested with HMAC signature
  simulation but not with a live Stripe/Telr account.
- **Voice Booking** accepts text transcripts, not raw voice input.
- **Local Experiences** uses mock event data; the AI logic is real.
- **Regulatory risk** — hospitality licensing varies by jurisdiction.
- **Competition** — Booking.com and Agoda are large and well-capitalized.
- **Key-person risk** — the AI-driven workflow depends on the seller's
  documented methodology; the buyer must internalize it.

---

## 12. Roadmap Post-Sale

**Stage 7 (buyer-driven):**

- VPS + domain + SSL setup
- PostgreSQL production deployment
- Payment provider activation (Telr / Stripe)
- AI provider key activation
- First tenant onboarding
- Brand launch
- **Optional:** Phase 24 (Cross-Business Rewards) module
- **Optional:** paid activation service by the seller

---

## 13. Appendix

### 13.1 Asset inventory

See `docs/buyer/ASSET-INVENTORY.md`.

### 13.2 Technical overview

See `docs/buyer/TECH-OVERVIEW.md`.

### 13.3 PostgreSQL verification

See `docs/21-PG-VERIFICATION.md`.

### 13.4 Payment test mode guide

See `docs/20-PAYMENT-TEST-MODE.md`.

### 13.5 Full roadmap

See `docs/16-MASTER-ROADMAP.md`.

### 13.6 Contact

- **Email:** platformx2026@gmail.com
- **Subject line:** "Platform-X — Acquisition Inquiry"
