# Platform-X — Project Handoff

> Complete overview for any AI/dev session. Read this + PROJECT-RULES.md + AI-CONTEXT.md.

Last updated: 2026-09-27

---

## 1. Project Overview

**Name:** Platform-X (working name)
**Type:** Multi-tenant smart platform for hospitality, travel, entertainment
**Purpose:** Hotels, restaurants, entertainment centers, travel agencies — one platform
**Long-term vision:** Modern alternative to Booking.com/Agoda/Expedia, but multi-service

**First real tenant:** Trianon Hotel (already exists as separate site: https://intermediate-aims-insights-metal.trycloudflare.com)

---

## 2. Working Rules (NON-NEGOTIABLE)

1. **Backup before every change** (file-level with timestamp)
2. **One step at a time** — test after each change
3. **Commit after every success**
4. **Handoff after every session**
5. **Test before claiming done**
6. **NEVER add features from yourself** — follow roadmap
7. **NEVER change architecture without explicit user approval**
8. **Do NOT ask the user technical decisions** — decide as Tech Lead
9. **Do NOT skip phases** — finish current phase before next
10. **Quality bar: EXCELLENCE** — no shortcuts, no bugs, production-ready

**Language:** All responses in Persian (Farsi). Direct, no fluff.

---

## 3. Environment

- **Platform:** Termux on Android (mobile phone)
- **Python:** 3.13.13
- **Repo:** ~/platform-x
- **Venv:** ~/platform-x/venv

**Backups location:** ~/platform-x/backups/
**Logs location:** ~/platform-x/logs/

---

## 4. Tech Stack (Locked)

- **Backend:** FastAPI 0.115
- **Database:** SQLite (dev/Termux) → PostgreSQL (production VPS later)
- **ORM:** SQLAlchemy 2.0
- **Migrations:** Alembic
- **Auth:** JWT (python-jose) + bcrypt
- **Templating:** Jinja2
- **Styling:** Custom CSS (Design System, Luxury Dark) + Tailwind CDN
- **Fonts:** Playfair Display (headings), Inter (body), JetBrains Mono (code)
- **Testing:** pytest + httpx TestClient
- **Deploy:** Cloudflare Quick Tunnel (Termux) → Named Tunnel + VPS later

---

## 5. Current Status

### Phase 0 — Strategic Documents: COMPLETE
### Phase 0.5 — Executive Documents: COMPLETE

### Phase 1 — First Tenant Live: SKIPPED
(Decision: build platform core first, tenant migration later)

### Phase 2 — Core Architecture: COMPLETE
Tag: v0.1.0-core
- 14 ORM models: Tenant, User, Session, Booking, Service, Order, Payment,
  Reward, Referral, Notification, AnalyticsEvent, PlatformAdmin, AuditLog, Subscription
- 46 API routes across 11 routers
- JWT auth (users + platform admins, separated)
- Multi-tenant isolation (X-Tenant-Slug header, JWT bound to tenant)
- Payment provider abstraction (mock for dev, Telr later)
- Rewards tiers: welcome→silver→gold→platinum→royal
- Referrals with point awards (100/50)
- Notifications (5 channels)
- Analytics events
- Alembic initial migration (all tables)
- Production hardening (fail-fast config validation)
- Full demo seed: 5 tenants, 23 services, 1 admin

### Phase 3 — Frontend: COMPLETE
Tag: v0.2.0-frontend
- Jinja2 + custom CSS Design System (Luxury Dark: black + gold + cream)
- 12 HTML pages: home, businesses, login, register, about, contact,
  tenant_home, tenant_book, tenant_pay, tenant_account
- 5 JS modules: auth.js, booking.js, payment.js, account.js
- Reserved-slug protection (API routes never shadowed by tenant slugs)
- Deploy: Cloudflare Quick Tunnel (always-on, verified with Termux closed)
- URL: https://larger-stable-are-southwest.trycloudflare.com
- 147 tests passing

### Phase 4 — UI Polish + i18n + Content: NEXT
Planned 23 steps (see section 9)

---

## 6. Live URLs

**Platform-X (dev demo):**
https://larger-stable-are-southwest.trycloudflare.com

**Trianon (existing, separate):**
https://intermediate-aims-insights-metal.trycloudflare.com

**Tunnel type:** Cloudflare Quick Tunnel (URL changes on cloudflared restart)
**Tunnel URL saved at:** ~/platform-x/logs/tunnel.url

---

## 7. Runit Services (Termux)

Location: /data/data/com.termux/files/usr/var/service/

| Service | Purpose | Port |
|---|---|---|
| trianon | Trianon frontend (http.server) | 8000 |
| trianon-backend | Trianon FastAPI | 8001 |
| wordsmart-tunnel | Word Smart project tunnel | 8020 |
| platform-x-api | Platform-X FastAPI | 8030 |
| platform-x-tunnel | Platform-X Cloudflare tunnel | — |

**Boot script:** ~/.termux/boot/start-services.sh (requires Termux:Boot app)
**Wake lock:** Enabled (keeps services alive when Termux closed)

**Management commands:**
- `sv status platform-x-api platform-x-tunnel`
- `sv up platform-x-api`
- `sv down platform-x-api`
- `sv restart platform-x-api`

---

## 8. Demo Data (Seeded)

**5 Tenants:**
- trianon-hotel (Trianon Hotel) — 5 rooms
- saffron-restaurant (Saffron Restaurant) — 6 dishes
- skyways-travel (Skyways Travel) — 4 packages
- oasis-entertainment (Oasis Entertainment) — 4 tickets
- desert-tours (Desert Tours) — 4 tours

**Platform Admin:**
- Email: admin@platform-x.local
- Password: ChangeMe123! (CHANGE BEFORE PUBLIC DEMO)

**Seed commands:**
- `python -m app.scripts.seed_all` (all)
- `python -m app.scripts.seed_tenants` (tenants only)
- `python -m app.scripts.seed_services` (services only)
- `python -m app.scripts.seed_admin` (admin only)

All idempotent.

---

## 9. Phase 4 Plan — 23 Steps

1. Design System Polish (typography, spacing, components)
2. Tenant Branding Config (per-tenant colors/fonts/logo)
3. Home Landing Redesign
4. Businesses Directory Redesign
5. Tenant Home by Type (hotel / restaurant / tour / ticket)
6. Booking Flow Polish (multi-step, date picker, live price)
7. Payment Flow Polish (method select, confirm, invoice)
8. Account Dashboard Polish (tabs, history, loyalty card)
9. i18n Foundation (EN/AR/FIL/HI + RTL)
10. i18n Content — English
11. i18n Content — Arabic (+ RTL)
12. i18n Content — Filipino
13. i18n Content — Hindi
14. Images & Assets
15. Responsive Polish (mobile/tablet/desktop)
16. Micro-interactions (animations, transitions, loading)
17. Admin Panel UI (platform admin frontend)
18. Named Tunnel Setup (custom domain + Cloudflare Named Tunnel)
19. SEO + Meta (OpenGraph, Twitter Card, sitemap)
20. Performance (cache, compression, lazy loading)
21. Security Frontend (CSP, rate limit, XSS)
22. E2E Playwright Tests
23. Milestone Close (v0.3.0-polish)

---

## 10. Key Decisions Made

1. **Multi-tenant via X-Tenant-Slug header** (not subdomain yet)
2. **SQLite for dev, PostgreSQL for production** (DATABASE_URL switch)
3. **JWT carries tenant_id** — token bound to tenant, cross-tenant use → 401
4. **Routes never touch DB directly** — always via services/
5. **Users and Platform Admins are separate auth flows** (different JWT claims)
6. **Payment provider abstraction** — Mock now, real later
7. **Frontend: Jinja2 + Tailwind CDN** (no build step, no separate server)
8. **Design: Luxury Dark** (from 07-DESIGN-SYSTEM.md) — black + gold + cream
9. **Trianon stays independent** — will be migrated into platform later
10. **Phase 1 skipped** — core first, then migration
11. **Phase 3 extended** — split into Frontend (done) + Polish (Phase 4)
12. **No framework build step** — Termux constraints, no npm

---

## 11. Files Reference

- **PROJECT-RULES.md** — Quality bar (EXCELLENCE)
- **AI-CONTEXT.md** — AI-specific context
- **PROJECT-NOTES.md** — Notes
- **docs/00-WORK-PLAN.md** through **docs/12-TESTING.md** — All project docs
- **docs/02-ROADMAP.md** — Roadmap + Progress Log
- **docs/07-DESIGN-SYSTEM.md** — Colors, fonts, spacing, components
- **docs/08-DATA-MODEL.md** — All tables
- **docs/09-API-SPEC.md** — All endpoints
- **README.md** — Setup + run instructions

---

## 12. How to Start a New Session

1. Read this HANDOFF.md fully
2. Read PROJECT-RULES.md
3. Read docs/02-ROADMAP.md (Progress Log at bottom)
4. Check current state:
