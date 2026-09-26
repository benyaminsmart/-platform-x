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


## 11. Documentation Map

All project docs are in docs/:

- docs/01-ARCHITECTURE.md — Technical architecture (multi-tenant design)
- docs/02-ROADMAP.md — Full 8-phase roadmap with deliverables
- docs/03-BUSINESS-MODEL.md — Revenue model, pricing, unit economics
- docs/04-FEATURES.md — Complete feature list by user type and phase
- docs/05-TENANT-GUIDE.md — Onboarding guide for businesses joining
- docs/06-DECISIONS.md — 15 ADRs (Architectural Decision Records)

Root-level files:

- PROJECT-RULES.md — Quality standards and working rules
- HANDOFF.md — This file — project overview + roadmap
- PROJECT-NOTES.md — Technical context and reasoning
- generate-handoff.sh — Auto-generates HANDOFF-STATE.txt

---

## 12. How to Continue This Project (New Chat)

### Step 1 — Send context
Send the new AI three files (concatenated):

cd ~/platform-x && cat HANDOFF.md PROJECT-RULES.md PROJECT-NOTES.md

Copy the output and send to the new chat.

### Step 2 — Send current state

cd ~/platform-x && bash generate-handoff.sh && cat HANDOFF-STATE.txt

Copy this too.

### Step 3 — Send docs (optional)
If the AI needs architectural details:

cd ~/platform-x && cat docs/01-ARCHITECTURE.md
cd ~/platform-x && cat docs/02-ROADMAP.md

And so on for 03, 04, 05, 06.

### Step 4 — Opening message for the AI

I am continuing Platform-X (multi-tenant hospitality/travel platform).
Read the attached context files. Environment: Termux on Android.
Always respond in Persian. Follow PROJECT-RULES.md strictly.
Backup before every change. Test after every change.
Commit after every success.
Continue from where we left off. See HANDOFF-STATE.txt for current state.

### Every session:
1. Check state (ls -la, git log --oneline -5)
2. Pick next task from roadmap
3. Backup before change (per file)
4. Test after change
5. Commit after success
6. Update HANDOFF.md if phase changed
7. Update docs if decisions changed

---

## 13. Contact & Authority

Owner: Trianon Royal Hotel management
First Tenant: Trianon Royal Hotel
Business Partner: (to be added)
Lead Developer: Platform-X team

---

Last updated: September 2026
Next review: When Phase 1 development begins
