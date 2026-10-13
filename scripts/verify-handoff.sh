#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — HANDOFF consistency verifier.
# Usage: bash scripts/verify-handoff.sh [--quick]
# Exit: 0 if all pass, 1 if any fail.

set -uo pipefail

cd ~/platform-x
QUICK=0
[ "${1:-}" = "--quick" ] && QUICK=1

PASS=0
FAIL=0
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $1"; PASS=$((PASS+1)); }
bad()  { echo -e "${RED}✗${NC} $1"; FAIL=$((FAIL+1)); }
info() { echo -e "${YELLOW}→${NC} $1"; }

echo "=== verify-handoff.sh ==="
echo "started: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo ""

if [ ! -f HANDOFF.md ]; then
  bad "HANDOFF.md not found"
  exit 1
fi

# ---- Check 1: version line vs latest tag ----
LATEST_TAG=$(git describe --tags 2>/dev/null || echo "none")
VERSION_LINE=$(grep -m1 "^> Version:" HANDOFF.md || echo "")
if echo "$VERSION_LINE" | grep -q "$LATEST_TAG"; then
  ok "Check 1: version line matches latest tag ($LATEST_TAG)"
else
  bad "Check 1: version mismatch"
  info "  latest tag:   $LATEST_TAG"
  info "  HANDOFF line: $VERSION_LINE"
fi

# ---- Check 2: test count vs real pytest output ----
if [ "$QUICK" -eq 1 ]; then
  info "Check 2: SKIPPED (--quick mode)"
else
  info "Check 2: running pytest (this takes ~60s)..."
  PYTEST_OUT=$(source venv/bin/activate 2>/dev/null; pytest tests/ -n auto --tb=no -q 2>&1 | grep -oE "[0-9]+ passed" | head -1)
  REAL_COUNT=$(echo "$PYTEST_OUT" | grep -oE "^[0-9]+")
  HND_COUNT=$(grep -m1 "^## 14. Test Count:" HANDOFF.md | grep -oE "[0-9]+" | head -1)
  if [ -z "$REAL_COUNT" ]; then
    bad "Check 2: could not parse pytest output"
    info "  raw: $PYTEST_OUT"
  elif [ "$REAL_COUNT" = "$HND_COUNT" ]; then
    ok "Check 2: test count matches ($REAL_COUNT)"
  else
    bad "Check 2: test count mismatch"
    info "  pytest:     $REAL_COUNT"
    info "  HANDOFF:    $HND_COUNT"
  fi
fi

# ---- Check 3: Section 0.5 has no stale [ ] ----
STALE=$(awk '/^## 0.5|^### 0.5|^Last step:/{flag=1; next} /^## /{flag=0} flag && /- \[ \]/' HANDOFF.md | wc -l)
if [ "$STALE" -eq 0 ]; then
  ok "Check 3: no stale [ ] in Section 0.5"
else
  bad "Check 3: $STALE stale [ ] in Section 0.5"
  info "  inspect with: grep -n '\\[ \\]' HANDOFF.md | head"
fi

# ---- Check 4: latest phase appears in HANDOFF ----
LATEST_PHASE=$(git log --oneline -50 | grep -oE "Phase [0-9]+" | head -1)
if [ -z "$LATEST_PHASE" ]; then
  info "Check 4: SKIPPED (no Phase N in recent commits)"
else
  if grep -q "$LATEST_PHASE" HANDOFF.md; then
    ok "Check 4: $LATEST_PHASE recorded in HANDOFF"
  else
    bad "Check 4: $LATEST_PHASE NOT found in HANDOFF"
  fi
fi

# ---- Check 5: Last updated == today ----
TODAY=$(date '+%Y-%m-%d')
LAST_UPDATED=$(grep -m1 "^Last updated:" HANDOFF.md | grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2}")
if [ "$LAST_UPDATED" = "$TODAY" ]; then
  ok "Check 5: Last updated = today ($TODAY)"
else
  bad "Check 5: Last updated is $LAST_UPDATED (today: $TODAY)"
fi

# ---- Check 6: working tree clean ----
if [ -z "$(git status --short)" ]; then
  ok "Check 6: working tree is clean"
else
  bad "Check 6: working tree has uncommitted changes"
  info "  files:"
  git status --short | sed 's/^/    /'
fi

# ---- Summary ----
echo ""
echo "=== summary: $PASS passed, $FAIL failed ==="
echo "finished: $(date '+%Y-%m-%d %H:%M:%S %Z')"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
