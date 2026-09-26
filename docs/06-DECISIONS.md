# Platform-X — Architectural Decisions

> Record of all significant technical decisions with reasoning.
> Format: ADR (Architecture Decision Record).

---

## ADR-001: Multi-Tenant (not Multi-Instance)

**Date:** September 2026
**Status:** Accepted

**Context:**  
We need to serve many businesses (hotels, restaurants, agencies) with the same core features.

**Decision:**  
Build a multi-tenant platform — one codebase, one database, many businesses.

**Reasoning:**
- Single codebase → single set of updates
- Shared infrastructure → economies of scale
- Easier to add new tenants
- Consistent behavior across tenants

**Alternatives Considered:**
- **Multi-Instance:** Each business gets its own installation. Rejected: maintenance nightmare, no shared features.

**Consequences:**
- Every table needs `tenant_id`
- Every request must be tenant-scoped
- More complex code, but manageable

---

## ADR-002: FastAPI (Backend Framework)

**Date:** September 2026
**Status:** Accepted

**Context:**  
Need a backend framework for the multi-tenant platform.

**Decision:**  
Use FastAPI.

**Reasoning:**
- Modern, fast, type-safe
- Auto-generated API documentation
- Pydantic validation built-in
- Async support (future-proof)
- Great Python ecosystem
- Already proven on Trianon

**Alternatives Considered:**
- **Django:** Too heavy, not async-first
- **Flask:** Not type-safe, no built-in validation
- **Node.js/Express:** Different language, team is Python-focused

**Consequences:**
- All backend code in Python
- Pydantic schemas required
- Alembic for migrations

---

## ADR-003: PostgreSQL (Production Database)

**Date:** September 2026
**Status:** Accepted

**Context:**  
Need a database for multi-tenant production.

**Decision:**  
PostgreSQL for production, SQLite for local dev.

**Reasoning:**
- PostgreSQL: robust, scalable, JSON support, row-level security
- SQLite: zero-config for local dev
- SQLAlchemy ORM supports both
- Easy to test locally, deploy to production

**Alternatives Considered:**
- **SQLite only:** Not scalable for multi-tenant
- **MySQL:** Less feature-rich than PostgreSQL
- **MongoDB:** Not needed, our data is relational

**Consequences:**
- Use SQLAlchemy ORM (database-agnostic)
- Alembic for migrations
- Different connection strings for dev/prod

---

## ADR-004: Shared Schema (not Schema-per-Tenant)

**Date:** September 2026
**Status:** Accepted

**Context:**  
Multi-tenant databases can isolate tenants in three ways.

**Decision:**  
Start with shared database + shared schema (tenant_id on all tables).

**Reasoning:**
- Simplest to implement
- Cheapest to run
- Good for first 100 tenants
- Can migrate to schema-per-tenant or database-per-tenant later

**Alternatives Considered:**
- **Schema-per-tenant:** More isolation, more complex. Deferred.
- **Database-per-tenant:** Maximum isolation, expensive. Deferred.

**Consequences:**
- Every table has `tenant_id`
- Composite indexes (tenant_id, other columns)
- Row-level isolation enforced in code

**Revisit:** When approaching 100 tenants.

---

## ADR-005: Session Tokens (Web) + JWT (API)

**Date:** September 2026
**Status:** Accepted

**Context:**  
Need authentication for web users and mobile/API clients.

**Decision:**  
Use session tokens for web, JWT for mobile and API.

**Reasoning:**
- **Session tokens (web):** Server-side revocation, more secure
- **JWT (mobile/API):** Stateless, efficient, standard for APIs
- Dual approach gives best of both

**Alternatives Considered:**
- **JWT only:** Can't revoke easily
- **Session only:** Doesn't scale for mobile
- **OAuth2:** Overkill for our use case

**Consequences:**
- Two auth systems to maintain
- Shared user database
- Different client libraries for each

---

## ADR-006: Vanilla Frontend (Phase 1) → React (Phase 2+)

**Date:** September 2026
**Status:** Accepted

**Context:**  
Frontend framework decision.

**Decision:**  
Vanilla HTML/CSS/JS for Phase 1, migrate to React (or Next.js) in Phase 2.

**Reasoning:**
- Phase 1 focuses on getting Trianon live fast
- Vanilla is simple, fast to deploy
- Phase 2 adds complex dashboards → need component framework
- Migration path: rewrite frontend, keep API

**Alternatives Considered:**
- **React from start:** Delays Phase 1
- **Next.js from start:** Same issue
- **Vue:** Similar to React, team is more familiar with React

**Consequences:**
- Phase 1 has vanilla JS
- Phase 2 rewrite of frontend
- Backend API stays the same

---

## ADR-007: Multi-Provider Payment Architecture

**Date:** September 2026
**Status:** Accepted

**Context:**  
Payment providers vary by region and feature.

**Decision:**  
Build a payment adapter interface. Start with Telr (UAE), add others as needed.

**Reasoning:**
- Telr: UAE-native, split payment support
- Stripe: global, better docs, limited UAE
- PayTabs: alternative for Middle East
- Adapter pattern → easy to swap/add

**Alternatives Considered:**
- **Single provider:** Risky, limits flexibility
- **Custom payment integration:** Too much compliance burden

**Consequences:**
- Abstract `PaymentProvider` interface
- Concrete implementations: `TelrProvider`, `StripeProvider`, etc.
- Config-driven provider selection per tenant

---

## ADR-008: Domain Strategy — Both Subdomain + Custom

**Date:** September 2026
**Status:** Accepted

**Context:**  
Each tenant needs a domain.

**Decision:**  
Support both subdomain (default) and custom domain (premium).

