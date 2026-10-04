# Platform-X — Deploy Guide (30 minutes)

> Short guide. Full checklist in `docs/DEPLOY-CHECKLIST.md`.

## Requirements
- Ubuntu 22.04 VPS (2 vCPU, 4 GB RAM, 20 GB SSD)
- Domain pointing to the VPS IP
- SSH root or sudo access

## Steps
1. SSH to the VPS.
2. Run the installer:
   sudo bash scripts/deploy/install.sh <domain> <repo_url>
3. Fill the environment file:
   sudo -u platformx nano /opt/platform-x/.env
   - SECRET_KEY  -> python3 -c "import secrets; print(secrets.token_urlsafe(48))"
   - CORS_ORIGINS=["https://<domain>"]
   - AI_API_KEY (if using a real provider)
   - ENABLE_MOCK_PAYMENTS=false
4. Run migrations + seeds:
   cd /opt/platform-x
   sudo -u platformx ./venv/bin/alembic upgrade head
   sudo -u platformx ./venv/bin/python -m app.scripts.seed_all
5. Start service:
   sudo systemctl start platform-x && sudo systemctl status platform-x
6. SSL:
   sudo certbot --nginx -d <domain> -d www.<domain>
7. Smoke test:
   bash scripts/smoke_test.sh https://<domain>

## Time budget
- Server prep: 5 min
- Install + clone: 5 min
- PostgreSQL: 5 min
- .env: 2 min
- Migrations + seed: 2 min
- Systemd + nginx: 5 min
- SSL: 3 min
- Smoke test: 2 min
Total: ~30 min
