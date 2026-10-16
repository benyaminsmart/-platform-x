# Platform-X — Buyer Activation Checklist

> **Purpose:** The complete list of accounts, keys, and services the
> buyer must provision with their own credentials before the platform
> goes live. Everything here is buyer-driven; the seller provides none
> of these.
>
> **Estimated time to complete:** 1–3 working days (mostly waiting on
> external signups).
>
> **Date:** 2026-10-16

---

## 1. Infrastructure (must-have before deploy)

### 1.1 VPS (Virtual Private Server)

- [ ] Choose provider:
  - **Hetzner Cloud CX22** — EUR ~4/month, 2 vCPU / 4 GB RAM / 40 GB SSD (recommended)
  - **Contabo VPS S** — EUR ~4.5/month, 4 vCPU / 8 GB RAM
  - **Oracle Cloud Free Tier** — free forever, 4 vCPU / 24 GB RAM (signup is difficult)
  - **DigitalOcean Droplet** — USD 6/month, 1 vCPU / 1 GB RAM (dev only)
- [ ] Provision Ubuntu 22.04 LTS
- [ ] Note the IP address
- [ ] Set up SSH key access
- [ ] Configure firewall (allow 22, 80, 443 only)

### 1.2 Domain

- [ ] Register a domain (Namecheap, GoDaddy, Cloudflare)
- [ ] Note the DNS provider's nameservers
- [ ] Create an A record pointing to the VPS IP
- [ ] Wait for DNS propagation (up to 48 hours; usually 15 min)

### 1.3 SSL certificate

- [ ] Nothing to purchase — Let's Encrypt is free.
- [ ] After deploy, run: `certbot --nginx -d yourdomain.com`
- [ ] Certbot auto-renews (verify: `systemctl status certbot.timer`)

---

## 2. Payment provider (choose one or more)

### 2.1 Stripe (recommended for international)

- [ ] Register at https://dashboard.stripe.com/register
- [ ] Complete KYC (ID, business details, bank account)
- [ ] Get API keys (Developers → API keys):
  - [ ] `STRIPE_SECRET_KEY` (`sk_live_...` or `sk_test_...`)
  - [ ] Publishable key (for frontend, if used)
- [ ] Set up webhook endpoint:
  - URL: `https://yourdomain.com/payments/webhook/stripe`
  - Events: `payment_intent.succeeded`, `payment_intent.payment_failed`
  - Copy the signing secret → `STRIPE_WEBHOOK_SECRET`
- [ ] (Optional) Test with `stripe listen --forward-to localhost:8000/...`

### 2.2 Telr (recommended for MENA)

- [ ] Register at https://telr.com
- [ ] Complete KYC
- [ ] Get `TELR_STORE_ID` and `TELR_AUTH_KEY`
- [ ] Configure webhook URL: `https://yourdomain.com/payments/webhook/telr`
- [ ] Set `PAYMENT_WEBHOOK_SECRET` to the shared secret Telr provides
- [ ] (Optional) Sandbox account for testing before going live

### 2.3 PayTabs (alternative MENA)

- [ ] Register at https://paytabs.com
- [ ] Complete KYC
- [ ] Get merchant credentials
- [ ] Configure webhook URL

### 2.4 Common to all providers

- [ ] In `.env`, set `PAYMENT_PROVIDER=<stripe|telr|paytabs>`
- [ ] In `.env`, set `PAYMENT_WEBHOOK_SECRET` (generic secret)
- [ ] In `.env`, set `ENABLE_MOCK_PAYMENTS=false`
- [ ] In `.env`, set `WEBHOOK_SIGNATURE_ENFORCED=true`
- [ ] **Before going live:** write the Stripe event adapter (see
      `docs/20-PAYMENT-TEST-MODE.md` §5) or ask the seller (paid
      activation service).

---

## 3. AI provider (choose one or more)

### 3.1 Google Gemini

- [ ] Go to https://aistudio.google.com/app/apikey
- [ ] Create an API key
- [ ] In `.env`, set `AI_PROVIDER=gemini`
- [ ] In `.env`, set `GEMINI_API_KEY=<your-key>`
- [ ] Set usage limits in Google Cloud Console (recommended)

### 3.2 OpenAI

- [ ] Go to https://platform.openai.com/api-keys
- [ ] Create an API key
- [ ] In `.env`, set `AI_PROVIDER=openai`
- [ ] In `.env`, set `OPENAI_API_KEY=<your-key>`
- [ ] Set usage limits (recommended)

---

## 4. Email sending (for notifications)

### 4.1 Resend (recommended)

- [ ] Register at https://resend.com
- [ ] Verify your domain (DNS TXT records)
- [ ] Get API key
- [ ] In `.env`, set `RESEND_API_KEY=<your-key>`
- [ ] In `.env`, set `EMAIL_FROM=<noreply@yourdomain.com>`

### 4.2 Alternative

Platform-X uses Resend by default. Alternatives (SendGrid, Mailgun,
AWS SES) require code changes in `app/services/notification_service.py`.

---

## 5. Production secrets

Generate strong secrets (not the dev defaults):

- [ ] `SECRET_KEY` — JWT signing key, at least 48 random bytes:
      `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`
