# Platform-X — Project Handoff

> Complete overview for any new AI/dev session. Read this + PROJECT-RULES.md + AI-CONTEXT.md.
> Version: v0.7.0-i18n (Phases 0-7, 9 complete)

Last updated: 2026-09-27

---

## 1. Project Overview

**Name:** Platform-X (working name)
**Type:** Multi-tenant smart platform for hospitality, travel, entertainment
**Purpose:** Hotels, restaurants, entertainment centers, travel agencies — one platform
**Long-term vision:** Modern alternative to Booking.com/Agoda/Expedia, multi-service

**First real tenant (future):** Trianon Royal Hotel
**Trianon existing site:** https://intermediate-aims-insights-metal.trycloudflare.com

---

## 2. Working Rules (NON-NEGOTIABLE)

1. Backup before every change (file-level with timestamp)
2. One step at a time — test after each change
3. Commit after every success
4. Handoff after every session
5. Test before claiming done
6. NEVER add features from yourself — follow roadmap
7. NEVER change architecture without explicit user approval
8. Do NOT ask the user technical decisions — decide as Tech Lead
9. Do NOT skip phases — finish current phase before next
10. Quality bar: EXCELLENCE — no shortcuts, no bugs, production-ready

**Language:** All responses in Persian (Farsi). Direct, no fluff.

---

## 3. Environment

- Platform: Termux on Android (mobile phone)
- Python: 3.13.13
- Repo: ~/platform-x
- Venv: ~/platform-x/venv

Backups: ~/platform-x/backups/
Logs: ~/platform-x/logs/

---

## 4. Tech Stack (Locked)

- Backend: FastAPI 0.115
- Database: SQLite (dev/Termux) → PostgreSQL (production VPS later)
- ORM: SQLAlchemy 2.0
- Migrations: Alembic
- Auth: JWT (python-jose) + bcrypt
- Templating: Jinja2
- Styling: Custom CSS (Light Hospitality theme) + Design System
- Fonts: Plus Jakarta Sans (display), Inter (body), JetBrains Mono (code)
- Testing: pytest + httpx TestClient
- Deploy: Cloudflare Quick Tunnel (Termux) → Named Tunnel + VPS later

---

## 5. Phases Status

### Phase 0 — Strategic Documents: COMPLETE
### Phase 0.5 — Executive Documents: COMPLETE

### Phase 1 — First Tenant Live: SKIPPED (intentional)
Reason: Build platform core first, migrate real tenants later.

### Phase 2 — Core Architecture: COMPLETE
Tag: v0.1.0-core
- 16 ORM models (see section 6)
- ~65 API routes
- JWT auth (users + platform admins, separated)
- Payment provider abstraction (mock for dev)
- Rewards tiers: welcome→silver→gold→platinum→royal
- Referrals with point awards (100/50)
- Notifications (5 channels)
- Analytics events
- Alembic migrations
- Production hardening (fail-fast config)
- Full demo seed

### Phase 3 — Frontend: COMPLETE
Tag: v0.2.0-frontend
- Jinja2 + custom CSS
- Design System v1 (dark luxury, later replaced)
- All pages: home, businesses, login, register, about, contact,
  tenant_home, tenant_book, tenant_pay, tenant_account
- Cloudflare Tunnel #2 online
- Always-on (wakelock + Termux:Boot)

