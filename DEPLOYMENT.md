# Platform-X — Deployment Guide

> Complete deployment checklist for taking Platform-X to production.

## Pre-deployment checklist

- [ ] All tests pass (`pytest`)
- [ ] No uncommitted changes (`git status`)
- [ ] All secrets set (see SECRETS.md)
- [ ] APP_ENV=production
- [ ] APP_DEBUG=false
- [ ] SECRET_KEY is strong (64+ chars)
- [ ] DATABASE_URL points to PostgreSQL
- [ ] CORS_ORIGINS contains only real domain(s)
- [ ] ENABLE_MOCK_PAYMENTS=false
- [ ] SSL certificate installed (Let's Encrypt)
- [ ] DNS configured
- [ ] Cloudflare named tunnel set up (or Nginx reverse proxy)

## Steps

1. Provision VPS (Ubuntu 22.04+)
2. Install system packages:
   apt update && apt upgrade -y
   apt install -y python3 python3-venv python3-pip nginx postgresql certbot python3-certbot-nginx

3. Create PostgreSQL database and user
4. Clone the repository
5. Create venv and install requirements
6. Set environment variables (production values)
7. Run Alembic migrations: alembic upgrade head
8. Start Gunicorn/Uvicorn behind Nginx
9. Configure Nginx reverse proxy
10. Issue SSL certificate: certbot --nginx
11. Configure systemd service for auto-restart
12. Set up daily backup cron
13. Test all critical flows
14. Monitor logs for 24 hours

## Nginx config (example)

server {
    listen 443 ssl http2;
    server_name platform-x.com;

    ssl_certificate /etc/letsencrypt/live/platform-x.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/platform-x.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8030;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

## Health checks

- GET /health — returns {"status": "ok"}
- Monitor response time and status code

## Rollback plan

1. Stop the service
2. Revert to previous Git tag: git checkout v0.4.0-full-flow
3. Run migrations down if needed: alembic downgrade -1
4. Restart the service
5. Verify health endpoint

## Post-deployment

- [ ] Enable uptime monitoring
- [ ] Enable error tracking (Sentry or similar)
- [ ] Set up log rotation
- [ ] Document incident response
- [ ] Schedule weekly security audit
