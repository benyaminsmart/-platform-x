# Platform-X — Project Handoff

> Complete overview of Platform-X — what it is, where we are, where we're going.
>
> Combined with PROJECT-NOTES.md and AI-CONTEXT.md, this gives full context for any new chat session.

---

## 1. Project Overview

**Name:** Platform-X (working name — final brand to be decided)
**Type:** Multi-tenant smart platform for hospitality, travel, and tourism
**Purpose:** Allow hotels, restaurants, entertainment centers, and travel agencies to onboard and offer services under one unified platform.

**Long-term vision:**
A modern, intelligent alternative to Booking.com, Agoda, and Expedia — but multi-service (hotels + restaurants + entertainment + travel agencies + flights).

---

## 2. Core Concept

**One platform. Many businesses. One seamless experience.**

Each business (tenant) gets:
- Its own domain and brand
- Its own dashboard
- Its own services and pricing
- Its own customer base

The platform provides (shared):
- Authentication
- Payment infrastructure
- Booking engine
- Notifications
- Analytics
- AI features

---

## 3. Platforms & Surfaces

Platform-X will be available across:

1. **Web Platform** (primary)
2. **REST API** (for integrations & mobile apps)
3. **Mobile Application** (iOS + Android)
4. **Telegram Bot** (guest services, notifications, quick actions)

All surfaces are first-class citizens, not afterthoughts.

---

## 4. Target Market

**Tenant Types (B2B):**
- Hotels
- Restaurants
- Entertainment centers
- Travel agencies
- Airlines (later)

**End Users (B2C):**
- Travelers
- Guests
- Tourists
- Business travelers

---

## 5. Business Model (High-Level)

- **Subscription** — tenants pay monthly/yearly for platform access
- **Commission** — platform takes % of each transaction
- **Tiered plans** — basic, professional, enterprise

Full details: docs/03-BUSINESS-MODEL.md

---

## 6. Roadmap (Summary)

| Phase | Title | Status |
|-------|-------|--------|
| 0 | Strategic Documents | ✅ COMPLETE |
| 0.5 | Executive Documents | 🟡 IN PROGRESS |
| 1 | Platform Core Development | ⬜ TODO |
| 2 | Multi-Tenant Architecture | ⬜ TODO |
| 3 | First Tenant Integration | ⬜ TODO |
| 4 | Second Tenant Onboarding | ⬜ TODO |
| 5 | Multi-Category Expansion | ⬜ TODO |
| 6 | Flights & Packages | ⬜ TODO |
| 7 | AI & Intelligence | ⬜ TODO |
| 8 | Mobile Apps & Telegram Bot | ⬜ TODO |

Full details: docs/02-ROADMAP.md

---

## 7. Current State

**Phase:** Phase 0.5 — Executive Documents

**Completed (Phase 0):**
- Project structure, git initialized
- .gitignore
- PROJECT-RULES.md
- HANDOFF.md (this file)
- PROJECT-NOTES.md
- AI-CONTEXT.md
- generate-handoff.sh, get-context.sh
- docs/00-WORK-PLAN.md
- docs/01-ARCHITECTURE.md
- docs/02-ROADMAP.md
- docs/03-BUSINESS-MODEL.md
- docs/04-FEATURES.md
- docs/05-TENANT-GUIDE.md
- docs/06-DECISIONS.md

**In Progress (Phase 0.5):**
- docs/07-DESIGN-SYSTEM.md
- docs/08-DATA-MODEL.md
- docs/09-API-SPEC.md
- docs/10-SECURITY.md
- docs/11-INFRASTRUCTURE.md
- docs/12-TESTING.md

**Not Started:**
- All code (backend, frontend)
- Database
- Any deployment

---

## 8. Technology Stack

**Backend:** Python + FastAPI
**Database:** PostgreSQL (production) / SQLite (dev)
**Frontend:** Vanilla HTML/CSS/JS (Phase 1) → React/Next.js (Phase 2+)
**Auth:** Session tokens (web) + JWT (API)
**Payments:** Multi-provider (Telr, Stripe, PayTabs)
**Hosting:** VPS + Nginx + systemd
**CI/CD:** To be decided (Phase 2)
**Monitoring:** To be decided (Phase 2)

Final decisions: docs/06-DECISIONS.md

---

## 9. Success Criteria

Platform-X is successful when:

1. At least **3 different business types** are onboarded
2. Multi-tenant onboarding takes < 1 day per new tenant
3. Zero critical bugs in production for 30+ days
4. Mobile app and Telegram bot are live
5. Code quality meets excellence standards
6. Platform handles **100+ tenants** without architecture changes

---

## 10. Documentation Map

Root files:

- PROJECT-RULES.md — Quality standards and working rules
- HANDOFF.md — This file (project overview + roadmap)
- PROJECT-NOTES.md — Technical context and reasoning
- AI-CONTEXT.md — AI working instructions
- generate-handoff.sh — Auto-generates HANDOFF-STATE.txt
- get-context.sh — Generates CONTEXT-FULL.txt

docs/ folder:

- 00-WORK-PLAN.md — Master work plan + phase sequencing
- 01-ARCHITECTURE.md — Technical architecture (multi-tenant)
- 02-ROADMAP.md — Full 8-phase roadmap
- 03-BUSINESS-MODEL.md — Revenue model and pricing
- 04-FEATURES.md — Complete feature list
- 05-TENANT-GUIDE.md — Tenant onboarding guide
- 06-DECISIONS.md — 15 ADRs
- 07-DESIGN-SYSTEM.md — Design system (in progress)
- 08-DATA-MODEL.md — Database schema (in progress)
- 09-API-SPEC.md — REST API specification (in progress)
- 10-SECURITY.md — Security architecture (in progress)
- 11-INFRASTRUCTURE.md — Servers, CI/CD, monitoring (in progress)
- 12-TESTING.md — Testing strategy (in progress)

---

## 11. How to Continue (New Chat)

### Step 1 — Generate full context

cd ~/platform-x && bash get-context.sh && cat CONTEXT-FULL.txt

### Step 2 — Send output to new AI

Copy the output and send.

### Step 3 — Opening message

I am continuing Platform-X. Read the attached files.
Environment: Termux. Respond in Persian.
Follow PROJECT-RULES.md. Backup, test, commit, handoff.
Continue from where we left off.

---

## 12. Key Principles

- Quality over speed. No shortcuts.
- Security first. Every decision considers security.
- Documentation always.
- Test everything.
- Backup before change.
- One step at a time.
- No features from thin air. Follow the roadmap.

---

## 13. Contact & Authority

Project: Platform-X
Working Name: Platform-X (final brand pending)
Lead Developer: Platform-X team

---

Last updated: September 2026
Next review: When Phase 0.5 completes
