# Platform-X — PostgreSQL Migration Guide

> SQLite (dev) -> PostgreSQL (production). This guide covers the
> switch, the compatibility status, and the verification steps.

## Compatibility status
- **Models:** 46 — all SQLAlchemy 2.0, dialect-agnostic
- **Migrations:** 33 — checked for PG compatibility
- **Blocking issues:** 0 (verified by scripts/check_postgres_compat.py)
- **Warnings:** 0

## Step 1 — Install PostgreSQL (Ubuntu 22.04)
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable --now postgresql

## Step 2 — Create DB + user
sudo -u postgres psql <<SQL
CREATE USER platformx WITH PASSWORD 'CHANGE_ME_STRONG';
CREATE DATABASE platform_x OWNER platformx;
GRANT ALL PRIVILEGES ON DATABASE platform_x TO platformx;
SQL

## Step 3 — Update .env
DATABASE_URL=postgresql://platformx:CHANGE_ME_STRONG@localhost:5432/platform_x

## Step 4 — Run migrations
cd /opt/platform-x
sudo -u platformx ./venv/bin/alembic upgrade head

Expected: no errors, ends at head revision.

## Step 5 — Seed base data
sudo -u platformx ./venv/bin/python -m app.scripts.seed_all
sudo -u platformx ./venv/bin/python -m app.scripts.seed_reward_rules
sudo -u platformx ./venv/bin/python -m app.scripts.seed_redeem_options

## Step 6 — Verify
psql "postgresql://platformx:CHANGE_ME_STRONG@localhost:5432/platform_x" -c "\dt"
# Should list ~50 tables.

## Step 7 — Run tests against Postgres (optional, advanced)
# Tests use SQLite in-memory by default. To run against Postgres:
export DATABASE_URL=postgresql://platformx:CHANGE_ME_STRONG@localhost:5432/platform_test
pytest tests/ -n auto -q

## Compatibility notes
The following patterns are safe on both SQLite and PostgreSQL:
- Numeric(12, 2) for money
- String(N) with explicit length
- DateTime(timezone=True) for timestamps
- JSON for metadata
- UniqueConstraint + Index

The following are avoided:
- JSONB (Postgres-only) — use JSON instead
- Array types — use JSON instead
- Native UUID type — we use String(36) for portability
- server_default=sa.text('1') for booleans — replaced with 'true'/'false'

## Rollback (PG -> SQLite)
Rarely needed, but possible:
1. Update DATABASE_URL back to sqlite:///./platform_x.db
2. alembic upgrade head (SQLite migrations are also maintained)
3. Copy seed data manually if needed

## Verifying compatibility after code changes
Run: python scripts/check_postgres_compat.py
Should output: CLEAN

## Common Postgres issues
| Symptom | Cause | Fix |
|---------|-------|-----|
| password authentication failed | bad password | update .env + reload service |
| relation does not exist | migrations not run | alembic upgrade head |
| too many connections | missing pool config | add pool_size in SQLAlchemy |
| SSL required | cloud PG | add ?sslmode=require to URL |
| timezone off | tz-aware datetimes | ensure DateTime(timezone=True) |

## Performance tips (PG)
- Add indexes on all FK columns (already done)
- Use EXPLAIN ANALYZE on slow queries
- Increase shared_buffers for larger VPS (default is conservative)
- Enable pg_stat_statements for query profiling

*End of guide.*