### Phase 4 — UI Redesign + Rich Demo: COMPLETE
Tag: v0.3.0-polish
- **NEW: Light Hospitality theme** (cream white + navy #0f3d5c + gold accent #c9a961)
- **NEW: 4 Category colors** (hotels blue, restaurants red, travel green, entertainment purple)
- **NEW: platform.css** (light theme tokens + components)
- **NEW: platform-home.css** (all home/category/detail styles, 1500+ lines)
- **NEW: Plus Jakarta Sans** display font
- **NEW: 21 businesses seeded** with Unsplash images (5 hotels, 5 restaurants, 6 agencies, 5 entertainment)
- **NEW: Home** (Hero + Stats Strip + Categories + 4 Featured sections + Steps + CTA)
- **NEW: Business Detail** (Hero + Info bar + Gallery + Services)
- **NEW: Split Auth layout**
- **NEW: Account Dashboard** (Category browser + Rewards Panel + Stats + Recent Activity + Tabs)
- **NEW: 404 page**
- **NEW: Micro-interactions**

### Phase 5 — Full Feature Verification + Partner Onboarding: COMPLETE
Tag: v0.4.0-full-flow
- Platform-wide auth: users book across ALL tenants (major architecture change)
- Cross-tenant Bookings/Orders in account
- Rewards auto-award on payment
- Dynamic booking form per business type (hotel/restaurant/travel/entertainment)
- Payment page shows user details (name/email/phone)
- Phone uniqueness handling (409, not 500)
- Entertainment time slot added
- Account: category browser removed New Booking (misleading)
- Partner onboarding form (/partners/apply)
  - 6-step dynamic form (type → contact → business → specifics → plan → about)
  - Type-specific fields for each business type
  - Backend: PartnerApplication model + POST /partners/apply + admin list endpoint
- Header restructure: avatar outside mobile menu
- Stats strip on home (businesses, services, categories, locations) with count-up animation

---

## 6. Data Models (16 tables)

Global:
- tenants (slug, name, tier, status, config JSON with branding/images/rating)
- platform_admins (email, role, mfa fields)
- audit_logs (actor, action, target, changes)
- subscriptions (tenant plan, billing)

Per-tenant (all have tenant_id):
- users (email, phone, password_hash, points, tier, referral_code, home_tenant_id via tenant_id)
- sessions (auth tokens)
- bookings (booking_type, service_id, check_in, check_out, guests, amount, status)
- services (type, name, price, image_urls, attributes)
- orders (service_type, quantity, amount, status)
- payments (booking_id OR order_id, provider, provider_reference, status)
- rewards (reward_type: earn/redeem/adjust, points)
- referrals (referrer_user_id, referred_user_id, reward_points)
- notifications (channel, template, content, status)
- analytics_events (event_type, metadata)

New in Phase 5:
- partner_applications (tenant_type, contact info, business info, tier_interest, languages, details JSON, status)

---

## 7. Key Architecture Decisions

### Platform-wide Users (Phase 5, CRITICAL)
- Users register on a "home tenant" but can book across ALL tenants
- JWT carries user_id + home tenant_id (reference only)
- Active tenant always from X-Tenant-Slug header
- get_current_user does NOT enforce tenant match
- Bookings/Orders/Payments use X-Tenant-Slug for the target tenant
- Account dashboard uses ?all=true to fetch across all tenants

### Multi-Tenancy
- Every tenant-scoped API needs X-Tenant-Slug header
- Fallback to DEFAULT_TENANT_SLUG for dev convenience
- Frontend: tenant slug from URL path (/{slug}/...) or default fallback

### Routes
- HTML routes at /login, /register, /hotels, /restaurants, /travel, /entertainment, /account, /partners/apply, /partners/thanks
- Tenant-scoped HTML: /{slug}/, /{slug}/book, /{slug}/pay, /{slug}/account
- API under /auth, /bookings, /orders, /payments, /rewards, /referrals, /notifications, /analytics, /platform, /partners
- Catch-all 404 last (after API, after reserved, after tenant)
- TrailingSlashRedirectMiddleware: /login/ → /login (for reserved slugs)

### Auth
- Users: POST /auth/register, POST /auth/login, GET /auth/me
- JWT contains sub (user_id), tenant_id (home), iat, exp
- Platform admins: POST /platform/auth/login, GET /platform/me
- JWT contains sub, actor=platform_admin, role

### Payment
- MockPaymentProvider for dev
- POST /payments/intent → returns redirect_url
- GET /payments/mock/confirm/{ref} → confirms (disabled in production via ENABLE_MOCK_PAYMENTS=false)
- POST /payments/webhook/{provider} → real provider callbacks
- On successful payment: booking.status confirmed, payment_status paid, reward points awarded (1pt per 10 units, min 5)

### Rewards
- Tiers: welcome (0), silver (500), gold (2000), platinum (5000), royal (15000)
- Auto-award on booking/order payment
- GET /rewards/me → summary with progress
- GET /rewards/history → paginated
- POST /rewards/redeem → redeem earn reward

### Referrals
- Each user has referral_code
- POST /referrals/apply → link user to referrer (once)
- Awards 100 pts (referrer) + 50 pts (referred)
- GET /referrals/me → code + list

---

## 8. Live URLs

Platform-X (dev demo):
https://larger-stable-are-southwest.trycloudflare.com

Trianon (existing, separate):
https://intermediate-aims-insights-metal.trycloudflare.com

Tunnel type: Cloudflare Quick Tunnel (URL may change on cloudflared restart)
Tunnel URL saved at: ~/platform-x/logs/tunnel.url

Get current URL: cat ~/platform-x/logs/tunnel.url

---

## 9. Runit Services (Termux)

Location: /data/data/com.termux/files/usr/var/service/

| Service | Purpose | Port |
|---|---|---|
| trianon | Trianon frontend (http.server) | 8000 |
| trianon-backend | Trianon FastAPI | 8001 |
| wordsmart-tunnel | Word Smart project tunnel | 8020 |
| platform-x-api | Platform-X FastAPI | 8030 |
| platform-x-tunnel | Platform-X Cloudflare tunnel | — |

Boot script: ~/.termux/boot/start-services.sh (requires Termux:Boot app)
Wake lock: Enabled (keeps services alive when Termux closed)

Management:
  sv status platform-x-api platform-x-tunnel
  sv up platform-x-api
  sv down platform-x-api
  sv restart platform-x-api

---

## 10. Demo Data

5 hotels:
- trianon-hotel (Trianon Royal Hotel) — 4.8★, Downtown Dubai
- azure-palm-resort (Azure Palm Resort) — 4.9★, Palm Jumeirah
- aurora-boutique (Aurora Boutique Hotel) — 4.7★, Alserkal
- marina-skylines (Marina Skylines Hotel) — 4.6★, Dubai Marina
- desert-rose-hotel (Desert Rose Hotel) — 4.5★, Al Fahidi

5 restaurants:
- saffron-restaurant (Modern Middle Eastern)
- olive-grove (Mediterranean)
- sakura-sushi (Japanese)
- the-copper-kitchen (European)
- spice-route-indian (Indian)

6 travel agencies:
- skyways-travel, horizon-voyages, caravan-tours, euro-explorer, blue-ocean-cruises, desert-tours

5 entertainment:
- oasis-entertainment (Family park), skypark-adventures (Ziplines),
- aqua-world (Waterpark), virtual-realm (VR), cinema-royale (Cinema)

Services: 127 across all tenants (auto-generated via seed_services_auto.py)

Platform Admin:
- Email: admin@platform-x.local
- Password: ChangeMe123! (CHANGE BEFORE PUBLIC DEMO)

Seed commands:
  python -m app.scripts.seed_all
  python -m app.scripts.seed_tenants
  python -m app.scripts.seed_services_auto
  python -m app.scripts.seed_admin

All idempotent.

---

## 11. Remaining Work

**Phase 7 — Admin Panel UI (NEXT)**
- Admin Login page
- Admin Dashboard (analytics)
- Tenants list/detail + status change
- Applications review
- Subscriptions management
- Audit Logs viewer
- 2FA for Platform Admin
- Milestone Close (v0.6.0-admin)

## 12. Future Phases (v2 Roadmap)

### Phase 6 — Security Hardening: COMPLETE (v0.5.0-security)
- Rate Limiting (login, register, partners, APIs)
- Security Headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options)
- JWT Refresh Tokens (access + refresh pattern)
- Password Policy + account lockout after 5 fails
- Session Revocation (real logout)
- CSRF Protection (HTML forms)
- XSS Sanitization audit
- SQL Injection audit
- HTTPS Enforcement (redirect HTTP → HTTPS)
- CORS Production (real domains only)
- 2FA for Platform Admin (model exists, UI needed)
- Audit Log coverage
- Secrets Management
- Backup Strategy (daily + off-site)
Estimate: 10-12 steps

