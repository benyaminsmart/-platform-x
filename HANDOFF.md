# Platform-X — Project Handoff

> **Purpose:** This file gives a complete overview of Platform-X — what it is, where we are, where we're going.
>
> **Use this file when starting a new chat session.** Combined with PROJECT-NOTES.md, it gives full context.

---

## 1. Project Overview

**Name:** Platform-X (working name — final brand to be decided)
**Type:** Multi-tenant smart platform for hospitality, travel, and tourism
**Purpose:** Allow hotels, restaurants, entertainment centers, and travel agencies to onboard and offer services under one unified platform.
**First Tenant:** Trianon Royal Hotel (Abu Dhabi, UAE)

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

### Tenant Types (B2B)
- Hotels
- Restaurants
- Entertainment centers
- Travel agencies
- Airlines (later)

### End Users (B2C)
- Travelers
- Guests
- Tourists
- Business travelers

---

## 5. Business Model (High-Level)

To be finalized, but direction:
- **Subscription** — tenants pay monthly/yearly for platform access
- **Commission** — platform takes % of each transaction
- **Tiered plans** — basic, professional, enterprise

Full details in `docs/03-BUSINESS-MODEL.md`.

---

## 6. Roadmap (Phases)

### Phase 1 — Trianon Royal Live
- Complete Trianon Royal hotel website
- Payment gateway integration
- Admin panel for hotel staff
- Real content (photos, menus, prices)
- Live on production server
- **Goal:** First real business running on the platform concept

### Phase 2 — Platform-X Core Architecture
- Design multi-tenant architecture (database, auth, domains)
- Build core platform (shared services)
- Testing framework setup
- **Goal:** The platform itself is functional

### Phase 3 — Migrate Trianon to Platform-X
- Move Trianon onto the platform
- Prove the multi-tenant model works with real data
- **Goal:** Trianon becomes "Tenant #1" formally

### Phase 4 — Second Hotel Onboarding
- Onboard a second hotel tenant
- Refine onboarding process
- **Goal:** Prove scalability and repeatability

### Phase 5 — Expand Categories
- Add restaurants
- Add entertainment centers
- Add travel agencies
- **Goal:** Platform serves multiple business types

### Phase 6 — Flights & Packages
- Integrate flight booking
- Add travel packages (hotel + flight + activities)
- **Goal:** Full travel platform

### Phase 7 — AI & Intelligence
- AI concierge for guests
- Smart pricing for tenants
- Predictive analytics
- **Goal:** Platform is smarter than competitors

### Phase 8 — Mobile Apps & Telegram Bot
- Launch iOS and Android apps
- Launch Telegram bot
- **Goal:** Multi-surface presence

---

## 7. Current State

**Phase:** Documentation & architecture design (pre-development)

**Completed:**
- Project folder created
- Git initialized
- .gitignore set up
- PROJECT-RULES.md written
- HANDOFF.md (this file)

**In Progress:**
- Architecture documentation
- Roadmap details

**Not Started:**
- Any production code
- Any backend/frontend

---

## 8. Technology Stack (Preliminary)

**Backend:** Python + FastAPI
**Database:** PostgreSQL (production) / SQLite (dev)
**Frontend:** Vanilla HTML/CSS/JS (Phase 1) → React/Next.js (Phase 2+)
**Auth:** Session tokens (hashed) + JWT (for API)
**Payments:** Multi-provider (Stripe, Telr, etc.)
**Hosting:** VPS (Ubuntu 22.04) + Nginx + systemd
**Monitoring:** To be decided
**CI/CD:** To be decided

Final decisions in `docs/06-DECISIONS.md`.

---

## 9. Success Criteria

The project is considered successful when:

1. **Trianon Royal Hotel** is live and processing real bookings.
2. **Platform-X** supports at least **3 different business types**.
3. **Multi-tenant onboarding** takes < 1 day per new tenant.
4. **Zero critical bugs** in production for 30+ days.
5. **Mobile app** and **Telegram bot** are live.
6. **Code quality** meets excellence standards (no technical debt).

---

## 10. Key Principles

- **Quality over speed.** No shortcuts.
- **Security first.** Every decision considers security.
- **Documentation always.** Every decision documented.
- **Test everything.** No untested code.
- **Backup before change.** Always.
- **One step at a time.** No big-bang changes.

---

## 11. How to Continue This Project

### When starting a new chat:
Send the AI:
1. `PROJECT-RULES.md` — quality standards
2. `HANDOFF.md` (this file) — overview and roadmap
3. `PROJECT-NOTES.md` — technical decisions
4. Current folder structure: `ls -la ~/platform-x/`

Then say:
> "Continue Platform-X. Read the attached files. Environment: Termux on Android. Always respond in Persian. Follow PROJECT-RULES.md strictly."

### Every session:
1. Check current state (`ls -la`, `git log --oneline -5`)
2. Pick next task from roadmap
3. Backup before change
4. Test after change
5. Commit after success
6. Update HANDOFF.md if phase changed

---

## 12. Contact & Authority

**Owner:** Trianon Royal Hotel management
**First Tenant:** Trianon Royal Hotel
**Business Partner:** (to be added)
**Developer:** Platform-X team

---

**Last updated:** September 2026
**Next review:** When Phase 1 begins
