# Platform-X — Work Plan

> Master work plan: what to do, in what order, in which phase.
> This is the source of truth for task sequencing.

---

## Overview

Platform-X development is organized into **phases**. Each phase has:

- Clear goal
- List of deliverables
- Estimated timeline
- Success criteria

**Current phase:** Phase 0.5 — Executive Documents

---

## Phase 0 — Strategic Documents (COMPLETE)

**Goal:** Define what Platform-X is and why.

**Status:** ✅ COMPLETE

**Deliverables:**

- [x] PROJECT-RULES.md — quality standards
- [x] HANDOFF.md — project overview + roadmap
- [x] PROJECT-NOTES.md — technical context
- [x] AI-CONTEXT.md — AI working instructions
- [x] docs/01-ARCHITECTURE.md — architecture
- [x] docs/02-ROADMAP.md — 8-phase roadmap
- [x] docs/03-BUSINESS-MODEL.md — revenue model
- [x] docs/04-FEATURES.md — feature list
- [x] docs/05-TENANT-GUIDE.md — tenant onboarding
- [x] docs/06-DECISIONS.md — 15 ADRs
- [x] generate-handoff.sh — auto state
- [x] get-context.sh — full context generator

---

## Phase 0.5 — Executive Documents (IN PROGRESS)

**Goal:** Define exactly how Platform-X is built — design, data, API, security, infrastructure, testing.

**Status:** 🟡 IN PROGRESS

**Deliverables:**

- [ ] docs/07-DESIGN-SYSTEM.md — visual design + UI/UX
- [ ] docs/08-DATA-MODEL.md — database schema (detailed)
- [ ] docs/09-API-SPEC.md — REST API specification
- [ ] docs/10-SECURITY.md — security architecture (detailed)
- [ ] docs/11-INFRASTRUCTURE.md — servers, CI/CD, monitoring
- [ ] docs/12-TESTING.md — testing strategy

**Success Criteria:**

- All 6 docs written and reviewed
- Every decision in the docs is final (no TBDs)
- Ready to start coding Phase 1 with zero ambiguity

**Order of work:**

1. `docs/07-DESIGN-SYSTEM.md` (first — foundation for UI)
2. `docs/08-DATA-MODEL.md` (schema before backend)
3. `docs/09-API-SPEC.md` (before writing endpoints)
4. `docs/10-SECURITY.md` (before auth code)
5. `docs/11-INFRASTRUCTURE.md` (before deployment)
6. `docs/12-TESTING.md` (before writing tests)

**Each doc:** write → review → commit → backup → next doc.

---

## Phase 1 — First Tenant Live (NEXT)

**Goal:** Get the first tenant (First Tenant) live on a working prototype.

**Status:** ⬜ NOT STARTED

**Deliverables:**

- [ ] Backend project structure (Python + FastAPI)
- [ ] Frontend project structure (HTML/CSS/JS)
- [ ] PostgreSQL database setup (local dev: SQLite)
- [ ] Authentication (register, login, session)
- [ ] User account management
- [ ] Room booking flow
- [ ] Dining ordering flow
- [ ] Spa booking flow
- [ ] Pool reservation flow
- [ ] Room service requests
- [ ] Rewards system (points, tiers)
- [ ] Referral system
- [ ] Payment gateway integration
- [ ] Admin/reception dashboard
- [ ] Multi-language (EN/AR/FIL/HI)
- [ ] VPS deployment
- [ ] Domain + SSL
- [ ] Real content upload
- [ ] Staff training
- [ ] Go-live

**Timeline:** 4-8 weeks (aggressive but realistic)

**Success Criteria:**

- First Tenant accepts real bookings
- Real payments processed
- Staff can manage bookings via dashboard
- Zero critical bugs for 7 consecutive days

---

## Phase 2 — Platform-X Core Architecture

**Goal:** Build multi-tenant foundation.

**Status:** ⬜ NOT STARTED

**Deliverables:**

