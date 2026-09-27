# Platform-X — Security Architecture

> Multi-layered security for a multi-tenant platform.

---

## 1. Threat Model

Assets to protect:
- Guest personal data (PII)
- Payment information (tokens only)
- Tenant business data (bookings, revenue)
- Platform admin credentials
- API keys and secrets

Threats:
- Unauthorized access (broken auth)
- Cross-tenant data leaks
- SQL injection
- XSS / CSRF
- DDoS attacks
- Credential stuffing
- Payment fraud
- Insider threats
- Supply chain attacks

---

## 2. Authentication

Passwords:
- Algorithm: argon2id (preferred) or bcrypt
- Minimum 8 characters
- No maximum (allow passphrases)
- No complexity requirements (modern guidance)
- Rate limit: 5 attempts / 15 min per account

Sessions (web):
- HttpOnly cookies
- Secure flag (HTTPS only)
- SameSite=Strict
- Session token: 32 bytes random (crypto-secure)
- Stored as SHA-256 hash in DB
- Expiry: 24 hours
- Rotate on login
- Revoke on logout

JWT (API):
- HS256 or RS256
- Short-lived access token: 15 min
- Long-lived refresh token: 30 days
- Refresh token rotation
- Revocation list in DB

Multi-Factor Authentication:
- Required for platform admins
- Optional for tenant admins
- TOTP-based (Google Authenticator)

---

## 3. Authorization

Role-Based Access Control (RBAC):
- platform_super_admin
- platform_admin
- platform_support
- tenant_owner
- tenant_manager
- tenant_staff
- guest

Tenant isolation:
- Every query scoped by tenant_id
- Application-level enforcement
- Optional RLS in PostgreSQL (Phase 3)

Permission checks:
- Middleware on every endpoint
- Deny by default
- Explicit allow rules

---

## 4. Data Protection

Encryption at rest:
- Database: encrypted volumes
- Backups: encrypted with separate key
- Secrets: stored in environment, not code

Encryption in transit:
- HTTPS/TLS 1.3 only
- HSTS enabled
- Certificates: Let's Encrypt, auto-renewal

PII handling:
- Minimal collection
- Clear purpose
- Right to deletion (GDPR/UAE PDPL)
- Data retention policy enforced

---

## 5. Input Validation

All input validated:
- Pydantic schemas for API
- Type checking
- Length limits
- Whitelist where possible
- Reject unexpected fields

SQL injection:
- SQLAlchemy ORM (parameterized queries)
- No raw SQL with user input
- No string concatenation

XSS:
- Output encoding (Jinja2 auto-escape if used)
- Content Security Policy header
- No dangerouslySetInnerHTML equivalent

CSRF:
- SameSite cookies
- CSRF tokens for state-changing requests
- Double-submit cookie pattern

---

## 6. API Security

Rate limiting:
- Per IP, per user, per endpoint
- Redis-backed
- Progressive backoff

API keys:
- Per tenant, scoped
- Rotatable
- Stored hashed
- Revocable

CORS:
- Explicit whitelist
- No wildcard in production
- Credentials allowed only for known origins

Headers:
- X-Content-Type-Options: nosniff
- X-Frame-Options: SAMEORIGIN
- Referrer-Policy: strict-origin-when-cross-origin
- Strict-Transport-Security
- Content-Security-Policy

---

## 7. Payment Security

PCI-DSS compliance:
- Never store card numbers
- Never store CVV
- Only store tokens from provider
- Provider handles card data (hosted fields or redirect)

Payment flow:
- Client gets session token from backend
- Client submits card directly to provider
- Provider returns token
- Backend charges via token

Webhook verification:
- Signature validation (HMAC)
- IP whitelist where possible
- Idempotency key per event

Fraud prevention:
- 3D Secure when supported
- Velocity limits (same card, IP, device)
- Manual review for large amounts

---

## 8. Infrastructure Security

Server hardening:
- SSH key-only (no passwords)
- Fail2ban for brute force
- Firewall (UFW or iptables)
- Regular security updates (unattended-upgrades)
- No unnecessary services

Database:
- Not exposed to internet
- Local-only connection
- Strong passwords
- Separate user per service

Secrets management:
- Environment variables
- Never in git
- Rotated regularly
- Separate per environment (dev, staging, prod)

---

## 9. Monitoring & Logging

Logs:
- Structured JSON
- No sensitive data (passwords, tokens, cards)
- Centralized (Loki or self-hosted)
- Retention: 90 days

Alerts:
- Failed login spike
- Unusual admin actions
- API error rate spike
- Database slow queries
- Disk/RAM/CPU thresholds

Incident response:
- Runbook for common incidents
- Contact list
- Post-mortem after incidents

---

## 10. Compliance

UAE PDPL (Personal Data Protection Law):
- Consent for data collection
- Data subject rights
- Breach notification within 72 hours
- Data processing agreement with tenants

GDPR (for EU users):
- Same principles apply
- Right to be forgotten
- Data portability

PCI-DSS:
- Provider handles card data
- We are SAQ-A compliant
- Annual attestation

---

## 11. Security in Development

Code review:
- Every PR reviewed
- Security checklist
- No direct commits to main

Dependencies:
- Pinned versions
- Weekly vulnerability scan (Dependabot or similar)
- Update policy: critical within 24h, high within 7 days

Testing:
- Security tests in CI
- OWASP Top 10 coverage
- Penetration testing annually

---

## 12. Backup Security

Encrypted:
- AES-256
- Separate key from main DB

Access:
- Backup access logged
- Only platform admins
- Restore tested quarterly

Retention:
- Daily: 7 days
- Weekly: 30 days
- Monthly: 12 months

---

## 13. Third-Party Services

Payment providers:
- Telr, Stripe, PayTabs, Checkout.com
- All PCI-DSS certified

Email/WhatsApp:
- SendGrid, Twilio, WhatsApp Business API
- No sensitive data in messages

Cloud/VPS:
- Reputable provider
- DDoS protection
- Regular security advisories

AI providers (Phase 7):
- OpenAI or Anthropic
- No PII sent without consent
- Data processing agreement in place

---

## 14. Security Checklist (Before Launch)

- [ ] HTTPS everywhere (no HTTP fallback)
- [ ] HSTS enabled
- [ ] All secrets in .env
- [ ] No secrets in git history
- [ ] Rate limiting on auth
- [ ] Session tokens hashed
- [ ] Passwords hashed (argon2/bcrypt)
- [ ] SQL injection tested
- [ ] XSS tested
- [ ] CSRF tokens
- [ ] CORS whitelist
- [ ] Security headers
- [ ] Firewall enabled
- [ ] SSH keys only
- [ ] Auto-updates enabled
- [ ] Backups encrypted + tested
- [ ] Monitoring active
- [ ] Alerts configured
- [ ] Incident runbook ready
- [ ] Privacy policy + terms
- [ ] Data processing agreement
- [ ] Penetration test done

---

Last updated: September 2026
Status: Living document.
