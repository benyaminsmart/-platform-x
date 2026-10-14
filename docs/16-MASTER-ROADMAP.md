# Platform-X — Master Roadmap (Phase 0 → Sale)

> **Purpose:** The single end-to-end map of Platform-X from day one
> (Phase 0) to a sale-ready product. Written so a new AI session,
> a partner, or a potential buyer can understand **what was built,
> why, and what remains** — in one read.
>
> **Sources:** `HANDOFF.md` (state), `git tag --sort=creatordate`
> (milestones), `docs/14-ROADMAP-V3-COMPETITIVE.md` (strategy).
>
> **Last updated:** 2026-10-04
> **Current version:** v0.59.0-referral-engine

---

## 0. How to Read This Document

- **Stage 0–4:** what is already built (Phase 0 → 77).
- **Stage 5–6:** what remains to make it sale-ready (Phase 81–88).
- **Stage 7:** post-sale (buyer-driven).
- Every phase shows: number, title, status (✅ complete / ⏳ in progress / ❌ planned), the git tag (if shipped), and a short summary.

---

## 0.1 A Note on Phase Numbering

Platform-X uses **historical phase numbers** — some numbers are
intentionally skipped, deferred, or superseded. This is normal for a
project that evolved over 2+ years. Specifically:

- **Skipped:** Phase 1 (First Tenant Live — moved to Stage 7).
- **Superseded:** Phase 8 (Rewards v1 → replaced by Phases 75–80);
  Phase 24 (Cross-Business Rewards — deferred, may become a future
  module).
- **Moved to Stage 7 (buyer-driven):** Phases 10 (Payment Production),
  12 (VPS + Domain), 13 (Business Onboarding Tools),
  15 (Trianon Migration), 16 (Mobile App).
- **Rolled into Stage 5:** Phases 70–74 (Deploy scripts, PostgreSQL
  migration, production env, smoke test, sales docs). The work is
  preserved but renumbered under Stage 5 (Phases 81–85) for clarity.
