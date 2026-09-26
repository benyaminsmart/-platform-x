# Platform-X — Project Notes

> **Purpose:** Technical decisions, architectural context, and reasoning behind choices.
>
> Read together with HANDOFF.md.

---

## 1. Why Platform-X (not just Trianon)

Trianon Royal Hotel is the first project. But we saw the bigger opportunity:

- Hotels pay 15-20% commission to Booking.com and Agoda.
- Restaurants, entertainment centers, travel agencies — same problem.
- All of them need the same infrastructure (auth, payments, bookings, notifications).
- Building it once → serving many.

Platform-X is that infrastructure. Trianon is the first proof it works.

---

## 2. Why Multi-Tenant (not Multi-Instance)

Two options were considered:

**Option A — Multi-Instance:** Each business gets its own separate installation.
- Pros: full isolation, simple code.
- Cons: massive duplication, impossible to maintain, no shared features.

**Option B — Multi-Tenant:** One codebase, one database, many businesses.
- Pros: single codebase, shared features, shared updates, economies of scale.
- Cons: slightly more complex (need tenant isolation).

**Decision: Option B — Multi-Tenant.**

---

## 3. Database Architecture (Preliminary)

Two sub-options within multi-tenant:

**Sub-option A — Shared Database, Shared Schema:**
- One database, tables have `tenant_id` column.
- Pros: simple, cheap, easy to query across tenants.
- Cons: harder to scale beyond 100 tenants.

**Sub-option B — Shared Database, Separate Schemas:**
- One database, one schema per tenant (PostgreSQL feature).
- Pros: better isolation, easier per-tenant backup.
- Cons: more complex migrations.

**Sub-option C — Database per Tenant:**
- One database per tenant.
- Pros: maximum isolation.
- Cons: expensive, hard to manage at scale.

**Preliminary decision: Sub-option A** — suitable for first 100 tenants. We can migrate to B or C later if needed.

---

## 4. Why PostgreSQL (for Platform-X)

SQLite is perfect for Trianon (single hotel, low traffic).
But Platform-X needs:
- Multi-tenant queries
- Concurrent writes
- Row-level security (optional)
- Better scaling

**Decision: PostgreSQL for production, SQLite for local dev.**

Can use SQLAlchemy ORM to support both.

---

## 5. Why FastAPI (Again)

Same reasoning as Trianon:
- Modern, fast, type-safe.
- Auto-generated API docs.
- Great for APIs + microservices.
- Python ecosystem.

**Decision: FastAPI for the platform backend.**

---

## 6. Frontend Strategy

**Phase 1 (Trianon + early platform):** Vanilla HTML/CSS/JS
- Fast, no build step, easy to deploy.
- Perfect for hotel websites.

**Phase 2+ (Full platform dashboard):** React or Next.js
- Complex dashboards need component model.
- State management.
- Better DX for large apps.

**Decision: Start vanilla, migrate to React when complexity demands.**

---

## 7. Authentication Strategy

**For end-users (guests):**
- Session tokens (same as Trianon).
- Server-side revocation.
- Works well on web.

**For API (mobile apps + third parties):**
- JWT with short expiry.
- Refresh tokens for long sessions.
- Better for stateless clients.

**Decision: Dual auth** — session for web, JWT for API/mobile.

---

## 8. Domain Strategy

**Tenant domains:**
- Option A: Subdomain per tenant (`hotelname.platform.com`)
- Option B: Custom domain per tenant (`hotelname.com` pointing to platform)
- Option C: Both

**Decision: Option C — Both supported.**
- Default: subdomain
- Premium: custom domain
- DNS verified per tenant

---

## 9. Payment Strategy

**Providers under consideration:**
- Stripe (global, limited UAE support)
- Telr (UAE-based, split payment)
- PayTabs (Middle East, marketplace)
- Checkout.com (enterprise)

**For multi-tenant split payments:**
- Telr or PayTabs support marketplace model.
- Each tenant needs a sub-account.

**Decision: Multi-provider adapter pattern.**
- Start with Telr (UAE-native).
- Add others as needed.
- Abstract payment logic behind an interface.

---

## 10. Testing Strategy

**Phase 1:**
- Manual smoke tests.
- No formal test suite.

**Phase 2+:**
- pytest for backend.
- Unit tests for all business logic.
- Integration tests for API endpoints.
- E2E tests for critical flows (booking → payment → confirmation).
- Coverage target: 80%+
- CI/CD runs tests on every commit.

**Decision: Defer test infrastructure to Phase 2, but structure code to be testable from Phase 1.**

---

## 11. Backup & Recovery

**Backup layers:**
1. Per file change: quick file copy in `backups/`
2. Per session: full project checkpoint
3. Per phase: tagged git release + full backup

**Disaster recovery:**
- Database: daily dump + weekly full backup
- Code: git (off-site via GitHub/GitLab)
- Config: `.env` stored securely, never in git

**Decision: Backup automation script + manual checkpoints.**

---

## 12. Code Organization (Planned)
