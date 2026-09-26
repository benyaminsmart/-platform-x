# Platform-X — Architecture

> Technical architecture of the multi-tenant platform.

---

## 1. High-Level Concept

Platform-X is a multi-tenant SaaS platform that serves multiple hospitality, travel, and tourism businesses from a single codebase and infrastructure.

Each business (a tenant) is:
- Fully branded (own logo, colors, domain)
- Configurable (own services, pricing, policies)
- Isolated (data never leaks between tenants)

Shared infrastructure:
- Authentication
- Payments
- Bookings
- Notifications
- Analytics
- AI features

---

## 2. System Diagram

Users (Guests, Travelers)
        |
        v
Surfaces (Web | Mobile | Telegram | API)
        |
        v
Platform-X Core
  - API Gateway (FastAPI)
  - Auth | Bookings | Payments | Rewards
  - Tenants | Notify | Analytics | AI
        |
        v
Shared Data Layer (PostgreSQL)
  - tenant_id on all tables
  - Row-level isolation
        |
        v
Tenants (Trianon | Hotel B | Restaurant | ...)

---

## 3. Tenancy Model

Each Tenant Has:

- Identity: tenant_id, domain, brand name
- Configuration: services, pricing, policies, languages
- Users: guests who registered on that tenant's domain
- Bookings: orders, reservations, requests

Isolation:

- Every database table has tenant_id.
- Every API request scoped to a tenant.
- Every user belongs to one tenant.
- Cross-tenant queries blocked by default.

---

## 4. Domain Strategy

Supported Patterns:

1. Subdomain: tenant1.platformx.com, tenant2.platformx.com
2. Custom Domain: trianon.com, hotelb.com (DNS points to platform)

SSL:

- Wildcard SSL for subdomains.
- Per-domain SSL via Let's Encrypt for custom domains.

Routing:

- Nginx reads Host header.
- Maps to tenant.
- Passes tenant_id to backend.

---

## 5. Authentication & Authorization

Guest (End-User) Auth:

- Registration with email + password.
- Password hashing: bcrypt or argon2.
- Session tokens for web.
- JWT for mobile & third-party APIs.

Tenant Admin Auth:

- Separate login for tenant admins.
- Role-based access (owner, manager, staff).
- Strict rate limiting.

Platform Admin Auth:

- Highest level.
- MFA required.
- Audit log for all actions.

---

## 6. Database Architecture

Shared Schema, Shared Database:

- One PostgreSQL database.
- All tables have tenant_id.
- Indexes optimized for tenant-scoped queries.

Core Tables (planned):

- tenants — businesses
- users — end users
- sessions — active sessions
- bookings — reservations
- orders — service orders
- payments — transactions
- rewards — loyalty points
- referrals — referral tracking
- notifications — sent messages
- analytics_events — event log

Migrations:

- Alembic for schema changes.
- Every migration tested on staging first.

---

## 7. Payment Architecture

Multi-Provider Strategy:

Abstract payment interface with adapters:
- Telr (UAE) — primary
- Stripe — fallback (international)
- PayTabs — alternative
- Checkout.com — enterprise

Split Payments:

For tenants that need platform commission:
- Sub-accounts per tenant (provider-dependent).
- Automatic split on transaction.
- Fallback: manual settlement with reporting.

PCI Compliance:

- Card data never touches our servers.
- Hosted payment fields or iframe.
- Only tokens stored.

---

## 8. Booking Engine

Supported Booking Types:

1. Rooms (hotels)
2. Tables (restaurants)
3. Treatments (spas)
4. Events (entertainment)
5. Flights (later)
6. Packages (later)

Common Flow:

1. User selects service + dates
2. System checks availability
3. User confirms details
4. Payment processed
5. Confirmation sent (WhatsApp, email, in-app)
6. Booking appears in user's account
7. Tenant admin sees booking in dashboard

Availability Logic:

- Real-time for rooms & tables.
- Time-slot based for treatments.
- Custom logic per service type.

---

## 9. Notifications Architecture

Channels:

- WhatsApp — primary (UAE market)
- Email — transactional
- SMS — fallback
- In-App — for mobile & web
- Telegram — for bot users

Events:

- Booking confirmed
- Payment received
- Reminder (24h before)
- Order ready
- Service completed

Delivery:

- Queue-based (Celery or RQ).
- Retry logic.
- Delivery log per tenant.

---

## 10. Mobile Application

Strategy:

- Native or React Native (decision in Phase 8).
- Same API as web.
- Push notifications.
- Offline-first for bookings view.

Distribution:

- iOS App Store
- Google Play Store

---

## 11. Telegram Bot

Features:

- Guest services (order food, request towels, etc.)
- Booking status
- Rewards balance
- Notifications

Architecture:

- Bot server as separate service.
- Webhooks from Telegram.
- Auth via phone number link.

---

## 12. AI Features (Phase 7)

Planned:

- Concierge AI — answers guest questions
- Smart pricing — suggests prices for tenants
- Demand forecasting — predicts occupancy
- Review analysis — sentiment on feedback

Technology:

- OpenAI GPT or Claude API.
- Fine-tuning on tenant data (with permission).

---

## 13. Security Architecture

Layers:

1. Network — HTTPS only, firewall, DDoS protection
2. Application — input validation, CSRF, XSS, SQL injection prevention
3. Session — token rotation, expiry, revocation
4. Data — encryption at rest, encryption in transit
5. Audit — all admin actions logged

Rate Limiting:

- Auth endpoints: strict
- Booking endpoints: moderate
- Public endpoints: lenient

---

## 14. Deployment Architecture

Environments:

- Development — local (Termux)
- Staging — VPS mirror of production
- Production — main VPS

Production Stack:

- Ubuntu 22.04
- Nginx (reverse proxy + static files)
- Gunicorn + Uvicorn (FastAPI)
- PostgreSQL
- Redis (cache + queue)
- Certbot (SSL)

CI/CD:

- GitHub Actions or GitLab CI (decision later)
- Automated tests on every commit
- Manual approval for production deploy

---

## 15. Monitoring & Logging

Monitoring:

- Sentry (error tracking)
- Prometheus + Grafana (metrics) — later
- Uptime monitoring

Logging:

- Structured JSON logs
- Centralized (e.g., Loki or self-hosted)
- Per-tenant log separation for privacy

---

## 16. Backup & Recovery

Database:

- Daily full dump
- Weekly archive (30 days)
- Monthly archive (12 months)

Files:

- Static assets backed up weekly
- Versioned via git

Recovery Targets:

- RPO (Recovery Point Objective): 24 hours
- RTO (Recovery Time Objective): 2 hours

---

## 17. Scalability Plan

Phase 1-3 (1-10 tenants):

- Single server
- Single database

Phase 4-5 (10-50 tenants):

- Separate database server
- Redis for caching
- CDN for static assets

Phase 6+ (50+ tenants):

- Multiple application servers
- Load balancer
- Read replicas for database
- Sharding if necessary

---

## 18. Open Questions

- Mobile framework: React Native vs Flutter
- CI/CD provider: GitHub Actions vs GitLab CI
- Monitoring stack: Sentry only vs Prometheus + Grafana
- Payment provider: Telr vs PayTabs vs both
- AI provider: OpenAI vs Anthropic vs self-hosted

These will be resolved when relevant phases begin.

---

Last updated: September 2026
Status: Living document.
