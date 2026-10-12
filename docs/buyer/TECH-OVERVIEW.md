# Platform-X — Technical Overview

## 1. Purpose
AI-First Hospitality Platform, built to be categorically better than
Booking.com and Agoda. Multi-tenant, AI-native, rewards-ledgered.

## 2. Architecture
- Backend: FastAPI (Python 3.13), SQLAlchemy 2.0, Alembic
- Frontend: Jinja2 server-rendered templates, mobile-first PWA
- DB: SQLite (dev) -> PostgreSQL (production)
- Auth: JWT + bcrypt + lockout + security headers + CORS
- AI: provider-agnostic layer (Gemini / OpenAI / Anthropic / mock)
- Rewards: immutable ledger + wallet projection + referral engine

## 3. Directory map
- app/api/        -> HTTP endpoints (200+)
- app/services/   -> business logic (60+)
- app/models/     -> SQLAlchemy models (46+)
- app/schemas/    -> Pydantic schemas
- app/templates/  -> Jinja2 UI
- app/scripts/    -> seed + migration helpers
- alembic/        -> DB migrations
- scripts/        -> dev helpers (backup, step, handoff)
- scripts/deploy/ -> install/update/backup/restore
- tests/          -> 1502 tests
- docs/           -> technical + strategy documents

## 4. Key subsystems
### 4.1 Booking
Search -> select -> rate plan -> promotion -> payment -> reward.
### 4.2 Rewards
Immutable ledger; per-category rates; tier multipliers; caps.
### 4.3 Referral
Full lifecycle; fraud checks; AED 20/15; monthly cap AED 100.
### 4.4 AI
Grounded deterministic-first; 15+ capabilities across 3 layers.
### 4.5 Public API
Versioned; API keys; webhooks.

## 5. Security
- HSTS, CSP, X-Frame-Options
- HTTPS redirect middleware
- JWT fail-fast; bcrypt; lockout
- Rate limits on all routes
- Immutable audit log
- No secrets in repo

## 6. Testing
- 1502 tests, all passing, ~60s parallel
- Coverage: auth, bookings, payments, rewards, referrals, AI, admin

## 7. Deployment
See DEPLOY-CHECKLIST.md. ~45 min on Ubuntu 22.04.

## 8. Growth path
Mobile app (API ready), real payment (provider-agnostic),
onboarding tools, Trianon migration, business-owner rewards module.
