#!/usr/bin/env bash
# Platform-X — restore from a backup archive.
# Usage: sudo bash scripts/deploy/restore.sh <archive.tar.gz>
set -euo pipefail
ARCHIVE="${1:?usage: restore.sh <archive.tar.gz>}"
APP_DIR="${APP_DIR:-/opt/platform-x}"
[[ -f "$ARCHIVE" ]] || { echo "not found: $ARCHIVE"; exit 1; }
echo "WARNING: overwrites DB and .env. Ctrl-C in 5s to abort."; sleep 5
TMP="$(mktemp -d)"; tar -xzf "$ARCHIVE" -C "$TMP"
DB_URL="$(grep -E '^DATABASE_URL=' "$TMP/.env" | cut -d= -f2-)"
if [[ -f "$TMP/db.sql" ]]; then
    sudo -u postgres psql "$(echo "$DB_URL" | sed 's|.*/||')" < "$TMP/db.sql"
elif [[ -f "$TMP/db.sqlite" ]]; then
    cp "$TMP/db.sqlite" "${DB_URL#sqlite:///}"
fi
cp "$TMP/.env" "$APP_DIR/.env"; chmod 600 "$APP_DIR/.env"
[[ -d "$TMP/uploads" ]] && cp -r "$TMP/uploads" "$APP_DIR/app/static/" || true
rm -rf "$TMP"; systemctl restart platform-x
echo "RESTORE DONE from $ARCHIVE"