- [ ] Multi-tenant database schema (tenant_id on all tables)
- [ ] Tenant management system
- [ ] Tenant configuration (branding, services, pricing)
- [ ] Multi-tenant authentication
- [ ] Domain routing (subdomain + custom)
- [ ] API Gateway
- [ ] Shared services (payments, notifications, analytics)
- [ ] Testing framework (pytest, coverage 80%+)
- [ ] CI/CD pipeline
- [ ] Staging environment

**Timeline:** 4-6 weeks

**Success Criteria:**

- New tenant can onboard in < 1 day
- Data isolation verified
- All API endpoints have tests
- Automated deployment works end-to-end

---

## Phase 3 — First Tenant Migration to Platform-X

**Goal:** Move first tenant from standalone to platform.

**Status:** ⬜ NOT STARTED

**Deliverables:**

- [ ] Data migration scripts
- [ ] Frontend adaptation to platform APIs
- [ ] Configure first tenant on platform
- [ ] Parallel running (2 weeks)
- [ ] Cutover
- [ ] Post-migration monitoring

**Timeline:** 2-3 weeks

---

## Phase 4 — Second Hotel Onboarding

**Goal:** Prove repeatability.

**Status:** ⬜ NOT STARTED

**Timeline:** 2-4 weeks

---

## Phase 5 — Multi-Category Expansion

**Goal:** Support restaurants, entertainment, travel agencies.

**Status:** ⬜ NOT STARTED

**Timeline:** 4-6 weeks

---

## Phase 6 — Flights & Packages

**Goal:** Add flight booking + travel packages.

**Status:** ⬜ NOT STARTED

**Timeline:** 6-8 weeks

---

## Phase 7 — AI & Intelligence

**Goal:** Add AI concierge, smart pricing, forecasting.

**Status:** ⬜ NOT STARTED

**Timeline:** 4-6 weeks

---

## Phase 8 — Mobile Apps & Telegram Bot

**Goal:** Multi-surface presence.

**Status:** ⬜ NOT STARTED

**Timeline:** 8-10 weeks

---

## Summary Table

| Phase | Title | Status | Timeline |
|-------|-------|--------|----------|
| 0 | Strategic Documents | ✅ DONE | Complete |
| 0.5 | Executive Documents | 🟡 IN PROGRESS | 1-2 days |
| 1 | First Tenant Live | ⬜ TODO | 4-8 weeks |
| 2 | Platform-X Core | ⬜ TODO | 4-6 weeks |
| 3 | First Tenant Migration | ⬜ TODO | 2-3 weeks |
| 4 | Second Hotel | ⬜ TODO | 2-4 weeks |
| 5 | Multi-Category | ⬜ TODO | 4-6 weeks |
| 6 | Flights & Packages | ⬜ TODO | 6-8 weeks |
| 7 | AI & Intelligence | ⬜ TODO | 4-6 weeks |
| 8 | Mobile & Telegram | ⬜ TODO | 8-10 weeks |

---

## Rules for Phase Execution

1. **No phase starts until previous phase is 100% complete.**
2. **Every phase ends with:** git tag + full backup + HANDOFF update.
3. **Documents must be finalized before coding.** (Phase 0.5 → Phase 1)
4. **No feature from future phases leaks into current phase.**
5. **If a decision changes**, update the relevant doc + ADR (in docs/06-DECISIONS.md).
6. **Every session:** backup → work → test → commit → handoff.

---

## Definition of "Phase Complete"

A phase is complete when:

- All deliverables checked off
- All success criteria met
- Documentation updated
- Backup taken
- Git tagged (e.g., v0.1.0)
- HANDOFF.md updated

---

## Session Workflow (Every Time)

1. `bash get-context.sh` — read current state
2. Pick next task from current phase
3. Backup file before change
4. Make change
5. Test
6. Commit if success
7. `bash generate-handoff.sh` if phase advanced

---

**Last updated:** September 2026
**Next review:** When Phase 0.5 completes