- [ ] Database password — strong, unique
- [ ] Admin password — change from `ChangeMe123!`

---

## 6. Database setup (on the VPS)

- [ ] Install PostgreSQL: `apt install postgresql postgresql-contrib`
- [ ] Create DB and user:
      ```
      sudo -u postgres psql
      CREATE USER platformx WITH PASSWORD '<strong-password>';
      CREATE DATABASE platform_x OWNER platformx;
      GRANT ALL PRIVILEGES ON DATABASE platform_x TO platformx;
      \q
      ```
- [ ] Update `.env`:
      `DATABASE_URL=postgresql://platformx:<strong-password>@localhost:5432/platform_x`
- [ ] Install driver: `pip install psycopg2-binary==2.9.9`
- [ ] Run migrations: `alembic upgrade head`
- [ ] Seed initial data: `python -m app.scripts.seed_all`

---

## 7. Email (domain verification)

- [ ] Add DNS records for your email provider (SPF, DKIM, DMARC)
- [ ] Verify the sending domain in your provider's dashboard
- [ ] Test sending from the platform

---

## 8. Monitoring and logging (optional but recommended)

### 8.1 Uptime monitoring

- [ ] Register at UptimeRobot, Better Stack, or similar
- [ ] Add a monitor for `https://yourdomain.com/health`
- [ ] Configure alerts (email, Slack)

### 8.2 Error tracking

- [ ] Register at Sentry (or similar)
- [ ] Get a DSN
- [ ] Set `SENTRY_DSN` in `.env` (SDK must be installed manually;
      Platform-X does not ship it to keep dependencies light)
- [ ] Alternative: use systemd journal + logrotate

### 8.3 Log aggregation

- [ ] Optional: ship logs to a central service (Papertrail, Datadog)

---

## 9. Backup automation

- [ ] Set up daily backup cron on the VPS:
      `0 3 * * * /opt/platform-x/scripts/deploy/backup.sh /var/backups/platform-x`
- [ ] Set up weekly off-site backup (rsync to S3, Backblaze B2, etc.)
- [ ] Verify: run `scripts/deploy/restore.sh` on a test machine
- [ ] Retention: 30 days minimum

---

## 10. Security hardening (on the VPS)

- [ ] Disable root SSH login: `PermitRootLogin no` in `/etc/ssh/sshd_config`
- [ ] Use SSH keys only (no password login)
- [ ] Install fail2ban: `apt install fail2ban`
- [ ] Configure UFW firewall: allow only 22, 80, 443
- [ ] Enable automatic security updates: `apt install unattended-upgrades`
- [ ] Set up a non-root user for the app
- [ ] Verify `ENABLE_MOCK_PAYMENTS=false`
- [ ] Verify `WEBHOOK_SIGNATURE_ENFORCED=true`

---

## 11. Hospitality operating licenses (per jurisdiction)

**This depends entirely on the buyer's geography and business model.**
Common requirements:

- [ ] Business license (per emirate in UAE, per municipality in KSA)
- [ ] Tourism license (from DTCM in Dubai, DCT in Abu Dhabi, etc.)
- [ ] Data residency compliance (if operating in KSA or serving
      government-linked operators)
- [ ] Local partner (if required by jurisdiction)
- [ ] Tax registration (VAT in UAE, KSA)

**Recommended:** engage local counsel before launch in each
jurisdiction.

---

## 12. Final pre-launch verification

Once everything above is done, run:

    cd /opt/platform-x
    source venv/bin/activate
    pytest tests/ -n auto
    # expected: 1509 passed, ~60s
    bash scripts/verify-handoff.sh
    # expected: 7/7 pass
    bash scripts/smoke_test.sh
    # expected: passes with demo data

Then visit:

- [ ] `https://yourdomain.com/health` → `{"status": "ok"}`
- [ ] `https://yourdomain.com/tenants` → returns seeded tenants
- [ ] `https://yourdomain.com/` → landing page loads
- [ ] Login as admin → change default password
- [ ] Create first tenant → configure branding → test booking flow

---

## 13. Payment end-to-end test (before going live)

- [ ] Use test mode first (Stripe test card `4242 4242 4242 4242`)
- [ ] Verify webhook is received (check server logs)
- [ ] Verify payment `status=success` in the database
- [ ] Switch to live mode
- [ ] Run a small real transaction
- [ ] Verify funds appear in the payment provider dashboard
- [ ] Refund the test transaction

---

## 14. Ongoing operations

After launch, the buyer is responsible for:

- [ ] Daily backups (automated)
- [ ] Weekly security updates
- [ ] Monthly review of logs
- [ ] Tenant onboarding
- [ ] Customer support
- [ ] Feature roadmap
- [ ] Marketing and sales

---

## 15. Seller support (handover period)

Per `docs/18-SALE-AGREEMENT.md`:

- The seller supports the buyer's team until the platform is declared
  live (not time-boxed).
- After go-live, emergency support only for seller-authored code, for
  12 months.
- Optional paid activation service: remote setup on the buyer's VPS.

---

## Document control

- **Version:** 1.0
- **Date:** 2026-10-16
- **Author:** Benjamin Bahoush (with AI assistance)
- **Status:** Ready for buyer
