# Platform-X — API Specification

> REST API design for the multi-tenant platform.
> Base URL: https://api.platform-x.com/v1 (or per-tenant subdomain)

---

## 1. Design Principles

- RESTful, resource-oriented
- JSON request/response
- HTTP status codes for errors
- Versioned via URL path (/v1/)
- Tenant-scoped via subdomain OR header X-Tenant-ID
- Auth: Bearer token (JWT) for API, session cookie for web
- Rate limited
- Idempotent where applicable (POST with idempotency key)

---

## 2. Authentication Endpoints

POST /auth/register
- Body: email, password, first_name, last_name, phone, language
- Returns: user object + session token

POST /auth/login
- Body: email, password
- Returns: user object + session token (web) or JWT (API)

POST /auth/logout
- Auth required
- Revokes current session

GET /auth/me
- Auth required
- Returns current user

POST /auth/forgot-password
- Body: email
- Sends reset link

POST /auth/reset-password
- Body: token, new_password

---

## 3. Booking Endpoints

GET /bookings
- Auth required
- Query: status, from_date, to_date, page, limit
- Returns paginated bookings

GET /bookings/{id}
- Auth required
- Returns booking details

POST /bookings
- Auth required
- Body: booking_type, service_id, check_in, check_out, guests, notes
- Idempotency-Key header supported
- Returns created booking

POST /bookings/{id}/cancel
- Auth required
- Cancels booking if allowed

---

## 4. Order Endpoints

GET /orders
POST /orders
GET /orders/{id}
POST /orders/{id}/cancel

Similar structure to bookings.

---

## 5. Payment Endpoints

POST /payments/intent
- Auth required
- Body: booking_id or order_id, amount, currency, method
- Returns: provider session / redirect URL

POST /payments/webhook/{provider}
- No auth (verified by signature)
- Receives provider callbacks
- Updates payment status

GET /payments/{id}
- Auth required
- Returns payment details

---

## 6. Rewards Endpoints

GET /rewards/me
- Auth required
- Returns: points, tier, next_tier, progress

GET /rewards/history
- Auth required
- Paginated rewards history

POST /rewards/redeem
- Auth required
- Body: reward_id
- Deducts points, applies benefit

---

## 7. Referral Endpoints

GET /referrals/me
- Auth required
- Returns referral code + list of referred users

POST /referrals/apply
- Auth required
- Body: referral_code
- Links current user to referrer (only once)

---

## 8. Service Endpoints (per tenant)

GET /services
- Public
- Query: type (room, table, treatment, event)
- Returns list of services

GET /services/{id}
- Public
- Returns service details

POST /services (admin only)
PATCH /services/{id} (admin only)
DELETE /services/{id} (admin only)

---

## 9. Notification Endpoints

GET /notifications
- Auth required
- Returns user's notifications

POST /notifications/{id}/read
- Auth required

---

## 10. Tenant Admin Endpoints

GET /admin/dashboard
- Tenant admin auth
- Returns stats: bookings today, revenue, occupancy, etc.

GET /admin/bookings
- Tenant admin auth
- Filters: status, date range, room

PATCH /admin/bookings/{id}
- Update booking status

GET /admin/customers
- Tenant admin auth
- Paginated customer list

GET /admin/finance
- Tenant admin auth
- Revenue reports, commission tracking

PATCH /admin/settings
- Update tenant config (branding, services, policies)

---

## 11. Platform Admin Endpoints

GET /platform/tenants
- Platform admin auth
- List all tenants

POST /platform/tenants
- Create tenant

PATCH /platform/tenants/{id}
- Update tenant

GET /platform/analytics
- Platform-wide analytics

GET /platform/subscriptions
- Subscription management

---

## 12. Error Format

All errors return:
{
  "success": false,
  "error": {
    "code": "BOOKING_NOT_FOUND",
    "message": "Human readable message",
    "details": {}
  }
}

HTTP Status Codes:
- 200 OK
- 201 Created
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 409 Conflict
- 422 Validation Error
- 429 Too Many Requests
- 500 Internal Server Error

---

## 13. Pagination

Query params:
- page (default 1)
- limit (default 20, max 100)

Response:
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8
  }
}

---

## 14. Rate Limiting

- Auth endpoints: 5 requests / minute / IP
- Booking/Order create: 20 requests / minute / user
- Public read: 100 requests / minute / IP
- Admin: 200 requests / minute / admin

Response header: X-RateLimit-Remaining, X-RateLimit-Reset

---

## 15. Versioning

URL: /v1/, /v2/, ...
Deprecation: 6-month warning before removal.
Sunset header used.

---

Last updated: September 2026
Status: Living document.
