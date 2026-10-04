# Platform-X — Tech Debt List (Honest)

> Published as-is. Buyer should know these before purchase.

## Not yet shipped (scoped, free)
- Phase 82 — PostgreSQL migration runbook (in progress)
- Payment production (Telr/Stripe) — Phase 10, buyer-driven
- Mobile app — Phase 16, optional
- Business onboarding tools — Phase 13
- Trianon first-tenant migration — Phase 15

## Known limitations
- 1487 tests pass but no CI pipeline is committed (easy add: GitHub Actions)
- No metrics/Prometheus exporter enabled by default (optional)
- No caching layer (Redis) — fine at current scale
- Single-language docs (product itself supports 4 languages)
- AI features ship with mock providers — real providers are drop-in
- Business-owner rewards module is architected but not built

## Deliberately out of scope (may never be added)
- Marketplace for third-party plugins
- Native desktop apps
- White-label multi-brand under one instance

## Non-issues (verified not broken)
- Payment-to-reward flow: tested and works with reward_rules seeded
- Multi-tenancy isolation: enforced at query layer
- Rewards ledger: immutable, idempotent, audit-tested

## Priority if buyer continues
1. Payment production (revenue-critical)
2. First real tenant (validation)
3. CI/CD (safety)
4. Mobile app (reach)
