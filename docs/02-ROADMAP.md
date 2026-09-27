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

**Last updated:** September 2026
**Current phase:** Phase 4 — Next (TBD)

