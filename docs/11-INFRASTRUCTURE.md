# Platform-X — Infrastructure

> Servers, deployment, CI/CD, monitoring.

---

## 1. Environments

Development:
- Local: Termux on Android
- Database: SQLite
- No external services
- Hot reload

Staging:
- VPS mirror of production
- Database: PostgreSQL
- Full stack deployed
- Used for testing before production

Production:
- VPS (or multiple)
- Database: PostgreSQL (managed if possible)
- CDN for static assets
- Monitoring active

---

## 2. Server Stack

Operating System: Ubuntu 22.04 LTS

Backend:
- Python 3.13
- FastAPI
- Uvicorn (ASGI server)
- Gunicorn (process manager) — optional

Web Server:
- Nginx (reverse proxy + static files)
- SSL via Let's Encrypt (certbot)

Database:
- PostgreSQL 16
- Managed service preferred (AWS RDS, DigitalOcean Managed DB) — Phase 3+
- Self-hosted on same VPS — Phase 1

Cache / Queue:
- Redis (Phase 3+)
- Used for sessions, rate limiting, background jobs

Background Jobs:
- Celery (with Redis broker) — Phase 3+
- Used for: notifications, reports, AI processing

---

## 3. VPS Recommendations

Phase 1 (single server):
- 2 vCPU
- 4 GB RAM
- 80 GB NVMe SSD
- Cost: ~$10-15/month

Phase 2-3 (growing):
- 4 vCPU
- 8 GB RAM
- 160 GB NVMe SSD
- Separate DB server (optional)
- Cost: ~$25-40/month

Phase 4+ (scaling):
- Load balancer
- 2+ app servers
- Managed database
- Redis cluster
- CDN

Providers considered:
- Hetzner (Europe, cheap, reliable)
- DigitalOcean (global, easy)
- Vultr (Dubai location)
- AWS / GCP (enterprise)

Decision: Start with Hetzner or DigitalOcean.

---

## 4. Deployment Process

Manual (Phase 1):
- Git pull on server
- Install dependencies
- Restart service
- Test

Automated (Phase 2+):
- CI/CD pipeline (GitHub Actions or GitLab CI)
- Tests run on push
- Auto-deploy to staging on merge to develop
- Manual approval for production
- Zero-downtime deploy (blue-green or rolling)

---

## 5. CI/CD Pipeline

Stages:
1. Lint (ruff, black)
2. Type check (mypy)
3. Unit tests (pytest)
4. Integration tests
5. Build (if frontend)
6. Deploy to staging
7. Smoke tests on staging
8. Manual approval
9. Deploy to production
10. Post-deploy health check

Tools:
- GitHub Actions (preferred)
- Or GitLab CI

---

## 6. Monitoring

Uptime:
- UptimeRobot or Better Stack
- Check every 1-5 minutes
- Alert on 2 consecutive failures

Error tracking:
- Sentry
- Captures backend + frontend errors
- Alerts on new error types

Metrics:
- Prometheus + Grafana (Phase 3+)
- CPU, memory, disk, requests, latency
- Custom business metrics

Logs:
- Structured JSON
- Centralized (Loki or self-hosted ELK)
- Retention: 90 days
- Search + alerting

Alerts:
- Slack or Telegram channel
- On-call rotation (when team grows)
- PagerDuty (Phase 4+)

---

## 7. Backup Strategy

Database:
- Daily full dump at 3:00 AM
- Weekly archive (Sunday)
- Monthly archive (1st of month)
- Stored in separate location (S3, Backblaze B2)
- Encrypted with AES-256

Files:
- Static assets: git + weekly backup
- User uploads: daily sync to object storage

Recovery:
- RPO: 24 hours
- RTO: 2 hours
- Restore tested quarterly

---

## 8. Security (Infrastructure)

Firewall:
- UFW (Ubuntu) or cloud firewall
- Only 22 (SSH), 80, 443 open
- SSH key only

SSH:
- Port changed (optional)
- Fail2ban for brute force
- Key-only auth
- No root login

Updates:
- unattended-upgrades for security patches
- Monthly manual review for feature updates

SSL:
- Let's Encrypt via certbot
- Auto-renewal every 60 days
- Monitoring for expiry

---

## 9. Scaling Strategy

Vertical (Phase 1-2):
- Bigger VPS
- More CPU/RAM

Horizontal (Phase 3+):
- Multiple app servers
- Load balancer (Nginx or HAProxy)
- Session store in Redis (shared)
- Static files on CDN

Database scaling (Phase 4+):
- Read replicas
- Connection pooling (PgBouncer)
- Partitioning large tables

Caching (Phase 3+):
- Redis for hot data
- CDN for static assets
- Application-level caching

---

## 10. Cost Estimation

Phase 1 (single tenant):
- VPS: $10-15/month
- Domain: $10/year
- SSL: Free (Let's Encrypt)
- Backups: $2-5/month
- Total: ~$15-20/month

Phase 2-3 (10-50 tenants):
- VPS: $25-40/month
- Managed database: $15-30/month
- Redis: $10/month
- CDN: $5-10/month
- Monitoring: $0-20/month
- Total: ~$60-100/month

Phase 4+ (100+ tenants):
- 2-4 app servers: $80-160/month
- Managed DB: $50-100/month
- Redis cluster: $30-50/month
- CDN: $20-40/month
- Monitoring: $30-50/month
- Total: ~$200-400/month

---

## 11. Deployment Checklist (Pre-Launch)

- [ ] Server provisioned
- [ ] OS updated
- [ ] Firewall configured
- [ ] SSH keys set up
- [ ] Fail2ban installed
- [ ] Auto-updates enabled
- [ ] Nginx installed + configured
- [ ] Python + venv + dependencies
- [ ] PostgreSQL installed + configured
- [ ] Redis installed + configured (Phase 3+)
- [ ] Certbot + SSL certificate
- [ ] DNS configured
- [ ] systemd services for backend
- [ ] Log rotation configured
- [ ] Backups scheduled + tested
- [ ] Monitoring configured
- [ ] Alerts configured
- [ ] Environment variables in .env
- [ ] Secrets not in git
- [ ] Health check endpoint working
- [ ] Smoke tests passed

---

Last updated: September 2026
Status: Living document.
