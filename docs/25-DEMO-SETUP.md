# Platform-X — Demo Setup Guide

> **Purpose:** Show Platform-X to a prospective buyer without
> purchasing production infrastructure.
>
> **Three options, in order of increasing cost and permanence:**
> 1. Local demo (Termux) with a temporary public URL via Cloudflare Tunnel — free.
> 2. Cheap VPS (Hetzner CX22 or equivalent) — ~EUR 4/month.
> 3. Full production deployment on the buyer's own VPS (see
>    `docs/buyer/DEPLOY-GUIDE.md`).

---

## 1. What a demo needs to show

Minimum viable demo:

- Landing / login page
- Tenant list (`/tenants`)
- A tenant's services (`/services?tenant_id=...`)
- Booking flow (search → intent → confirmation)
- Rewards ledger
- Business dashboard
- One AI feature (pricing coach or content writer)

Do not show:
- Payment checkout with real provider (Stripe is test-mode only
  unless the seller configures a test account)
- Admin panel with real passwords
- `.env` contents

---

## 2. Option 1 — Local demo via Cloudflare Tunnel (free)

### 2.1 Prerequisites

- Termux with Python 3.13 and PostgreSQL running (as set up in
  `docs/21-PG-VERIFICATION.md`).
- `cloudflared` installed.

Install cloudflared in Termux:

    pkg install cloudflared

If not available:

    pkg install wget
    wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -O $PREFIX/bin/cloudflared
    chmod +x $PREFIX/bin/cloudflared

### 2.2 Start the app

    cd ~/platform-x
    source venv/bin/activate
    export DATABASE_URL="postgresql+pg8000://platformx:testpass123@localhost:5432/platform_x"
    uvicorn app.main:app --host 127.0.0.1 --port 8000

Leave this running.

### 2.3 Open the public tunnel (in a second Termux session)

    cloudflared tunnel --url http://localhost:8000

Cloudflare prints a URL like:

    https://random-words-1234.trycloudflare.com

Share that URL with the buyer.

**Important:** the URL only works while both commands are running.
If the phone sleeps or Termux closes, the URL stops working.

### 2.4 Duration

For a live demo call: 30–60 minutes.
For asynchronous review: leave running for as long as practical.

---

## 3. Option 2 — Cheap VPS (recommended for serious demos)

### 3.1 Choose a provider

- **Hetzner Cloud CX22** — EUR ~4/month, 2 vCPU, 4 GB RAM, 40 GB SSD.
- **Contabo VPS S** — EUR ~4.5/month, 4 vCPU, 8 GB RAM.
- **Oracle Cloud Free Tier** — free forever, 4 vCPU, 24 GB RAM
  (signup is difficult).

### 3.2 Provision

Choose **Ubuntu 22.04**. Minimum specs as above.

### 3.3 Deploy Platform-X

    ssh root@<vps-ip>
    apt update && apt install -y git python3.13 python3.13-venv postgresql nginx
    git clone <repo-url> /opt/platform-x
    cd /opt/platform-x
    bash scripts/deploy/install.sh <your-domain> <repo-url>

Follow the prompts. Then:

    systemctl status platform-x
    curl http://localhost:8000/health

### 3.4 Domain + SSL

Point a DNS A record to the VPS IP. Then:

    certbot --nginx -d demo.yourdomain.com

### 3.5 Duration

Permanent until the VPS is deleted. Cost: ~EUR 4/month.

---

## 4. Option 3 — Screenshots and video only

If neither option above is feasible:

1. Take clean screenshots of each key page (see §1 list).
2. Record a 3–5 minute screen capture walking through the flow.
3. Include the screenshots in the pitch deck (slide 5).
4. Send the video on request (hosted on private YouTube or Vimeo,
   link-only).

No public URL, no VPS required.

**Note:** a live URL converts better than screenshots. Use Option 1
or 2 for serious buyers.

---

## 5. Demo data

Before any demo, seed the database:

    cd ~/platform-x
    source venv/bin/activate
    export DATABASE_URL="postgresql+pg8000://platformx:testpass123@localhost:5432/platform_x"
    python -m app.scripts.seed_all

This creates:
- 20 tenants
- 19 services
- 1 platform admin (`admin@platformx.com` / `ChangeMe123!`)

**Change the admin password before any demo.** Anyone who sees the
login page and knows the default credentials can access the admin
panel.

For a more visually rich demo, add: booking history, rewards ledger
entries, and 2–3 sample reviews. These are not currently seeded and
must be created manually via the app.

---

## 6. Demo security checklist

Before sharing any public URL:

- [ ] Change the admin password from `ChangeMe123!` to something
      strong.
- [ ] `ENABLE_MOCK_PAYMENTS=true` (dev only, since no real provider
      is connected).
- [ ] `WEBHOOK_SIGNATURE_ENFORCED=true` (keep default).
- [ ] `CORS_ORIGINS` set to the demo URL, not `localhost`.
- [ ] Do not show `.env` on screen.
- [ ] Do not share the admin credentials with the buyer.
- [ ] After the demo, stop the Cloudflare Tunnel (Ctrl+C) or shut
      down the VPS.

---

## 7. Talking points during the demo

Follow the flow in `docs/24-PITCH-DECK.md`:

1. **Problem** — hospitality tech is 20 years behind.
2. **Show the product** — booking flow, rewards, dashboard.
3. **Show one AI feature** — pricing coach is the cleanest.
4. **Show multi-tenancy** — switch between two tenants.
5. **Show the admin panel** — without revealing credentials.
6. **Close on the roadmap** — 7 stages, all complete except Stage 7.

Do not overstate. If the buyer asks "is Stripe connected?" — answer
honestly: "Stripe signature verification is implemented and tested;
live account setup is buyer-driven."

---

## 8. After the demo

- Send the buyer a follow-up email summarizing what was shown.
- Attach the pitch deck (`docs/24-PITCH-DECK.md`) if not already sent.
- If the buyer wants deeper evaluation, send the NDA
  (`docs/19-NDA-TEMPLATE.md`).
- Log the demo in your outreach tracking sheet
  (`docs/26-OUTREACH-EMAILS.md` §Tracking).

---

## Document control

- **Version:** 1.0
- **Date:** 2026-10-16
- **Author:** Benjamin Bahoush (with AI assistance)
- **Status:** Ready

