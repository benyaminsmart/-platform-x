# Platform-X

Multi-tenant smart platform for hotels, restaurants, entertainment, and travel agencies.

Status: Phase 2 (Core Architecture) — Backend complete, ready for frontend.

## Tech Stack

- Backend: FastAPI 0.115 + Python 3.13
- Database: PostgreSQL (production) / SQLite (local dev)
- ORM: SQLAlchemy 2.0
- Migrations: Alembic
- Auth: JWT (python-jose) + bcrypt
- Testing: pytest + httpx TestClient

## Project Structure

app/
  api/          - FastAPI routers
  core/         - config, security
  db/           - Base, session, engine
  models/       - SQLAlchemy ORM models
  schemas/      - Pydantic request/response models
  services/     - Business logic (DB operations)
  scripts/      - Seed scripts
tests/          - pytest suite
alembic/        - Migration history
docs/           - Project documentation

Rule: Routes call services. Services talk to the DB. Routes never touch the DB directly.

## Local Development

1. Create venv:            python -m venv venv
2. Activate:               source venv/bin/activate
3. Install deps:           pip install -r requirements.txt
4. Configure:              cp .env.example .env
5. Run migrations:         alembic upgrade head
6. Seed demo data:         python -m app.scripts.seed_all
7. Run server:             uvicorn app.main:app --reload --port 8000

API docs: http://localhost:8000/docs
Health:   http://localhost:8000/health

## Testing

pytest                          - full suite
pytest -x                       - stop on first failure
pytest tests/test_auth_api.py   - single file

Test suite is speed-optimized (BCRYPT_ROUNDS=4 for tests).

## Environment Variables

See .env.example. Critical:

APP_ENV               dev: development    prod: production
APP_DEBUG             dev: true           prod: false
SECRET_KEY            dev: default        prod: 32+ chars, not default
DATABASE_URL          dev: SQLite file    prod: postgresql://...
CORS_ORIGINS          dev: localhost      prod: real domain
ENABLE_MOCK_PAYMENTS  dev: true           prod: false

App fails to start if production is misconfigured.

## Multi-Tenancy

- Every tenant-scoped request needs X-Tenant-Slug header.
- Fallback to DEFAULT_TENANT_SLUG if header absent (dev convenience).
- JWT tokens are bound to a tenant; using a token on a different tenant returns 401.

## Authentication

Two separate auth flows:

1. Users (guests): POST /auth/register, POST /auth/login, GET /auth/me
   JWT carries sub (user id) and tenant_id.
2. Platform admins: POST /platform/auth/login, GET /platform/me
   JWT carries sub (admin id) and actor=platform_admin.
   Role-gated endpoints use require_role(...).

## Migrations

After modifying a model:
  alembic revision --autogenerate -m "short description"

Apply:
  alembic upgrade head

Rollback one:
  alembic downgrade -1

## Payments

- MockPaymentProvider used in development.
- Switch to real provider by implementing PaymentProvider in app/services/payment_provider.py.
- /payments/mock/confirm/{ref} disabled when ENABLE_MOCK_PAYMENTS=false.

## INTEGRATION-READY Features (mock data/provider)

The following features are code-complete, logic-tested, and ready to
plug real providers/data in Stage 7 (buyer-driven). Until then they
run on mock data or mock providers so the platform stays demoable.

| Feature | What is mock | What is real |
|---------|--------------|--------------|
| AI Voice Booking (Phase 64) | Voice→text input — user sends a transcript | Intent parsing, search, AI polish |
| Local Experiences (Phase 65) | Event data | Haversine distance, AI recommendation |
| AI Provider | Default replies | Full integration layer (switch to gemini/openai via `AI_PROVIDER` env) |
| Payment Provider | Provider selection | Full abstraction (Telr/Stripe/PayTabs ready via `PaymentProvider`) |
| Installments | Payment capture | Installment ledger, scheduling logic |

> ⚠️ Anything marked "mock" above becomes real after the buyer
> configures the relevant `.env` keys (Stage 7). No code changes needed.

## Seed Data

python -m app.scripts.seed_all          - tenants + services + demo admin
python -m app.scripts.seed_tenants      - tenants only
python -m app.scripts.seed_services     - services only
python -m app.scripts.seed_admin        - admin only

All seed scripts are idempotent.
Demo admin (dev only): admin@platform-x.local / ChangeMe123!
Change before any public demo.

## API Surface

Health               /health              none
Auth                 /auth                public / JWT
Tenants              /tenants             public
Services             /services            public read, admin write
Bookings             /bookings            JWT
Orders               /orders              JWT
Payments             /payments            JWT (webhook public)
Rewards              /rewards             JWT
Referrals            /referrals           JWT
Notifications        /notifications       JWT
Analytics            /analytics           public track, admin summary
Platform Admin       /platform            admin JWT

## License & Authors

- **License:** Proprietary — All Rights Reserved. See [LICENSE](LICENSE).
- **Authors:** See [AUTHORS.md](AUTHORS.md).
- **Transfer on sale:** See LICENSE § "TRANSFER ON SALE".

## Project Rules

See PROJECT-RULES.md for the quality bar (EXCELLENCE).

- Backup before every change.
- One step at a time, test after each step.
- Commit after every success.
- No feature added without roadmap approval.
