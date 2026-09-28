# Platform-X — Roadmap

> Full development roadmap across all phases.
> Each phase has clear goals, deliverables, and success criteria.

---

## Overview

| Phase | Title | Status |
|-------|-------|--------|
| 1 | First Tenant Live | In Progress |
| 2 | Platform-X Core Architecture | Not Started |
| 3 | First Tenant Migration | Not Started |
| 4 | Second Hotel Onboarding | Not Started |
| 5 | Expand Categories (Restaurants, Entertainment, Agencies) | Not Started |
| 6 | Flights & Travel Packages | Not Started |
| 7 | AI & Intelligence | Not Started |
| 8 | Mobile Apps & Telegram Bot | Not Started |

---

## Phase 1 — First Tenant Live

**Goal:** Get First Tenant website fully live with real bookings and payments.

**Timeline:** 2-3 weeks

**Deliverables:**

- [ ] Payment gateway integration (Telr or equivalent)
- [ ] Admin/reception dashboard
- [ ] Real content (photos, menus, prices)
- [ ] Complete i18n for all pages (EN/AR/FIL/HI)
- [ ] Visual polish (typography, spacing)
- [ ] VPS deployment (Ubuntu 22.04 + Nginx + PostgreSQL)
- [ ] Domain DNS configuration (trianon.com)
- [ ] SSL certificate (Let's Encrypt)
- [ ] End-to-end testing
- [ ] Staff training
- [ ] Go-live

**Success Criteria:**

- Real guests can book rooms online
- Real payments processed securely
- Hotel staff can manage bookings
- Zero critical bugs for 7 consecutive days

---

## Phase 2 — Platform-X Core Architecture

**Goal:** Design and build the multi-tenant foundation.

**Timeline:** 3-4 weeks

**Deliverables:**

- [ ] Database schema with tenant_id
- [ ] Multi-tenant authentication system
- [ ] Tenant registration & onboarding flow
- [ ] Domain routing (subdomain + custom domain)
- [ ] API Gateway structure
- [ ] Shared services (auth, payments, notifications)
- [ ] Tenant configuration system (branding, services, pricing)
- [ ] Testing framework (pytest, coverage 80%+)
- [ ] CI/CD pipeline
- [ ] Staging environment

**Success Criteria:**

- A new tenant can be onboarded in < 1 day
- Data isolation is verified
- All API endpoints have tests
- Automated deployment works end-to-end

---

## Phase 3 — First Tenant Migration

**Goal:** Move First Tenant onto the multi-tenant platform.

**Timeline:** 2-3 weeks

**Deliverables:**

- [ ] Migrate first tenant data (users, bookings, payments)
- [ ] Adapt first tenant frontend to platform APIs
- [ ] Configure first tenant
- [ ] Redirect trianon.com to platform
- [ ] Verify all features work
- [ ] Run both versions in parallel (2 weeks)
- [ ] Cutover to platform version
- [ ] Post-migration monitoring

**Success Criteria:**

- First tenant runs on Platform-X
- All existing bookings preserved
- Users experience zero downtime
- Performance equal or better than before

---

## Phase 4 — Second Hotel Onboarding

**Goal:** Prove repeatability by onboarding a second hotel tenant.

**Timeline:** 1-2 weeks

**Deliverables:**

- [ ] Recruit second hotel (business development)
- [ ] Onboard through self-service flow
- [ ] Customize branding (logo, colors, domain)
- [ ] Import rooms, pricing, staff
- [ ] Staff training
- [ ] Go-live for second hotel

**Success Criteria:**

- Second hotel live in < 1 week of onboarding
- No platform code changes needed
- Onboarding process documented
- Lessons learned applied

---

## Phase 5 — Expand Categories

**Goal:** Support non-hotel business types.

**Timeline:** 4-6 weeks

**Deliverables:**

- [ ] Restaurant vertical (menus, tables, reservations)
- [ ] Entertainment vertical (events, tickets, venues)
- [ ] Travel agency vertical (packages, itineraries)
- [ ] Vertical-specific configurations
- [ ] Cross-vertical features (reviews, ratings)

**Success Criteria:**

- At least one tenant in each new category live
- Same onboarding flow works for all categories
- Platform handles category-specific logic cleanly

---

## Phase 6 — Flights & Travel Packages

**Goal:** Add flight booking and combined travel packages.

**Timeline:** 6-8 weeks

**Deliverables:**

- [ ] Flight search API integration (Amadeus, Skyscanner, or similar)
- [ ] Flight booking flow
- [ ] Package builder (hotel + flight + activities)
- [ ] Multi-currency support
- [ ] Travel itinerary generation
- [ ] Commission model for flights

**Success Criteria:**

- Users can book flights
- Combined packages work end-to-end
- Commission tracking automated

---

## Phase 7 — AI & Intelligence

**Goal:** Make the platform smarter than competitors.

**Timeline:** 4-6 weeks

**Deliverables:**

- [ ] AI concierge for guests (chat assistant)
- [ ] Smart pricing suggestions for tenants
- [ ] Demand forecasting (occupancy predictions)
- [ ] Review sentiment analysis
- [ ] Personalized recommendations
- [ ] Multi-language AI (Arabic, English, Filipino, Hindi)

**Success Criteria:**

- AI concierge handles 70%+ of guest questions without human
- Smart pricing increases tenant revenue measurably
- AI is available in all supported languages

---

## Phase 8 — Mobile Apps & Telegram Bot

**Goal:** Multi-surface presence.

**Timeline:** 8-10 weeks

**Deliverables:**

**Mobile App:**
- [ ] Framework decision (React Native vs Flutter)
- [ ] iOS app (App Store)
- [ ] Android app (Google Play)
- [ ] Push notifications
- [ ] Offline mode for bookings

**Telegram Bot:**
- [ ] Guest services (order food, request towels)
- [ ] Booking status
- [ ] Rewards balance
- [ ] Notifications
- [ ] Payment via Telegram

**Success Criteria:**

- Apps published on both stores
- Telegram bot handles guest requests
- Cross-platform auth works seamlessly
- User experience consistent across surfaces

---

## Post-Roadmap (Beyond Phase 8)

Future possibilities (not prioritized yet):

- Loyalty program across tenants (multi-brand rewards)
- B2B marketplace for services
- White-label solution for other platforms
- Franchise model
- Data analytics marketplace
- Corporate travel management
- Integration with other OTAs

---

## Cross-Phase Principles

Throughout all phases:

- **Quality:** Excellence standard, no technical debt
- **Testing:** Automated tests on every commit (Phase 2+)
- **Documentation:** Updated every phase
- **Backup:** Every change backed up
- **Security:** Reviewed at every phase transition
- **Performance:** Monitored and optimized continuously

---

## Dependencies & Risks

**External dependencies:**

- Payment provider approval (Phase 1)
- Flight API access (Phase 6)
- AI API access (Phase 7)
- App Store approvals (Phase 8)

**Risks:**

- Multi-tenant complexity (Phase 2)
- Data migration errors (Phase 3)
- Payment provider limitations (Phase 1, 6)
- Scaling challenges (Phase 5+)

**Mitigation:**

- Phased rollout
- Extensive testing
- Parallel running during migrations
- Regular backups


---

## Progress Log

### v0.1.0-core — Phase 2 Complete
- 14 ORM models, 46 API routes, 114 tests
- Alembic migrations
- Production hardening
- Full demo seed (5 tenants, 23 services, 1 admin)
- End-to-end demo flow test

### v0.2.0-frontend — Phase 3 Complete
- Jinja2 + custom CSS Design System (Luxury Dark)
- 12 HTML pages: home, businesses, login, register, about, contact,
  tenant_home, tenant_book, tenant_pay, tenant_account
- 5 JS modules: auth, booking, payment, account
- Cloudflare Tunnel deploy (always-on like Trianon)
- 147 tests
- Live at: https://larger-stable-are-southwest.trycloudflare.com

---



### v0.3.0-polish — Phase 4 Complete
- Light Hospitality theme (cream white + navy + gold accent)
- 4 categories with dedicated pages (hotels, restaurants, travel, entertainment)
- Platform-X Own Design (Plus Jakarta Sans + Inter)
- 21 businesses seeded with Unsplash images
- Home: Hero + Search + Why + Categories + 4 Featured sections + Steps + CTA
- Business detail page: Hero + Info bar + Gallery + Services
- Booking flow: form + live summary sidebar
- Payment: method picker + summary
- Account dashboard: stats + tabs (Bookings/Orders/Rewards/Referrals)
- Auth: split layout with image
- 404 page
- Micro-interactions + responsive + a11y polish
- 154 tests passing
- Live at: https://larger-stable-are-southwest.trycloudflare.com

**Phase 4 closed.**



### v0.4.0-full-flow — Phase 5 Complete
- Platform-wide auth (users book across all tenants)
- Cross-tenant Bookings + Orders in account
- Dynamic booking form per business type (hotel/restaurant/travel/entertainment)
- Restaurant Menu + Order Cart + Order Payment page
- Partner Onboarding Form (/partners/apply) — 6-step dynamic, type-specific
- Rewards auto-award on successful payment
- Account Dashboard: Rewards Panel + Stats + Recent Activity + Tabs + Category browse
- Header: avatar/initials dropdown with logout (outside mobile menu)
- Stats Strip on home with count-up animation
- Phone uniqueness handling (409 instead of 500)
- Payment page shows user details (name/email/phone)
- 154 tests passing
- Live at: https://larger-stable-are-southwest.trycloudflare.com

**Phase 5 closed.**



### v0.5.0-security — Phase 6 Complete
- Rate Limiting (slowapi): login 20/min, register 5/min, partner 3/5min, payment 20/min
- Security Headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- JWT Refresh Tokens (access 30min, refresh 30 days, /auth/refresh)
- Password Policy (min 8 + lower + upper + digit)
- Account Lockout (5 failed attempts → 15 min)
- Session Revocation (/auth/logout revokes, JWT jti unique)
- XSS Audit — all clear (Jinja autoescape + PX.esc everywhere)
- SQL Injection Audit — all clear (SQLAlchemy Core/ORM only)
- HTTPS Enforcement (production only)
- Audit Log Coverage (admin login, tenant status, subscription create)
- SECRETS.md + DEPLOYMENT.md + auto_backup.sh
- 154 tests passing
- Live at: https://goes-nevada-endorsement-labor.trycloudflare.com

**Phase 6 closed.**



### v0.6.0-admin — Phase 7 Complete
- Admin Login page (/admin/login) with separate auth flow
- Admin Dashboard: stats + recent tenants + recent applications + recent audit
- Tenants List: table with status filter
- Tenant Detail: info + status change (activate/suspend/delete)
- Applications Review: table with status filter
- Audit Logs Viewer: paginated table
- Subscriptions Management: list + inline create form
- Admin panel: dark navy theme, dedicated sidebar + topbar
- Admin token stored separately (px_admin_token)
- 154 tests passing
- Live at: https://goes-nevada-endorsement-labor.trycloudflare.com/admin

**Phase 7 closed.**



### v0.7.0-i18n — Phase 9 Complete
- i18n foundation (app/core/i18n.py)
- 4 translation files: en, ar (RTL), fil, hi (186 keys each)
- Language resolution: ?lang → cookie → Accept-Language → default
- Language switcher (🌍 globe) in header
- All public pages translated: Home, Category, Business Detail, Book, Pay, Account, Login, Register, Partners, 404
- JS strings via window.PX_I18N
- RTL layout for Arabic
- 154 tests passing

**Phase 9 closed.**



### v0.8.0-notifications — Phase 11 Complete
- Email service via Resend (EMAIL_ENABLED flag)
- 3 email templates: welcome, booking_confirmed, password_reset
- Password Reset Flow (forgot + reset pages, SHA-256 hashed tokens, 1h expiry)
- Auto-notifications: welcome, booking_confirmed, password_changed
- Notification Center UI: tab in account, unread badge, mark-as-read
- 4-language support for all notification UI
- SMS/WhatsApp deferred (needs Twilio account)
- 154 tests passing
- Live URL: https://statement-lee-med-fraction.trycloudflare.com

**Phase 11 closed.**



### v0.9.0-business — Phase 20 Complete
- Business Owner Panel (separate from Admin Panel)
- Business auth: /business/login (URL-based tenant)
- Business Dashboard: bookings, confirmed, services, revenue
- Services Management: create, list, activate/deactivate
- Bookings Inbox: view all, change status
- Customer List: distinct customers with booking counts
- Analytics (placeholder for AI insights)
- Staff Accounts: owner/manager/staff roles, owner-only management
- Business Notifications: new booking alerts
- Reserved slug: business
- API prefix: /business/api (avoid collision with HTML)
- 154 tests passing
- Live URL: https://always-avoiding-bull-psychiatry.trycloudflare.com

**Phase 20 closed.**



### v0.10.0-ai-foundation — Phase 18 Complete
- Provider abstraction layer (app/services/ai/)
- MockProvider (default, keyword-based smart responses)
- GeminiProvider + OpenAIProvider stubs (ready when API key configured)
- Factory with safe fallback to mock
- Public AI Chat: POST /ai/chat (20/min)
- Business AI Chat: POST /business/api/ai/chat (30/min)
- Health: GET /ai/health
- Floating AI FAB on all pages with chat panel
- Business AI Assistant page (/business/ai)
- Provider-agnostic: change via AI_PROVIDER env var
- 154 tests passing

**Phase 18 closed.**

**Last updated:** September 2026
**Current phase:** TBD (Phase 8 waiting for plan; Phase 10-16 available)