### Phase 7 — Admin Panel UI: COMPLETE
Tag: v0.6.0-admin

### Phase 9 — i18n (4 languages): COMPLETE
Tag: v0.7.0-i18n
- EN, AR (RTL), FIL, HI — 186 keys each
- Language switcher (🌍 globe) in header
- All public pages + JS strings translated
- 154 tests passing

### Phase 8 — Rewards + Referral: WAITING (user plan pending)
### Phase 10 — Payment Production (Telr): AVAILABLE
### Phase 11 — Notifications: AVAILABLE
### Phase 12 — VPS Deploy + Domain + Named Tunnel: AVAILABLE
### Phase 13 — Business Onboarding Tools: AVAILABLE
### Phase 14 — API + Webhooks + SDK: AVAILABLE
### Phase 15 — Trianon Migration: AVAILABLE
### Phase 16 — Mobile App: AVAILABLE
### Phase 17 — AI Assistant: AVAILABLE
- Platform Admin Login
- Dashboard (analytics overview)
- Tenants list/detail, approve/suspend
- Applications review (partner applications)
- Subscriptions management
- Audit logs viewer
- Analytics dashboard (charts)
- User management (impersonate, reset, ban)
Estimate: 8-10 steps

### Phase 8 — Rewards + Referral Complete
- Redeem catalog (rewards shop)
- Rewards dashboard (tier progress, milestones)
- Referral dashboard (referred users, total earned)
- Referral milestones (bonus at 5, 10, 25 referrals)
- Special offers / promo codes
- Birthday rewards
- Tier benefits (real perks)
Estimate: 6-10 steps