- **First official shipping tag:** `v0.2.0-frontend` (there is no
  `v0.1.0` — the project's first internal milestone was not tagged).

**Numbers are not a continuous sequence from 0 to 88; they are the
map of what was actually shipped.** Every number that appears in this
document maps to a real, tagged milestone or a planned phase with a
clear owner.

---

## 1. Executive Summary

Platform-X is an **AI-First Hospitality Platform** designed to be
**better and more attractive than Booking.com and Agoda in every
dimension**. It serves three sides of the market:

- **Guests** — search, book, pay, review, get AI help at every step.
- **Businesses** — list services, manage bookings, price intelligently,
  and receive AI-generated insights.
- **Platform** — commission-based revenue, an immutable rewards ledger,
  a referral engine, and a full public API.

**What makes it different:** 20+ AI features and 15 "blue-ocean"
capabilities that Booking.com and Agoda do not offer (see Section 2).

**Current state (2026-10-04):**
- Version: `v0.59.0-referral-engine`
- Test suite: **1433 passing, 0 failing**
- Phase 77 (Referral Engine) just completed.
- **Stage 4 (Rewards Engine)** is at ~75%.
- **Stage 5–6 (Production readiness + Sales prep)** are the remaining
  free work, no purchases required.
- **Stage 7 (VPS + Payment + Domain)** is buyer-driven.

---

## 2. Competitive Advantage — What Booking/Agoda Don't Have

This section is the **heart of the sale**. Buyers are not purchasing
"another booking site" — they are purchasing a differentiated product
with unique AI layers and blue-ocean features.

### 2.1 Blue-Ocean Features (B1–B15)

| # | Feature | Phase | Tag | Why it matters |
|---|---------|-------|-----|----------------|
| B1 | AI Voice Booking | 64 | v0.51.0 | Guests can book by voice (⚠️ INTEGRATION-READY: transcript input only — voice→text deferred to Stage 7). |
| B2 | AI Auto-Repricing Live | 60 | v0.50.0 | Real-time dynamic pricing driven by AI. |
| B3 | Multi-Business Bundle Deals | 51 | v0.41.0 | Cross-business packages (hotel + restaurant + activity). |
| B5 | Instant Refund AI | 54 | v0.44.0 | AI previews refunds before the guest cancels. |
| B6 | AI Group Coordinator | 59 | v0.49.0 | Coordinates group bookings (rooms, meals, activities). |
| B7 | Predictive Price Locks | 47 | v0.37.0 | Guests lock a future price; the platform covers the delta. |
| B8 | Smart Waitlist | 48 | v0.38.0 | Auto-notifies guests when a sold-out slot frees. |
| B10 | Business AI Receptionist | 53 | v0.43.0 | AI drafts replies to guest messages for the business. |
| B11 | Trust Score per Business | 49 | v0.39.0 | Composite reputation score beyond ratings. |
| B12 | Deep Peer Benchmark | 52 | v0.42.0 | Businesses see how they compare to peers, privately. |
| B13 | AI Upsell Engine | 56 | v0.46.0 | Contextual up-sells on the booking page. |
| B14 | Live Local Experiences | 65 | v0.52.0 | Nearby experiences integrated (⚠️ INTEGRATION-READY: events are mock data; haversine + AI logic are real). |
| B15 | Family & Kids Mode | 55 | v0.45.0 | Filters tuned for traveling families. |

### 2.2 AI-First Layers

**Guest AI (Layer 2):**
- AI Location Recommender (45 — v0.35.0)
- AI Trip Memory (46 — v0.36.0)
- AI Budget Optimizer (50 — v0.40.0)

**Business AI (Layer 3):**
- AI Business Assistant / Pricing Coach (21 — v0.12.0)
- AI Content Writer + Importer (23 — v0.15.0)
- AI Marketing Copilot (25 — v0.16.0)
- AI Review Writer + Responder (28 — v0.19.0)
- AI Auto-Repricing (60 — v0.50.0)
- AI Group Coordinator (59 — v0.49.0)
- Business AI Receptionist (53 — v0.43.0)
- Instant Refund AI (54 — v0.44.0)
- AI Upsell Engine (56 — v0.46.0)
- AI Voice Booking (64 — v0.51.0) — ⚠️ INTEGRATION-READY: transcript-only, real voice input deferred

**Core AI Foundations:**
- AI Foundation (18 — v0.10.0)
- User AI Assistant (19 — v0.11.0)

### 2.3 Platform Unique Selling Points

- **Immutable Rewards Ledger** — every reward is auditable, idempotent,
  and reversable. (Phases 75–80.)
- **User Referral Engine** — full lifecycle, fraud checks, monthly caps.
  (Phase 77.)
- **Public API + Webhooks + SDK** — Phase 14 (v0.20.0).
- **Business Owner Panel** — Phase 20 (v0.9.0).
- **Multi-property Dashboard** — Phase 58 (v0.48.0).
- **Group Booking + AI Coordinator** — Phases 40, 59.
- **Trust Score + Peer Benchmark** — Phases 49, 52.
- **Split Payment / Installments** — Phase 57 (v0.47.0).

**Bottom line for the buyer:** ~40% of the codebase is AI or
differentiated features that Booking.com and Agoda do not have.
This is not a clone — it is a new category.

---

## 3. Stage 0 — Strategic Foundation

**Goal:** Lock the strategy before writing code.

### Phase 0 — Strategic Documents ✅
- Tag: pre-code.
- Delivered: mission, competitive positioning, architecture, data model,
  API spec, design system, security posture.
- Docs: `docs/00` through `docs/12`.

### Phase 0.5 — Executive Documents ✅
- Tag: pre-code.
- Delivered: `docs/14-ROADMAP-V3-COMPETITIVE.md`,
  `docs/15-AI-PLAYBOOK.md`, business model, tenant guide.

---

## 4. Stage 1 — Core Platform (Phase 1 → 30)

**Goal:** Working multi-tenant booking platform with guests, businesses,
payments (mock), admin, i18n, and the public API.

| Phase | Title | Status | Tag |
|-------|-------|--------|-----|
| 1 | First Tenant Live | SKIPPED (intentional — moved to Stage 7) | — |
| 2 | Core Architecture | ✅ | v0.2.0-frontend |
| 3 | Frontend | ✅ | v0.3.0-polish |
| 4 | UI Redesign + Rich Demo | ✅ | v0.4.0-full-flow |
| 5 | Full Feature Verification + Partner Onboarding | ✅ | v0.5.0-security |
| 6 | Security Hardening | ✅ | v0.5.0-security |
| 7 | Admin Panel UI | ✅ | v0.6.0-admin |
| 9 | i18n (EN / AR / FIL / HI) | ✅ | v0.7.0-i18n |
| 11 | Notifications | ✅ | v0.8.0-notifications |
| 20 | Business Owner Panel | ✅ | v0.9.0-business |
| 18 | AI Foundation | ✅ | v0.10.0-ai-foundation |
| 19 | AI Guest Assistant | ✅ | v0.11.0-user-ai |
| 21 | AI Business Assistant (Pricing Coach) | ✅ | v0.12.0-pricing-coach |
| 22 | Dynamic Pricing Rules | ✅ | v0.13.0-dynamic-pricing |
| 29 | Business Leaderboard + AI Scoring | ✅ | v0.14.0-leaderboard |
| 23 | AI Content Writer + Importer | ✅ | v0.15.0-content-ai |
| 25 | AI Marketing Copilot | ✅ | v0.16.0-marketing-ai |
| 26 | Real-Time Occupancy + Analytics | ✅ | v0.17.0-occupancy |
| 27 | Competitor / Market Insights | ✅ | v0.18.0-market-insights |
| 28 | AI Review Writer + Responder | ✅ | v0.19.0-reviews |
| 14 | Public API + Webhooks + SDK | ✅ | v0.20.0-public-api |
| 30 | Wave 0 part A (Foundation) | ✅ | v0.21.0-wave0-part-a |
| 31 | Wave 0 part B (VPS + Domain + Payment) | ❌ moved to Stage 7 | — |

**Phase 8 (Rewards + Referral v1):** superseded by Stage 4 (Phases 75–80).
**Phase 24 (Cross-Business Rewards):** deferred by user directive (2026-09-29).

**Phase 10 (Payment Production):** moved to Stage 7 (buyer-driven).
**Phase 12 (VPS + Domain):** moved to Stage 7 (buyer-driven).
**Phase 13 (Business Onboarding Tools):** planned for Stage 7.
**Phase 15 (Trianon Migration):** planned for Stage 7.
**Phase 16 (Mobile App):** future — not required for sale.

---

## 5. Stage 2 — Feature Waves 1–4 (Phase 32 → 65)

**Goal:** Reach parity with Booking/Agoda on the basics, and add
blue-ocean features on top.

### Wave 1 — Parity Essentials (Phase 32 → 44)

| Phase | Title | Status | Tag |
|-------|-------|--------|-----|
| 32 | Map + Location Search | ✅ | v0.22.0-map-location |
| 33 | Wishlist + Compare | ✅ | v0.23.0-wishlist-compare |
| 34 | Reports (CSV + PDF) | ✅ | v0.24.0-reports |
| 35 | Booking Modification + No-show | ✅ | v0.25.0-booking-mod |
| 36 | Room Inventory + Auto-assignment | ✅ | v0.26.0-rooms |
| 37 | Rate Plans | ✅ | v0.27.0-rate-plans |
| 38 | Promotions Engine | ✅ | v0.28.0-promotions |
| 39 | Review Photos + Guest Messaging | ✅ | v0.29.0-reviews-messaging |
| 40 | Group Booking | ✅ | v0.30.0-group-booking |
| 41 | Nearby Attractions | ✅ | v0.31.0-nearby |
| 42 | Recent Searches | ✅ | v0.32.0-recent-searches |
| 43 | Price Alerts | ✅ | v0.33.0-price-alerts |
| 44 | Loyalty Redemption (TEMP catalog) | ✅ | v0.34.0-loyalty-redeem |

### Wave 2 — AI Depth (Phase 45 → 53)

| Phase | Title | Status | Tag |
|-------|-------|--------|-----|
| 45 | AI Location Recommender | ✅ | v0.35.0-ai-location |
| 46 | AI Trip Memory | ✅ | v0.36.0-ai-trip-memory |
| 47 | Predictive Price Locks | ✅ | v0.37.0-price-locks |
| 48 | Smart Waitlist | ✅ | v0.38.0-waitlist |
| 49 | Trust Score per Business | ✅ | v0.39.0-trust-score |
| 50 | AI Budget Optimizer | ✅ | v0.40.0-budget-optimizer |
| 51 | Multi-Business Bundle Deals | ✅ | v0.41.0-bundle-deals |
| 52 | Deep Peer Benchmark | ✅ | v0.42.0-peer-benchmark |
| 53 | Business AI Receptionist | ✅ | v0.43.0-ai-receptionist |

### Wave 3 — Blue-Ocean Innovations (Phase 54 → 65)

| Phase | Title | Status | Tag |
|-------|-------|--------|-----|
| 54 | Instant Refund AI | ✅ | v0.44.0-instant-refund |
| 55 | Family & Kids Mode | ✅ | v0.45.0-family-mode |
| 56 | AI Upsell Engine | ✅ | v0.46.0-upsell-engine |
| 57 | Split Payment / Installments | ✅ | v0.47.0-installments |
| 58 | Multi-property Dashboard | ✅ | v0.48.0-business-groups |
| 59 | AI Group Coordinator | ✅ | v0.49.0-group-coordinator |
| 60 | AI Auto-Repricing Live | ✅ | v0.50.0-auto-repricing |
| 61 | Lessons Learned batch update | ✅ | (lightweight) |
| 62 | Expand /docs/api | ✅ | (lightweight) |
| 63 | UI Consistency Guard | ✅ | (lightweight) |
| 64 | AI Voice Booking | ✅ | v0.51.0-voice-booking |
| 65 | Live Local Experiences (mock) | ✅ | v0.52.0-local-experiences |

**Stage 2 outcome:** Tier 1+2 competitive parity + 15 blue-ocean
features + 15 AI layers. Waves 1–4 fully shipped.

---

## 6. Stage 3 — Production Audit (Phase 66 → 69)

**Goal:** Harden the platform before adding rewards or going to sale.

| Phase | Title | Status | Tag |
|-------|-------|--------|-----|
| 66 | Business Panel Polish | ✅ | v0.53.0-business-polish |
| 67 | Full Bug Sweep (logging, N+1, FK indexes) | ✅ | v0.54.0-bug-sweep |
| 68 | Security Review (rate limits on all routes) | ✅ | v0.55.0-security |
| 69 | Performance Review (N+1, payload caps) | ✅ | v0.56.0-performance |

**Stage 3 is COMPLETE through Phase 69.**

**Note on Phases 70–74:** these numbers were reserved in the
original HANDOFF Section 0.1.5 for production-readiness work
(deploy scripts, PostgreSQL dry-run, prod env config, smoke test,
sales docs). That work was **not shipped under 70–74**. It has
been reorganized and is now tracked as Stage 5, Phases 81–85
(see Section 8). No 70–74 work was lost — it was renumbered for
clarity so that "70" cannot be confused with the numbers of the
actual production phases.

---

## 7. Stage 4 — Rewards Engine (Phase 75 → 80)

**Goal:** Build a differentiated User Rewards & Referral Engine —
server-authoritative, immutable ledger, economic guardrails,
AI-ready.

**Plan source:** "USER REWARDS & REFERRAL ENGINE — Technical
Implementation Specification" (24 sections). Business-owner rewards
are a separate future module (not built here).

| Phase | Title | Status | Tag |
|-------|-------|--------|-----|
| 75 | Rewards Foundation (Ledger + Wallet + Tier migration) | ✅ | v0.57.0-rewards-foundation |
| 76 | Eligibility + Calculation Engine | ✅ | v0.58.0-rewards-eligibility |
| 77 | Referral Engine | ✅ | v0.59.0-referral-engine |
| 78 | Expiration + Reversal | ✅ | v0.60.0-rewards-complete |
| 79 | Redemption + Wallet API | ✅ | v0.60.0-rewards-complete |
| 80 | Campaigns + AI-ready + Analytics | ✅ | v0.60.0-rewards-complete |

**Phase 75 — Rewards Foundation ✅**
- Immutable `Reward` ledger (funding_source, status, expiry,
  transaction_id, referral_id, campaign_id, metadata).
- `RewardWallet` projection (available/locked/expiring/referral/
  experience/bonus balances).
- `RewardRule` per-category config (HOTEL 1.0%, FLIGHT 0.5%,
  EXPERIENCE 1.5%, DINING 1.2%).
- Tier model: EXPLORER / TRAVELER / INSIDER / VIP (1.0x → 2.0x).

**Phase 76 — Eligibility + Calculation Engine ✅**
- `is_qualifying_transaction()` — payment, category, min amount,
  not cancelled, not refunded, not already rewarded.
- Base reward = amount × category_rate; final capped by category
  cap + economic guardrail (≤ 50% of the 6% commission estimate).
- Tier multipliers applied only to eligible bonus components.
- Wired into `payment_service.mark_success` with legacy fallback.

**Phase 77 — Referral Engine ✅**
- Four new tables: `ReferralCode`, `ReferralRelationship`,
  `ReferralEvent`, `ReferralReward`.
- Lifecycle: INVITED → REGISTERED → VERIFIED → QUALIFIED → REWARDED
  → REVERSED / EXPIRED / REVIEW.
- Rewards: referrer AED 20, referred AED 15 (non-cash platform credit).
- Minimum qualifying transaction: AED 300.
- Monthly cap: AED 100 per user.
- Fraud checks: same phone / IP / circular / velocity / cancellations
  / account age → REVIEW (no auto-pay).
- API: GET /referrals/me, POST /referrals/apply,
  POST /referrals/generate, GET /referrals/history/{id}.
- Wired into payment flow (never fails the payment).

**Phase 78 — Expiration + Reversal (NEXT)**
- Expiration windows 30/60/90 days (configurable).
- Automated job: AVAILABLE + expires_at ≤ now → EXPIRED.
- Pre-expiry notifications (7/3/1 days).
- Cancellation/refund → PENDING→CANCELLED, AVAILABLE→REVERSED.
- Spent reward → negative compensating ledger entry (never delete).

**Phase 79 — Redemption + Wallet API**
- Server-authoritative redemption.
- Validation: ownership, expiration, eligibility, cap, duplicate.
- Replace Phase 44 TEMP catalog with a real one (platform_cost +
  funding_source per item).
- Endpoints: wallet, history, available, expiring, redeem, tiers,
  campaigns.

**Phase 80 — Campaigns + AI-ready + Analytics**
- Campaign engine (conditions, budget, usage/user limits,
  economic_cap).
- Economic guardrails (track gross_booking_value,
  platform_commission, reward_cost, referral_cost,
  net_platform_value).
- AI Reward Decision interface (recommendation only — never bypasses
  deterministic limits).
- Analytics: user, financial, campaign metrics.
- Admin config + audit log.


---

## 8. Stage 5 — Production Readiness (Phase 81 → 85)

**Goal:** Make the platform deployable on any VPS by anyone (buyer)
without our involvement. **No purchases required by us — all free
work.**

This stage replaces the older "Phase 70–74" placeholders from
HANDOFF Section 0.1.5.

| Phase | Title | Status |
|-------|-------|--------|
| 83 | Production Env Config (.env.example + systemd + nginx) | ✅ v0.60.1 |
| 81 | Deploy Scripts (install / update / backup / restore) | ✅ v0.60.2 |
| 84 | Smoke Test Suite (critical flows E2E) | ✅ v0.60.3 |
| 85 | Documentation for Buyer (TECH-OVERVIEW + DEPLOY-GUIDE) | ✅ v0.60.3 |
| 82 | PostgreSQL Migration + Dry-run + Edge Cases | ✅ v1.0.0 |

### Phase 81 — Deploy Scripts
- `scripts/deploy/install.sh` — Ubuntu 22.04 one-shot installer.
- `scripts/deploy/update.sh` — pull + migrate + restart.
- `scripts/deploy/backup.sh` — DB + uploads.
- `scripts/deploy/restore.sh` — restore from a backup.
- Idempotent and testable.

### Phase 82 — PostgreSQL Migration
- Real migration run against a **local PostgreSQL** (not SQLite).
- Document every SQLite-specific workaround.
- Deliver `POSTGRES-MIGRATION.md`.

### Phase 83 — Production Env Config
- Complete `.env.example` with comments for every variable.
- Systemd service files (`platform-x.service`, `platform-x-worker.service`).
- Nginx reverse proxy sample.
- Let's Encrypt / Caddy SSL notes.

### Phase 84 — Smoke Test Suite
- One script that exercises every critical flow end-to-end:
  - Guest: register → search → book → pay → review.
  - Business: register → add service → receive booking → reports.
  - Rewards: qualify → ledger entry → wallet.
  - Referral: apply → qualify → award.
- Runnable against a staging instance.

### Phase 85 — Documentation for Buyer
- `TECH-OVERVIEW.md` — architecture, data model, security posture.
- `DEPLOY-GUIDE.md` — 30-minute install walkthrough.
- `OPERATIONS.md` — logs, backups, monitoring, common issues.
- `API.md` — condensed public API reference for the buyer.

---

## 9. Stage 6 — Sales Preparation (Phase 86 → 88)

**Goal:** Package everything so a buyer can evaluate, purchase, and
onboard without friction. **No purchases required by us.**

| Phase | Title | Status |
|-------|-------|--------|
| 86 | Handover Package (CHECKLIST + TRANSFER + BUYER-GUIDE) | ✅ v0.60.4 |
| 87 | Sales Assets (SELLING-PITCH + TECH-DEBT + INVENTORY) | ✅ v0.60.4 |
| 88 | Final Audit + Cleanup (secrets, test data, license) | ✅ v0.60.4 |

> **Order revised 2026-10-04:** Stages 5/6 are sequenced light → heavy. Phase 83 done first; Phase 82 (heaviest) last of Stage 5.

### Phase 86 — Handover Package
- `HANDOVER-CHECKLIST.md` — step-by-step what the seller and buyer do.
- `TRANSFER-GUIDE.md` — how to move the repo, secrets, DB, and
  domain to the buyer's environment.
- `BUYER-GUIDE.md` — first-30-minutes checklist after purchase.

### Phase 87 — Sales Assets
- `SELLING-PITCH.md` — one-page commercial summary.
- `TECH-DEBT-LIST.md` — honest list of what is not finished
  (protects both sides and builds trust).
- `ASSET-INVENTORY.md` — every artifact: repo, tags, docs, tests.
- `ROADMAP-FOR-BUYER.md` — what the buyer can add (upside story).

### Phase 88 — Final Audit + Cleanup
- Remove all secrets from history (rotate anything sensitive).
- Remove demo / test data from shipped DB (fresh seed only).
- Add `LICENSE` (recommended: proprietary or custom).
- Final `pytest tests/ -n auto` — must be 100% green.
- Tag `v1.0.0-sale-ready`.

---

## 10. Stage 7 — Post-Sale Onboarding (Buyer-Driven)

**Goal:** Once a buyer is found, get Platform-X live on their VPS
and their domain. **All purchases and account ownership are the
buyer's.**

**Not phases — execution steps:**

| Step | Action | Owner |
|------|--------|-------|
| 7.1 | Buyer purchases VPS (Ubuntu 22.04, min 2 vCPU / 4 GB RAM) | Buyer |
| 7.2 | Buyer purchases domain and points it at the VPS | Buyer |
| 7.3 | Buyer runs `scripts/deploy/install.sh` | Buyer (or us as a paid service) |
| 7.4 | Buyer configures `.env` (DATABASE_URL, JWT secret, AI keys) | Buyer |
| 7.5 | Buyer sets up SSL (Let's Encrypt or Caddy) | Buyer |
| 7.6 | Buyer sets up the payment provider (Telr / Stripe) — Phase 10 | Buyer |
| 7.7 | Business onboarding tools (Phase 13) — optional add-on | Buyer |
| 7.8 | First real tenant migration (Trianon, Phase 15) — optional | Buyer |

**Our role after sale (optional):** We can offer a paid "activation
service" — install Platform-X on the buyer's VPS within 24–48 hours.
This is an upsell, not part of the sale itself.

---

## 11. Progress Summary

**By the numbers (2026-10-04):**

| Metric | Value |
|--------|-------|
| Phases complete | 0, 0.5, 2–7, 9, 11, 14, 18–23, 25–30, 32–69, 75–77 |
| Phases deferred / skipped | 1 (intentional), 8 (superseded), 24 (deferred) |
| Phases remaining (Stage 4) | none — COMPLETE |
| Phases remaining (Stage 5) | 81, 82, 83, 84, 85 |
| Phases remaining (Stage 6) | 86, 87, 88 |
| Total shipping tags | 59 (v0.2.0 → v0.59.0) |
| Tests passing | **1433** |
| Languages | EN / AR / FIL / HI |
| AI features | 15+ |
| Blue-ocean features | 15 |
| Public API version | v1 |

**Estimated remaining effort (free work only):**
- **ALL STAGES COMPLETE. Zero free work remains.**
- Only Stage 7 (buyer-driven): VPS, domain, payment provider,
  AI provider keys — all on the buyer's accounts.

---

## 12. Handover Notes for Buyer

**What the buyer receives:**
- Full source code (git repository with 59 shipping tags).
- `docs/` — 16+ technical, strategy, and operational documents.
- Test suite (1433 tests) — green.
- Deploy scripts and production config (Stage 5 output).
- Sales and handover documents (Stage 6 output).
- Full commit history with tagged milestones.

**What the buyer must provide:**
- VPS (their own account and billing).
- Domain (their own registration).
- Payment provider account (Telr / Stripe — their own KYC).
- AI provider API keys (their own).

**What is intentionally NOT in the package:**
- Production secrets (buyer generates their own).
- Demo / test data (buyer seeds fresh data).
- Any third-party account or credential owned by the seller.

**Growth path for the buyer:**
- Mobile app (Phase 16) — the API is ready.
- Trianon migration (Phase 15) — first real hospitality customer.
- Business onboarding tools (Phase 13) — self-serve partner signup.
- Real payment provider (Phase 10) — production transactions.
- Business-owner rewards module — separate from user rewards.

**Support the seller can offer (optional, paid):**
- Activation service: 24–48 hour deployment on the buyer's VPS.
- Training session: walkthrough of the business panel + admin panel.
- Customization: white-labeling, new languages, new AI features.

---

*End of Master Roadmap. For state, see `HANDOFF.md`. For strategy,
see `docs/14-ROADMAP-V3-COMPETITIVE.md`. For playbook rules, see
`docs/15-AI-PLAYBOOK.md`.*
