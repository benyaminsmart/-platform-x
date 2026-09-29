#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — Full backup (code + DB + .env).
# Use at MILESTONES ONLY (slow). For step-by-step use scripts/backup.sh.
# Usage:
#   bash scripts/backup-full.sh <label>
# Example:
#   bash scripts/backup-full.sh v0.14.0-leaderboard

set -e

LABEL="${1:?usage: bash scripts/backup-full.sh <label>}"
TS="$(date +%Y%m%d-%H%M%S)"
OUT="backups/full-${LABEL}-${TS}.tar.gz"
mkdir -p backups

# Full backup: include the DB and .env (secrets). DO NOT share this file.
# Excludes: venv, .git, logs, caches, backups, __pycache__, temp files.
tar \
  --exclude='backups' \
  --exclude='.git' \
  --exclude='venv' \
  --exclude='logs' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='.mypy_cache' \
  --exclude='.ruff_cache' \
  --exclude='.coverage' \
  --exclude='CONTEXT-FULL.txt' \
  --exclude='HANDOFF-STATE.txt' \
  -I 'gzip -1' \
  -cf "$OUT" \
  .

SIZE=$(du -h "$OUT" | cut -f1)
echo "FULL BACKUP: $OUT  ($SIZE)"
echo "WARNING: this archive contains .env and platform_x.db — keep it private."
