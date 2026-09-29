#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — Fast project backup.
# Usage:
#   bash scripts/backup.sh <label>
# Example:
#   bash scripts/backup.sh phase-23-step-3-done
#
# Produces: backups/<label>-<timestamp>.tar.gz
# Fast because: gzip -1 + explicit paths + excludes.

set -e

LABEL="${1:?usage: bash scripts/backup.sh <label>}"
TS="$(date +%Y%m%d-%H%M%S)"
OUT="backups/${LABEL}-${TS}.tar.gz"
mkdir -p backups

# Important: explicit top-level paths (not '.') so we don't drag in
# .pytest_cache, .git, venv, logs, backups, .mypy_cache, etc.
PATHS=(
  app
  tests
  alembic
  scripts
  docs
  HANDOFF.md
  PROJECT-RULES.md
  WORKING-METHOD.md
  AI-CONTEXT.md
  README.md
  Makefile
  alembic.ini
  pytest.ini
  requirements.txt
  .env.example
  .gitignore
  DEPLOYMENT.md
  SECRETS.md
  WHERE-WE-ARE.md
)

# Keep only paths that exist
EXISTING=()
for p in "${PATHS[@]}"; do
  [ -e "$p" ] && EXISTING+=("$p")
done

tar \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='.mypy_cache' \
  --exclude='.ruff_cache' \
  --exclude='.coverage' \
  -I 'gzip -1' \
  -cf "$OUT" \
  "${EXISTING[@]}"

SIZE=$(du -h "$OUT" | cut -f1)
echo "BACKUP: $OUT  ($SIZE)"
