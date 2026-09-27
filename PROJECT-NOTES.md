k
# Platform-X — Project Notes

> Technical decisions, architectural context, reasoning.
> Read with HANDOFF.md and AI-CONTEXT.md.

---

## 1. Why Platform-X

Market observation:
- Hotels pay 15-20% commission to Booking.com/Agoda.
- Restaurants, entertainment, travel agencies — same problem.
- All need same infrastructure: auth, payments, bookings, notifications.
- Build once → serve many.

Platform-X is that infrastructure.
Multi-tenant platform. Many businesses onboard. Each has own branded presence.

---

## 2. Why Multi-Tenant (not Multi-Instance)

Option A — Multi-Instance: separate install per business.
- Pros: full isolation.
- Cons: duplication, unmaintainable.

Option B — Multi-Tenant: one codebase, many businesses.
- Pros: single codebase, shared features, economies of scale.
- Cons: need tenant isolation.

Decision: Option B.

---

## 3. Database Architecture

Sub-option A — Shared DB, Shared Schema:
- One DB, tenant_id column on all tables.
- Pros: simple, cheap.
- Cons: harder beyond 100 tenants.

Sub-option B — Shared DB, Schema per Tenant.
- Pros: better isolation.
- Cons: complex migrations.

Sub-option C — DB per Tenant.
- Pros: max isolation.
- Cons: expensive.

Decision: Sub-option A. Migrate to B/C later if needed.

---

## 4. Why PostgreSQL (Production)

SQLite OK for dev. Platform-X needs:
- Multi-tenant queries
- Concurrent writes
- Better scaling

Decision: PostgreSQL production, SQLite dev. SQLAlchemy ORM for both.

---

## 5. Why FastAPI

Modern, fast, type-safe. Auto API docs. Pydantic validation. Async support. Python ecosystem.

Decision: FastAPI.

---

## 6. Frontend Strategy

Phase 1: Vanilla HTML/CSS/JS. Fast, no build step.
Phase 2+: React or Next.js. Component model, state management.

Decision: Start vanilla, migrate to React later.

---

## 7. Authentication

Web: Session tokens. Server-side revocation.
API/Mobile: JWT. Refresh tokens.

Decision: Dual auth.

---

## 8. Domain Strategy

Options: subdomain, custom domain, both.

Decision: Both.
- Default: subdomain
- Premium: custom domain

---

## 9. Payment Strategy

Considered: Stripe, Telr, PayTabs, Checkout.com.

For multi-tenant split: Telr or PayTabs marketplace.
Each tenant needs sub-account.

Decision: Multi-provider adapter pattern. Start with Telr.

---

## 10. Testing Strategy

Phase 1: Manual smoke tests.
Phase 2+: pytest, unit + integration + E2E. Coverage 80%+.

Decision: Defer infra to Phase 2, structure code testable from Phase 1.

---

## 11. Backup & Recovery

Layers:
1. Per file change: file copy
2. Per session: checkpoint
3. Per phase: git tag + backup

DR:
- DB: daily dump, weekly full
- Code: git off-site
- Config: .env never in git

---

## 12. Code Organization

backend/
  api/ — routes
  core/ — config, db, security
  models/ — db models
  services/ — business logic
  schemas/ — pydantic
  utils/ — helpers
  tests/ — test suite

frontend/, mobile/, telegram-bot/, deploy/, docs/, backups/

---

## 13. Security Standards

- Secrets in .env only
- Input validated
- Passwords hashed (bcrypt/argon2)
- Sessions validated server-side
- HTTPS only
- Rate limiting on auth
- SQL injection prevention (ORM)
- XSS prevention
- CSRF tokens

---

## 14. Performance Targets

- API: <200ms (95%)
- Page load: <2s on 3G
- DB: indexed, no N+1
- Redis cache (Phase 3+)

---

## 15. Known Challenges

1. Tenant isolation
2. Scaling 1 → 1000 tenants
3. SSL per domain
4. Payment splits
5. Multi-currency
6. Multi-language
7. Mobile apps
8. Telegram bot

---

## 16. Open Questions

- Final brand name + domain
- Payment provider choice
- Mobile framework
- CI/CD provider
- Monitoring stack
- Hosting location

---

Last updated: September 2026
Status: Living document.
