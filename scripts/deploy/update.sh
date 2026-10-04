#!/usr/bin/env bash
# Platform-X — update an existing deployment.
# Usage: sudo bash scripts/deploy/update.sh [git_ref]
set -euo pipefail
APP_USER="platformx"; APP_DIR="/opt/platform-x"; REF="${1:-main}"
cd "$APP_DIR"
sudo -u "$APP_USER" git fetch --all --tags
sudo -u "$APP_USER" git checkout "$REF"
sudo -u "$APP_USER" git pull --ff-only || true
sudo -u "$APP_USER" ./venv/bin/pip install -r requirements.txt
sudo -u "$APP_USER" ./venv/bin/alembic upgrade head
systemctl restart platform-x
sleep 2
systemctl --no-pager status platform-x | head -8
echo "UPDATE DONE: $REF"
