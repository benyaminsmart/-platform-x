# Platform-X — Deploy Checklist (VPS + Domain)

> Step-by-step guide to get Platform-X live on Ubuntu 22.04 VPS.
> Total time: ~45 minutes.

## 0. Prerequisites
- Ubuntu 22.04 LTS VPS (2 vCPU / 4 GB RAM / 20 GB)
- Domain pointing to VPS IP
- SSH access
- Git repo URL

## 1. Server prep (5 min)
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.13 python3.13-venv python3-pip postgresql postgresql-contrib nginx git ufw certbot python3-certbot-nginx
sudo ufw allow OpenSSH && sudo ufw allow 'Nginx Full' && sudo ufw --force enable

## 2. Service user (1 min)
sudo useradd --system --create-home --shell /bin/bash platformx
sudo mkdir -p /opt/platform-x /var/log/platform-x
sudo chown -R platformx:platformx /opt/platform-x /var/log/platform-x

## 3. Clone (2 min)
sudo -u platformx git clone <YOUR_REPO_URL> /opt/platform-x
cd /opt/platform-x
sudo -u platformx python3.13 -m venv venv
sudo -u platformx ./venv/bin/pip install --upgrade pip
sudo -u platformx ./venv/bin/pip install -r requirements.txt

## 4. PostgreSQL (5 min)
sudo -u postgres psql -c "CREATE USER platformx WITH PASSWORD 'CHANGE_ME_STRONG';"
sudo -u postgres psql -c "CREATE DATABASE platform_x OWNER platformx;"
psql "postgresql://platformx:CHANGE_ME_STRONG@localhost:5432/platform_x" -c "SELECT 1;"

## 5. Environment file (2 min)
cd /opt/platform-x
sudo -u platformx cp .env.example .env
sudo -u platformx nano .env
# Fill: DATABASE_URL, SECRET_KEY, APP_ENV=production, APP_DEBUG=false,
#       ENABLE_MOCK_PAYMENTS=false, CORS_ORIGINS, AI_API_KEY
sudo chmod 600 /opt/platform-x/.env

## 6. Migrations (1 min)
sudo -u platformx ./venv/bin/alembic upgrade head

## 7. Seed base data (1 min)
sudo -u platformx ./venv/bin/python -m app.scripts.seed_all
sudo -u platformx ./venv/bin/python -m app.scripts.seed_reward_rules
sudo -u platformx ./venv/bin/python -m app.scripts.seed_redeem_options

## 8. systemd (2 min)
sudo cp /opt/platform-x/deploy/platform-x.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now platform-x
sudo systemctl status platform-x

## 9. Nginx (3 min)
sudo cp /opt/platform-x/deploy/nginx.conf /etc/nginx/sites-available/platform-x
sudo nano /etc/nginx/sites-available/platform-x
sudo ln -s /etc/nginx/sites-available/platform-x /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

## 10. SSL (3 min)
sudo certbot --nginx -d your-domain.example -d www.your-domain.example

## 11. Smoke test (2 min)
curl -sSf https://your-domain.example/health
# Then in browser: register -> search -> book -> pay -> check /account/wallet

## 12. Backups (5 min)
# Add to platformx crontab:
# 0 3 * * * /opt/platform-x/scripts/deploy/backup.sh >> /var/log/platform-x/backup.log 2>&1

## 13. Monitoring (optional)
- Uptime: UptimeRobot / BetterStack
- Logs: journalctl -u platform-x -f
- Metrics: /metrics (Prometheus) if enabled

## 14. First business tenant (optional)
1. Login as platform admin: /platform/login
2. Approve tenant application
3. Send business owner their tenant URL

## Troubleshooting
| Symptom | Cause | Fix |
|---------|-------|-----|
| 502 Bad Gateway | Uvicorn not running | systemctl restart platform-x |
| Connection refused | bad HOST/PORT | check .env |
| permission denied on DB | bad DATABASE_URL | check .env |
| SSL fails | DNS not propagated | wait 30 min, retry certbot |
| Empty pages | migrations not run | alembic upgrade head |

## Rollback
cd /opt/platform-x
sudo -u platformx git checkout <last-good-tag>
sudo -u platformx ./venv/bin/alembic downgrade -1
sudo systemctl restart platform-x

*End of checklist.*
