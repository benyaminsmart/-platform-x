#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — Step automation helper.
#
# Usage:
#   bash scripts/step.sh <label> <test_path> "<commit_message>"
#
# What it does (in order):
#   1. Stage all changes:  git add -A
#   2. Run tests:          pytest <test_path>
#   3. If tests pass:      git commit -m "<message>"
#   4. Backup:             bash scripts/backup.sh <label>
#   5. If anything fails: abort and rollback staging (git reset)

set -e

LABEL="${1:?usage: step.sh <label> <test_path> \"<message>\"}"
TEST_PATH="${2:?missing test_path}"
MESSAGE="${3:?missing commit message}"

cd ~/platform-x

echo "▶ staging changes..."
git add -A

if git diff --cached --quiet; then
  echo "  no staged changes. Nothing to commit."
  exit 0
fi

echo "▶ running tests: $TEST_PATH"
if ! source venv/bin/activate && pytest "$TEST_PATH" -q 2>&1 | tail -5; then
  echo "  ✘ tests failed. Unstaging."
  git reset
  exit 1
fi

echo "▶ committing..."
git commit -m "$MESSAGE"

echo "▶ backup: $LABEL"
bash scripts/backup.sh "$LABEL"

echo ""
echo "=== STEP DONE ==="
git log --oneline -1
