#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — Build a delivery package for a buyer.
#
# Usage: bash scripts/package-delivery.sh [output-zip-path]
#
# Excludes: .env, *.db, venv/, backups/, logs/, .git/, caches.
# Includes: source, tests, docs, scripts, LICENSE, AUTHORS, etc.

set -euo pipefail

cd ~/platform-x
VERSION=$(git describe --tags --abbrev=0)
DATE=$(date +%Y%m%d-%H%M%S)
OUTPUT="${1:-$HOME/platform-x-delivery-${VERSION}-${DATE}.zip}"
STAGE=$(mktemp -d)

echo "=== Package Platform-X delivery ==="
echo "version: $VERSION"
echo "output:  $OUTPUT"
echo "staging: $STAGE"
echo ""

# --- Copy the repo, excluding sensitive/large dirs (no rsync) ---
echo "-> copying with exclusions (no rsync available)"
mkdir -p "$STAGE/platform-x"
cd ~/platform-x

find . -mindepth 1 -maxdepth 1 \
  ! -name '.env' \
  ! -name '.git' \
  ! -name '.pytest_cache' \
  ! -name 'venv' \
  ! -name '.venv' \
  ! -name 'backups' \
  ! -name 'logs' \
  ! -name '*.db' \
  -exec cp -r {} "$STAGE/platform-x/" \;

# --- Remove nested .env, *.db, caches, __pycache__ inside staged tree ---
find "$STAGE/platform-x" -name '.env' -delete 2>/dev/null || true
find "$STAGE/platform-x" -name '*.db' -delete 2>/dev/null || true
find "$STAGE/platform-x" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find "$STAGE/platform-x" -name '*.pyc' -delete 2>/dev/null || true

# --- Sanity checks ---
echo "-> sanity checks"

if [ -f "$STAGE/platform-x/.env" ]; then
  echo "!! .env leaked — abort"
  rm -rf "$STAGE"; exit 1
fi
if find "$STAGE/platform-x" -name '*.db' | grep -q .; then
  echo "!! .db leaked — abort"
  rm -rf "$STAGE"; exit 1
fi
if [ -d "$STAGE/platform-x/backups" ]; then
  echo "!! backups/ leaked — abort"
  rm -rf "$STAGE"; exit 1
fi
if [ -d "$STAGE/platform-x/.git" ]; then
  echo "!! .git/ leaked — abort"
  rm -rf "$STAGE"; exit 1
fi

echo "OK — no secrets, databases, or git history in staging"

# --- Delivery README ---
cat > "$STAGE/platform-x/DELIVERY-README.md" <<EOF
# Platform-X — Delivery Package

Version: $VERSION
Packaged: $DATE

This package contains the complete Platform-X platform, prepared
for buyer evaluation and transfer.

## What is in here

- Source code (app/)
- Tests (tests/)
- Documentation (docs/, docs/buyer/)
- Deployment scripts (scripts/, deploy/)
- Database migrations (alembic/)
- HANDOFF.md (project state)
- CHANGELOG.md, LICENSE, AUTHORS.md
- Sales materials (docs/17-INVESTMENT-MEMO.md,
  docs/18-SALE-AGREEMENT.md, docs/19-NDA-TEMPLATE.md,
  docs/22-VALUATION-DEFENSE.md, docs/23-TARGET-BUYERS.md,
  docs/24-PITCH-DECK.md, docs/26-OUTREACH-EMAILS.md,
  docs/27-DATA-ROOM.md)

## What is NOT in here

- .env (secrets)
- Database files (*.db)
- Backups
- Virtual environments
- Logs
- Git history

## How to verify

1. Create a fresh Python 3.13 virtual environment.
2. pip install -r requirements.txt
3. Create your own .env from .env.example
4. pytest tests/ -n auto
   Expected: 1,509 tests passing in ~60 seconds.
5. bash scripts/verify-handoff.sh

## Contact

Benjamin Bahoush — platformx2026@gmail.com
EOF

# --- Build zip ---
echo "-> creating zip (this may take a moment)"
cd "$STAGE"

if command -v zip >/dev/null 2>&1; then
  zip -rq "$OUTPUT" platform-x
else
  echo "!! zip not installed. Trying tar.gz fallback..."
  OUTPUT="${OUTPUT%.zip}.tar.gz"
  tar -czf "$OUTPUT" platform-x
fi

cd ~/platform-x

# --- Report ---
SIZE=$(du -h "$OUTPUT" | cut -f1)
if command -v sha256sum >/dev/null 2>&1; then
  SHA=$(sha256sum "$OUTPUT" | cut -d' ' -f1)
else
  SHA="(sha256sum not available)"
fi

echo ""
echo "=== DONE ==="
echo "output: $OUTPUT"
echo "size:   $SIZE"
echo "sha256: $SHA"

rm -rf "$STAGE"
