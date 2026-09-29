#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — Step automation helper.
#
# Usage (named args — order-independent):
#   bash scripts/step.sh --test <path> --message "<commit msg>" --label <backup-label>
#
# Example:
#   bash scripts/step.sh \
#     --test tests/test_x.py \
#     --message "feat(phase-N/step-M): short description" \
#     --label phase-N-step-M-done
#
# What it does:
#   1. Validate test file exists
#   2. Stage: git add -A
#   3. Run pytest <test>
#   4. If pass -> git commit
#   5. Backup: bash scripts/backup.sh <label>
#   6. On any failure -> git reset (unstage) and abort

set -e

TEST=""
MESSAGE=""
LABEL=""

while [ $# -gt 0 ]; do
  case "$1" in
    --test)    TEST="$2"; shift 2 ;;
    --message) MESSAGE="$2"; shift 2 ;;
    --label)   LABEL="$2"; shift 2 ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done

[ -z "$TEST" ]    && { echo "missing --test"; exit 2; }
[ -z "$MESSAGE" ] && { echo "missing --message"; exit 2; }
[ -z "$LABEL" ]   && { echo "missing --label"; exit 2; }

cd ~/platform-x

if [ ! -f "$TEST" ]; then
  echo "✘ test file not found: $TEST"
  exit 2
fi

echo "▶ staging changes..."
git add -A

if git diff --cached --quiet; then
  echo "  no staged changes. Nothing to commit."
  exit 0
fi

echo "▶ running tests: $TEST"
source venv/bin/activate
if ! pytest "$TEST" -q 2>&1 | tail -5 | grep -qE "passed|no tests ran"; then
  echo "  ✘ tests failed or none ran. Unstaging."
  git reset
  exit 1
fi

echo "▶ committing..."
git commit -m "$MESSAGE"

echo "▶ backup: $LABEL"
bash scripts/backup.sh "$LABEL"

echo "▶ updating HANDOFF progress..."
export STEP_LABEL="$LABEL"

echo "▶ updating HANDOFF progress..."
export STEP_LABEL="$LABEL"
python3 - <<'PYHANDOFF'
import os, re
from datetime import datetime

path = "HANDOFF.md"
try:
    src = open(path, encoding="utf-8").read()
except FileNotFoundError:
    raise SystemExit(0)

if "## 0.5 Wave 0 Progress" not in src:
    raise SystemExit(0)

label = os.environ.get("STEP_LABEL", "").strip()
if not label:
    raise SystemExit(0)

now = datetime.now().strftime("%Y-%m-%d %H:%M")
src = re.sub(r"^Last step: .*$", f"Last step: {label} ({now})", src, count=1, flags=re.MULTILINE)

open(path, "w", encoding="utf-8").write(src)
print("HANDOFF progress updated:", label)
PYHANDOFF
unset STEP_LABEL

echo ""
echo "=== STEP DONE ==="
git log --oneline -1