**Reasoning:**
- Subdomain: fast onboarding, no DNS setup
- Custom domain: premium experience, more trust
- Give tenants choice based on tier
- Both work with same infrastructure

**Alternatives Considered:**
- **Subdomain only:** Limits premium tenants
- **Custom only:** Slows onboarding

**Consequences:**
- Nginx config handles both patterns
- Wildcard SSL for subdomains
- Let's Encrypt per custom domain
- Tenant domain verification process

---

## ADR-009: WhatsApp as Primary Notification Channel

**Date:** September 2026
**Status:** Accepted

**Context:**  
Need to notify guests and staff about bookings, orders, etc.

**Decision:**  
WhatsApp is primary channel. Email is secondary. SMS is fallback.

**Reasoning:**
- WhatsApp dominant in UAE and Gulf region
- Higher engagement than email
- Familiar to staff and guests
- Cheaper than SMS for volume

**Alternatives Considered:**
- **Email only:** Lower engagement
- **SMS only:** Expensive at volume
- **Push notifications:** Requires mobile app (Phase 8)

**Consequences:**
- WhatsApp Business API integration
- Template-based messages
- Fallback to email if WhatsApp fails

---

## ADR-010: English as Base Language (with Arabic RTL)

**Date:** September 2026
**Status:** Accepted

**Context:**  
Platform serves multilingual users.

**Decision:**  
English is base language. Arabic (RTL), Filipino, Hindi supported.

**Reasoning:**
- English: business/tech standard in UAE
- Arabic: local language, RTL support required
- Filipino, Hindi: large expat communities in UAE
- Extensible for future languages

**Alternatives Considered:**
- **Arabic first:** Possible but development harder
- **Multiple equal languages:** Complex content management

**Consequences:**
- All UI strings externalized (i18n)
- RTL layout support
- Language switcher on all pages
- Backend supports locale in notifications

---

## ADR-011: Phone + Email Verification on Registration

**Date:** September 2026
**Status:** Proposed

**Context:**  
Guest registration needs verification to prevent spam/fraud.

**Decision:**  
Require email verification. Phone verification optional (SMS cost).

**Reasoning:**
- Email: free, standard, easy
- Phone: extra cost, but higher trust
- Start with email only, add phone later

**Consequences:**
- Email verification flow
- Rate limiting on registrations
- Phone verification in Phase 3

---

## ADR-012: Microservices vs Monolith

**Date:** September 2026
**Status:** Accepted

**Context:**  
Architectural style for the platform.

**Decision:**  
Start with a modular monolith. Extract microservices only when needed.

**Reasoning:**
- Monolith: simpler to develop, deploy, debug
- Modular structure allows future extraction
- Microservices: premature complexity
- Only split when scaling requires it

**Alternatives Considered:**
- **Microservices from start:** Massive overhead, slower development
- **Traditional monolith:** Harder to extract later

**Consequences:**
- Single FastAPI app initially
- Clear module boundaries in code
- Services can be extracted (payments, notifications, AI) when needed
- Shared database initially

---

## ADR-013: Backup Before Every Change

**Date:** September 2026
**Status:** Accepted

**Context:**  
Development on Termux (mobile) has risks.

**Decision:**  
Before modifying any file → quick file backup.

**Reasoning:**
- Git is good but per-commit
- File-level backups allow instant rollback
- No cost (files are small)
- User's explicit preference

**Consequences:**
- `backups/` folder always maintained
- Backup command documented in PROJECT-RULES.md
- Not tracked in git (too many files)

---

## ADR-014: Excellence Quality Standard (No Compromises)

**Date:** September 2026
**Status:** Accepted

**Context:**  
Project will be public-facing and high-stakes.

**Decision:**  
Every piece of code must meet excellence standards.

**Reasoning:**
- Public-facing → bugs affect real people
- Quality = long-term maintainability
- No technical debt from day one
- User's explicit requirement

**Consequences:**
- No shortcuts
- Tests required (Phase 2+)
- Documentation required
- Code review for significant changes
- Automated checks (lint, format, tests)

---

## ADR-015: First Tenant is Trianon Royal

**Date:** September 2026
**Status:** Accepted

**Context:**  
Platform needs a proof of concept.

**Decision:**  
Trianon Royal Hotel is the first tenant.

**Reasoning:**
- Already in development (`~/trianon-hotel/`)
- Real business with real needs
- Provides real data and feedback
- Proves the model works

**Consequences:**
- Phase 1 = Trianon live
- Phase 3 = Trianon migrates to platform
- Trianon code informs platform architecture
- Trianon becomes case study for other tenants

---

## Decision Log

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| 001 | Multi-Tenant Architecture | Accepted | Sep 2026 |
| 002 | FastAPI Backend | Accepted | Sep 2026 |
| 003 | PostgreSQL Database | Accepted | Sep 2026 |
| 004 | Shared Schema | Accepted | Sep 2026 |
| 005 | Session + JWT Auth | Accepted | Sep 2026 |
| 006 | Vanilla → React | Accepted | Sep 2026 |
| 007 | Multi-Provider Payments | Accepted | Sep 2026 |
| 008 | Subdomain + Custom Domain | Accepted | Sep 2026 |
| 009 | WhatsApp Primary | Accepted | Sep 2026 |
| 010 | English Base + Arabic RTL | Accepted | Sep 2026 |
| 011 | Email Verification | Proposed | Sep 2026 |
| 012 | Modular Monolith | Accepted | Sep 2026 |
| 013 | Backup Before Change | Accepted | Sep 2026 |
| 014 | Excellence Standard | Accepted | Sep 2026 |
| 015 | Trianon First Tenant | Accepted | Sep 2026 |

---

Last updated: September 2026
Status: Living document — new ADRs added as decisions are made.
