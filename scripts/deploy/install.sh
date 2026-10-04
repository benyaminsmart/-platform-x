#!/usr/bin/env bash
# Platform-X — installer for Ubuntu 22.04 VPS.
# Usage: sudo bash scripts/deploy/install.sh <domain> <repo_url>
set -euo pipefail
DOMAIN="${1:?usage: install.sh <domain> <repo_url>}"
REPO_URL="${2:?usage: install.sh <domain> <repo_url>}"
APP_USER="platformx"; APP_DIR="/opt/platform-x"; LOG_DIR="/var/log/platform-x"
DB_NAME="platform_x"; DB_USER="platformx"; DB_PASS="$(openssl rand -hex 24)"
log() { printf "\n==> %s\n" "$*"; }
[[ $EUID -eq 0 ]] || { echo "run as root"; exit 1; }
log "1/8 packages"; apt-get update
apt-get install -y --no-install-recommends python3 python3-venv python3-pip postgresql postgresql-contrib nginx git curl openssl certbot python3-certbot-nginx ufw
log "2/8 user"; id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /bin/bash "$APP_USER"
mkdir -p "$APP_DIR" "$LOG_DIR"; chown -R "$APP_USER:$APP_USER" "$APP_DIR" "$LOG_DIR"
log "3/8 clone"; [[ -d "$APP_DIR/.git" ]] && sudo -u "$APP_USER" git -C "$APP_DIR" pull || sudo -u "$APP_USER" git clone "$REPO_URL" "$APP_DIR"
log "4/8 venv"; cd "$APP_DIR"; [[ -d venv ]] || sudo -u "$APP_USER" python3 -m venv venv
sudo -u "$APP_USER" ./venv/bin/pip install --upgrade pip wheel; sudo -u "$APP_USER" ./venv/bin/pip install -r requirements.txt
log "5/8 db"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 || sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 || sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
log "6/8 .env"; if [[ -f "$APP_DIR/.env" ]]; then echo "  exists"; else
  sudo -u "$APP_USER" cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  sudo -u "$APP_USER" sed -i "s|^DATABASE_URL=.*|DATABASE_URL=postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME|" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"; fi
echo "DB PASSWORD: $DB_PASS"
log "7/8 systemd+nginx"
cp "$APP_DIR/deploy/platform-x.service" /etc/systemd/system/platform-x.service
systemctl daemon-reload; systemctl enable platform-x
sed "s|your-domain.example|$DOMAIN|g" "$APP_DIR/deploy/nginx.conf" > /etc/nginx/sites-available/platform-x
ln -sf /etc/nginx/sites-available/platform-x /etc/nginx/sites-enabled/platform-x
rm -f /etc/nginx/sites-enabled/default; nginx -t; systemctl reload nginx
log "8/8 firewall"; ufw allow OpenSSH; ufw allow 'Nginx Full'; ufw --force enable
cat <<NEXT

=== INSTALL COMPLETE ===
Next:
1. Edit $APP_DIR/.env  (SECRET_KEY, CORS_ORIGINS, AI_API_KEY)
2. cd $APP_DIR && sudo -u $APP_USER ./venv/bin/alembic upgrade head
3. sudo -u $APP_USER ./venv/bin/python -m app.scripts.seed_all
4. sudo systemctl start platform-x
5. sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN
6. curl -sSf https://$DOMAIN/health
NEXT
