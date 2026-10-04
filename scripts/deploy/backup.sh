#!/usr/bin/env bash
# Platform-X — backup DB + .env + uploads.
# Usage: bash scripts/deploy/backup.sh [label]
set -euo pipefail
APP_DIR="${APP_DIR:-/opt/platform-x}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/platform-x}"
LABEL="${1:-auto}"; TS="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
OUT="$BACKUP_DIR/platformx-${LABEL}-${TS}.tar.gz"
DB_URL="$(grep -E '^DATABASE_URL=' "$APP_DIR/.env" | cut -d= -f2-)"
TMP="$(mktemp -d)"
if [[ "$DB_URL" == postgresql* ]]; then
    sudo -u postgres pg_dump "$(echo "$DB_URL" | sed 's|.*/||')" > "$TMP/db.sql"
elif [[ "$DB_URL" == sqlite* ]]; then
    cp "${DB_URL#sqlite:///}" "$TMP/db.sqlite"
fi
cp "$APP_DIR/.env" "$TMP/.env"
[[ -d "$APP_DIR/app/static/uploads" ]] && cp -r "$APP_DIR/app/static/uploads" "$TMP/uploads" || true
tar -czf "$OUT" -C "$TMP" .
rm -rf "$TMP"
ls -1t "$BACKUP_DIR"/platformx-*.tar.gz | tail -n +15 | xargs -r rm -f
SIZE="$(du -h "$OUT" | cut -f1)"
echo "BACKUP: $OUT ($SIZE)"
