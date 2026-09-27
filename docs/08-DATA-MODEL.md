# Platform-X — Data Model

> Database schema for the multi-tenant platform.
> Every table has tenant_id for isolation.

---

## 1. Design Principles

- Every table has tenant_id (except global tables).
- All IDs are UUIDs or ULIDs (sortable).
- All timestamps are UTC ISO 8601.
- Soft delete where appropriate (deleted_at).
- Foreign keys enforced.
- Indexes on tenant_id + frequent queries.
- No nullable foreign keys unless intentional.

---

## 2. Tables Overview

Global tables (platform-wide):
- tenants
- platform_admins
- audit_logs
- subscriptions

Per-tenant tables (isolated by tenant_id):
- users (guests)
- sessions
- bookings
- orders
- payments
- rewards
- referrals
- notifications
- analytics_events
- services (rooms, tables, treatments, etc.)

---

## 3. Global Tables

### tenants

Represents a business on the platform.

Columns:
- id (UUID, primary key)
- slug (unique, e.g., "trianon-hotel")
- name (brand name)
- domain (custom domain, nullable)
- subdomain (e.g., "trianon", nullable)
- tier (starter, professional, enterprise)
- status (active, suspended, deleted)
- config (JSON — branding, colors, languages)
- created_at
- updated_at
- deleted_at (nullable)

Indexes: slug, domain, subdomain, status

### platform_admins

Platform-level admins.

Columns:
- id (UUID)
- email (unique)
- password_hash
- name
- role (super_admin, admin, support)
- mfa_enabled (bool)
- mfa_secret (nullable)
- created_at
- last_login_at

### audit_logs

All admin actions logged.

Columns:
- id (UUID)
- actor_id (user or admin)
- actor_type (user, tenant_admin, platform_admin)
- tenant_id (nullable)
- action (create, update, delete, login, etc.)
- target_table
- target_id
- changes (JSON)
- ip_address
- user_agent
- created_at

### subscriptions

Tenant subscriptions to platform.

Columns:
- id (UUID)
- tenant_id (FK)
- plan (starter, professional, enterprise)
- status (active, cancelled, past_due)
- price (decimal)
- currency (AED, USD)
- billing_cycle (monthly, yearly)
- current_period_start
- current_period_end
- cancelled_at (nullable)
- created_at
- updated_at

---

## 4. Per-Tenant Tables

### users (guests)

End-users (guests, travelers).

Columns:
- id (UUID)
- tenant_id (FK, indexed)
- email (unique per tenant)
- phone (unique per tenant, nullable)
- password_hash
- first_name
- last_name
- language (en, ar, fil, hi)
- preferred_currency (AED, USD, etc.)
- email_verified (bool)
- phone_verified (bool)
- points (int, default 0)
- tier (welcome, silver, gold, platinum, royal)
- referral_code (unique per tenant)
- referred_by (nullable, FK to users)
- room_number (nullable)
- status (active, suspended, deleted)
- created_at
- updated_at
- deleted_at (nullable)

Indexes: tenant_id + email (unique), tenant_id + phone, referral_code

### sessions

Active login sessions.

Columns:
- id (UUID)
- tenant_id (FK, indexed)
- user_id (FK, indexed)
- token_hash (unique)
- ip_address
- user_agent
- created_at
- expires_at (indexed)
- revoked (bool, default false)

Indexes: token_hash, expires_at, tenant_id + user_id

### bookings

Room and service bookings.

Columns:
- id (UUID)
- tenant_id (FK, indexed)
- user_id (FK, indexed)
- booking_type (room, table, treatment, event, package, flight)
- service_id (FK to services, nullable)
- service_name (denormalized)
- check_in (date)
- check_out (date, nullable)
- room_number (nullable)
- guests (int)
- amount (decimal)
- discount (decimal, default 0)
- total_amount (decimal)
- currency (AED, USD)
- status (pending, confirmed, checked_in, checked_out, cancelled)
- payment_status (pending, paid, refunded, failed)
- referral_code (nullable)
- notes (text, nullable)
- created_at
- updated_at
- cancelled_at (nullable)

Indexes: tenant_id + user_id, tenant_id + check_in, tenant_id + status

### orders

Service orders (dining, room service, etc.).

Columns:
- id (UUID)
- tenant_id (FK, indexed)
- user_id (FK, indexed)
- service_type (dining, room_service, spa, pool, etc.)
- service_name
- quantity (int)
- amount (decimal)
- currency (AED, USD)
- status (pending, preparing, ready, delivered, cancelled)
- payment_status (pending, paid, refunded)
- notes (text, nullable)
- created_at
- updated_at
- delivered_at (nullable)

Indexes: tenant_id + user_id, tenant_id + status

