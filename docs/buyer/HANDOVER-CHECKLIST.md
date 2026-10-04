# Platform-X — Handover Checklist

## What the buyer receives
- Full source code (git repo, 60+ tags)
- docs/ (18+ files: strategy + technical + operational)
- scripts/deploy/ (install/update/backup/restore)
- scripts/smoke_test.sh
- 1487 automated tests
- .env.example (all variables, commented)
- deploy/ (systemd + nginx samples)
- LICENSE (custom, proprietary)

## What the buyer provides
- VPS (Ubuntu 22.04, 2 vCPU, 4 GB RAM)
- Domain name
- Payment provider account (Telr / Stripe)
- AI provider key (Gemini / OpenAI / Anthropic)
- SSL (Let's Encrypt — free)

## Steps at handover
1. Seller: tag `v1.0.0-sale-ready`, final backup
2. Seller: transfer repo ownership (GitHub/GitLab)
3. Buyer: clone repo to their VPS
4. Buyer: run scripts/deploy/install.sh <domain> <repo_url>
5. Buyer: fill .env
6. Buyer: run migrations + seeds
7. Buyer: start service, run smoke test
8. Buyer: issue SSL via certbot
9. Seller: rotate any secrets in the seller's own accounts
10. Buyer: confirm smoke test passes

## What is NOT included
- Seller's production secrets
- Seller's demo data
- Seller's third-party accounts
- Hands-on support (available as paid engagement)

## Post-handover support (optional, paid)
- Activation service: 24-48h deployment on buyer's VPS
- Training session: business panel + admin walkthrough
- Customization: white-label, new languages, new AI features