### Phase 9 — i18n (EN / AR / FIL / HI)
- i18n foundation
- English complete
- Arabic + RTL layout
- Filipino
- Hindi
- Language switcher in header
- Currency switcher
- Locale-aware dates and numbers
Estimate: 5-8 steps

### Phase 10 — Payment Production (Telr)
- Telr provider (replace Mock)
- Webhook signature verification
- Refund flow (API + UI)
- Payment reconciliation (daily job)
- PCI compliance check
- Multi-currency
- Invoice / receipt PDF
- Failed payment retry
Estimate: 6-8 steps

### Phase 11 — Notifications (Real Providers)
- Email provider (SendGrid / Mailgun)
- SMS provider (Twilio / Unifonic)
- WhatsApp Business API
- Templates per notification type
- User notification preferences
- Digest emails
- Notification center UI
Estimate: 5-6 steps

### Phase 12 — VPS Deploy + Domain + Named Tunnel
- VPS provisioning (Ubuntu 22.04)
- Nginx reverse proxy
- Gunicorn/Uvicorn workers
- PostgreSQL migration (from SQLite)
- SSL certificate (Let's Encrypt / Certbot)
- Custom domain + Cloudflare DNS
- Named Cloudflare Tunnel (replaces Quick Tunnel)
- Subdomain per tenant (slug.platform-x.com)
- Custom domain support per tenant
- Monitoring (uptime + error tracking)
- Log aggregation
- Backup automation (cron + off-site)
- Deployment script / CI-CD
- Health checks
- Environment separation (dev/staging/prod)
- Graceful restart (zero-downtime)
Estimate: 8-10 steps

### Phase 13 — Business Onboarding Tools
- Subdomain routing per tenant
- Custom domain support
- SSL for custom domains (wildcard)
- DNS configuration guide
- Tenant self-service setup wizard
- Data import tools (from legacy systems)
- Tenant analytics dashboard
- Tenant staff accounts (Owner / Manager / Staff)
- Tenant billing (Platform-X → business)
- Subscriptions enforcement
Estimate: 10-15 steps

### Phase 14 — API + Webhooks + SDK
- Public API keys for businesses
- Webhooks outbound (Platform-X → business systems)
- API rate limiting per tenant
- API documentation (OpenAPI + examples)
- SDKs (Python, JavaScript)
- Flight API integration (Amadeus / Sabre)
- Google Maps integration
- Email service
- SMS service
- WhatsApp Business API
- Push notifications (future mobile)
Estimate: 6-8 steps

### Phase 15 — Trianon Migration
- Move real Trianon hotel onto Platform-X
- Import existing bookings, users, payments
- Adapt Trianon frontend to platform APIs
- Configure Trianon tenant
- Redirect trianon.com to platform
- Parallel run (2 weeks)
- Cutover
Estimate: 5-8 steps

### Phase 16 — Mobile App
- Framework decision (React Native vs Flutter)
- Shared API layer
- Customer app (iOS + Android)
- Business staff app
- Push notifications
- App Store + Play Store
Estimate: weeks/months


### Phase 17 — AI Assistant
- Floating chat button (FAB) on public site
- Chat panel UI (sidebar/modal with messages)
- Backend: POST /ai/chat endpoint
- LLM integration (OpenAI GPT-4o-mini OR Google Gemini)
- System prompt: knows Platform-X and can help with bookings
- Rate limiting per user (5/min)
- Chat history in localStorage
- Fallback message when AI unavailable
- Analytics: track chat usage
Estimated: 6-8 steps

---

## 13. Commands Cheat Sheet

Run dev server:
  cd ~/platform-x && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

Run tests:
  pytest

Apply migrations:
  alembic upgrade head

Create migration:
  alembic revision --autogenerate -m "description"

Seed demo data:
  python -m app.scripts.seed_all

Check services:
  sv status platform-x-api platform-x-tunnel

Restart Platform-X:
  sv restart platform-x-api

Get current tunnel URL:
  cat ~/platform-x/logs/tunnel.url

---

## 14. Test Count: 154 tests, all passing

Test files:
- test_health.py
- test_security.py (11)
- test_schemas.py (7)
- test_auth_api.py (11)
- test_tenants_api.py (5)
- test_bookings_api.py (11)
- test_services_api.py (12)
- test_orders_api.py (11)
- test_payments_api.py (11)
- test_rewards_referrals_api.py (12)
- test_notifications_api.py (8)
- test_analytics_api.py (6)
- test_production_hardening.py (7)
- test_demo_flow.py (2)
- test_web_pages.py (10)
- test_auth_pages.py (7)
- test_booking_page.py (5)
- test_payment_page.py (5)
- test_account_page.py (6)
- test_category_pages.py (7)

Speed: BCRYPT_ROUNDS=4 in tests, schema created once per session.

---

## 15. Key Files

- app/core/config.py — Settings (production hardening)
- app/core/security.py — bcrypt hash, JWT
- app/api/deps.py — get_current_tenant, get_current_user
- app/api/deps_admin.py — get_current_admin, require_role
- app/web/pages.py — HTML routes + CATEGORIES registry
- app/web/templates.py — shared Jinja2 env + globals (tenant_path, now_year)
- app/static/css/platform.css — light theme tokens + components
- app/static/css/platform-home.css — all page-specific styles (1500+ lines)
- app/static/js/px-core.js — shared utilities (getToken, authHeaders, initHeaderAuth, logout, count-up)
- app/templates/layouts/platform_base.html — main layout
- app/templates/partials/platform_header.html — dynamic header with avatar

---

## 16. How to Start a New Session

1. Read this HANDOFF.md fully
2. Read PROJECT-RULES.md
3. Check current state:
   cd ~/platform-x
   git log --oneline -5
   git tag -l
   sv status platform-x-api platform-x-tunnel
4. Ask user what to work on next
5. Follow working rules: backup → change → test → commit → report

---

## 17. Contact / User Preferences

User's goal: Professional Demo online to show to business partners.

User's style:
- Persian only, direct
- Does not want to be asked technical decisions
- Wants excellence quality
- Wants full phases completed (no skipping)
- Does not want features outside roadmap

---



---

## 18. Security Checklist (Before Production)

- [ ] Rate Limiting enabled
- [ ] Security headers configured
- [ ] JWT Refresh tokens implemented
- [ ] Password policy enforced
- [ ] Account lockout after failures
- [ ] Session revocation works
- [ ] CSRF protection on forms
- [ ] XSS audit complete
- [ ] SQL injection audit complete
- [ ] HTTPS enforced
- [ ] CORS restricted to real domains
- [ ] 2FA for admins
- [ ] Audit logs complete
- [ ] Secrets in secure store
- [ ] Backup strategy active
- [ ] Payment webhook signature verified
- [ ] PCI compliance reviewed

---

## 19. Production Deployment Checklist

- [ ] VPS provisioned
- [ ] PostgreSQL installed and migrated
- [ ] Nginx configured
- [ ] SSL certificate issued
- [ ] Custom domain configured
- [ ] Named Cloudflare Tunnel set up
- [ ] Subdomain routing per tenant
- [ ] Monitoring active (uptime + errors)
- [ ] Logs aggregated
- [ ] Backup automation running
- [ ] Health checks configured
- [ ] Environment variables secure
- [ ] DNS records verified
- [ ] Custom domain per tenant ready

---

## 20. Business Onboarding Checklist (per new tenant)

- [ ] Partner application received
- [ ] Application reviewed and approved
- [ ] Tenant created in DB
- [ ] Subdomain or custom domain configured
- [ ] SSL certificate issued
- [ ] Branding configured (colors, fonts, logo)
- [ ] Services imported (rooms, menu, packages, tickets)
- [ ] Staff accounts created
- [ ] Billing activated
- [ ] Tenant admin dashboard access granted
- [ ] Email/notifications configured
- [ ] Tenant live

---

**END OF v2 ROADMAP SECTIONS**




### Phase 18 — AI Foundation
- LLM provider integration (OpenAI GPT-4o-mini OR Google Gemini)
- AI service layer (prompt management, safety)
- Rate limiting per user
- Cost tracking + budget caps
- Context injection (tenant data, user data)
- Fallback + error handling
- AI audit log
Estimated: 6-8 steps

### Phase 19 — AI Guest Assistant
- Floating chat widget on public site
- AI Travel Planner (multi-business itinerary)
- AI Concierge (during trip)
- AI Booking Agent (can actually book)
- AI Negotiation (auto-offers from businesses)
- Chat history + context memory
- Multi-language AI
Estimated: 6-8 steps

### Phase 20 — Business Owner Panel
- Separate panel: /business/*
- Dashboard (bookings, revenue, occupancy)
- Services management (rooms, menu, packages)
- Bookings inbox + status
- Customer list + history
- Analytics (views, bookings, conversion)
- Staff accounts (Owner / Manager / Staff roles)
- Business notifications
Estimated: 10-12 steps

### Phase 21 — AI Business Assistant (Pricing Coach)
- AI competitor price intelligence (confidential)
- AI pricing suggestions
- AI demand forecasting
- AI competitor benchmark
- AI market insights
Estimated: 8-10 steps

### Phase 22 — Dynamic Pricing Rules
- Rule builder for owners
- Auto price adjustment (weekends, seasons, urgency)
- Capacity-based pricing
- Last-minute discounts
- AI learning from historical data
Estimated: 6-8 steps

### Phase 23 — AI Content Writer + Onboarding
- AI auto-generate service descriptions (4 languages)
- AI-suggested images
- AI Onboarding (URL → extract business info)
- AI menu/room importer
Estimated: 6-8 steps

### Phase 24 — Cross-Business Rewards Enhancement
- Spend points across categories
- Tier benefits (real perks)
- Redeem catalog
- Birthday rewards
- Milestone bonuses
Estimated: 4-6 steps

### Phase 25 — AI Marketing Copilot
- AI campaign suggestions
- Auto email/SMS to past customers
- AI discount suggestions based on trends
- Personalized offers per user segment
Estimated: 5-7 steps

### Phase 26 — Real-Time Occupancy + Analytics
- Live occupancy dashboard
- Predictive capacity
- Revenue forecasting
- Booking heatmaps
Estimated: 5-6 steps

### Phase 27 — Competitor Insights
- Aggregate market data (anonymized)
- Industry benchmarks
- Anonymous peer comparison
- Region/category insights
Estimated: 5-7 steps

### Phase 28 — AI Review Writer + Responder
- AI writes reviews from guest input
- Business AI auto-responds to reviews
- Multi-language reviews
- Sentiment analysis
Estimated: 4-5 steps

### Phase 29 — Business Leaderboard + AI Scoring ⭐
- Monthly AI scoring (5 criteria):
  - Customer Satisfaction (30%)
  - Service Quality (25%)
  - Pricing Competitiveness (20%)
  - Engagement (15%)
  - Platform Loyalty (10%)
- Per-category Leaderboard (Hotels, Restaurants, Travel, Entertainment)
- Auto-rewards:
  - Rank 1: Hero Featured + Sponsored Promotion + Gold Badge + Email to users + 0% commission next month
  - Rank 2: Category Featured + Silver Badge + 50% commission discount
  - Rank 3: Bronze Badge + Featured in search
- Public /leaderboard page
- Business Panel: My Score + AI tips
- Badges on cards
- AI suggestions for improvement
Estimated: 6-8 steps

### Phase 30 — Mobile App
- Framework: React Native or Flutter
- Guest app (iOS + Android)
- Business staff app
- Push notifications
- Store submission
Estimated: weeks/months

---

## Strategic Differentiation (from partner meeting 2026-09-28)

### For Guests (vs Agoda/Booking.com):
1. AI Travel Planner (itinerary in one click)
2. Multi-Business Cart (hotel + restaurant + tour in one booking)
3. Universal Rewards (cross-category earn and spend)
4. AI Negotiation (auto-offer discounts)
5. AI Concierge (24/7 in-trip assistant)
6. Group Booking simplified by AI
7. Referral Cash Rewards (real money, not just points)
8. AI Review Writer
9. 5-Tier Loyalty (Welcome/Silver/Gold/Platinum/Royal)
10. AI Trip Memory (hyper-personalization)

### For Business Owners:
1. Business Panel with AI assistant
2. AI Pricing Coach (market comparison)
3. Dynamic Pricing Rules
4. AI Content Writer (4 languages)
5. AI Onboarding (URL extraction, no forms)
6. AI Booking Manager
7. AI Marketing Copilot
8. Real-Time Occupancy Dashboard
9. AI Competitor Insights
10. AI Review Responder
11. Zero setup cost + AI-driven
12. Multi-Staff with role-based access

### Unique vs Agoda/Booking.com:
- AI everywhere (booking, pricing, content, marketing)
- Multi-business cart (they only have hotel)
- Cross-category rewards
- Confidential price intelligence
- AI-powered leaderboard with auto-rewards
- Real cash referral rewards

### Business-First Strategy:
- Prioritize Business Panel + AI Pricing Coach
- Then AI Guest Assistant
- Reason: businesses pay; users use

### Platform Commission:
- Rank 1 (monthly): 0% next month
- Rank 2 (monthly): 50% off
- Rank 3 (monthly): standard
- Standard rate: TBD (decision pending)


END OF HANDOFF