### payments

Payment transactions.

Columns:
- id (UUID)
- tenant_id (FK, indexed)
- user_id (FK, indexed)
- booking_id (nullable, FK)
- order_id (nullable, FK)
- amount (decimal)
- currency (AED, USD)
- provider (telr, stripe, paytabs, checkout)
- provider_reference (unique)
- status (pending, success, failed, refunded)
- method (card, apple_pay, google_pay, cash)
- metadata (JSON — provider response)
- created_at
- completed_at (nullable)

Indexes: tenant_id + user_id, provider_reference, status

---

### rewards

Reward points history.

Columns:
- id (UUID)
- tenant_id (FK, indexed)
- user_id (FK, indexed)
- reward_type (earn, redeem, adjust)
- points (int, can be negative)
- description (nullable)
- reference_id (nullable — booking_id, order_id)
- created_at

Indexes: tenant_id + user_id, created_at

### referrals

Referral tracking.

Columns:
- id (UUID)
- tenant_id (FK, indexed)
- referrer_user_id (FK, indexed)
- referred_user_id (FK, indexed)
- referral_code (indexed)
- status (pending, completed, cancelled)
- reward_points (int, default 0)
- first_booking_id (nullable, FK)
- created_at
- completed_at (nullable)

Indexes: tenant_id + referrer_user_id, referral_code

### notifications

Sent notifications log.

Columns:
- id (UUID)
- tenant_id (FK, indexed)
- user_id (FK, indexed)
- channel (email, whatsapp, sms, in_app, telegram)
- template (booking_confirmed, order_ready, etc.)
- subject (nullable)
- content (text)
- status (pending, sent, failed, delivered, read)
- provider_reference (nullable)
- metadata (JSON, nullable)
- created_at
- sent_at (nullable)
- delivered_at (nullable)
- read_at (nullable)

Indexes: tenant_id + user_id, status, channel

### services

Tenant services (rooms, tables, treatments, etc.).

Columns:
- id (UUID)
- tenant_id (FK, indexed)
- type (room, table, treatment, event, etc.)
- name
- description (text, nullable)
- price (decimal)
- currency (AED, USD)
- capacity (int, nullable)
- attributes (JSON — flexible for different types)
- image_urls (JSON array)
- status (active, inactive)
- display_order (int)
- created_at
- updated_at

Indexes: tenant_id + type, tenant_id + status

### analytics_events

Event log for analytics.

Columns:
- id (UUID)
- tenant_id (FK, indexed)
- user_id (nullable, FK)
- event_type (page_view, booking_started, booking_completed, etc.)
- metadata (JSON)
- ip_address
- user_agent
- created_at

Indexes: tenant_id + event_type, tenant_id + user_id, created_at

---

## 5. Relationships

- tenants → users (1:N)
- tenants → services (1:N)
- tenants → subscriptions (1:1 current)
- users → bookings (1:N)
- users → orders (1:N)
- users → payments (1:N)
- users → rewards (1:N)
- users → referrals (as referrer, 1:N)
- users → referrals (as referred, 1:1)
- bookings → payments (1:N, at least 1)
- orders → payments (1:N)
- sessions → users (N:1)

---

## 6. Data Isolation Strategy

Every per-tenant query MUST include tenant_id in WHERE clause.

Enforcement:
1. Application-level: every query scoped by tenant.
2. Database-level (optional): Row-Level Security (PostgreSQL RLS).

If RLS is enabled:
- Session variable `app.current_tenant` set per request.
- Policies enforce `tenant_id = current_setting('app.current_tenant')`.

Decision: Start with application-level. Add RLS in Phase 3 as extra protection.

---

## 7. Migrations Strategy

Tool: Alembic
- Version-controlled migrations.
- Every schema change requires a migration.
- Migrations tested on staging before production.
- Rollback tested for every migration.

---

## 8. Backup Strategy

Database backups:
- Daily full dump
- Weekly archive (30 days)
- Monthly archive (12 months)

Point-in-time recovery (PITR):
- WAL archiving enabled in production.
- Recovery to any point in last 7 days.

---

## 9. Performance Considerations

Indexes:
- All foreign keys indexed.
- tenant_id always in composite indexes.
- Query planner reviewed for slow queries.

Partitioning (Phase 6+):
- Consider partitioning large tables by tenant_id or created_at when > 100M rows.

---

## 10. Data Retention

- users: retained indefinitely unless deleted by user
- sessions: purged after expiry + 30 days
- notifications: retained 12 months
- analytics_events: retained 24 months
- audit_logs: retained 7 years (compliance)
- deleted tenants: hard delete after 90 days soft-delete window

---

Last updated: September 2026
Status: Living document.
