#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — Print a COMPACT context for a new AI chat.
#
# Output: ~5-8 KB instead of ~300 KB. Contains everything a new session
# needs to start immediately.
set -e
cd ~/platform-x

echo "==================================================================="
echo "Platform-X — Compact Context for New Chat"
echo "Generated: $(date)"
echo "==================================================================="
echo ""
echo "READ THIS FIRST, THEN CONTINUE FROM 'NEXT STEP'."
echo ""
echo "=== 1. NEW CHAT QUICKSTART (authoritative for behavior) ==="
cat docs/00-NEW-CHAT-QUICKSTART.md
echo ""
echo "=== 2. HANDOFF — STRATEGIC SECTIONS ONLY ==="
echo ""
echo "--- 2a. Version / current tag ---"
head -8 HANDOFF.md
echo ""
echo "--- 2b. Strategic plan (Section 0.1.5) ---"
sed -n '/## 0.1.5 STRATEGIC ROADMAP TO SALE/,/^---$/p' HANDOFF.md | head -200
echo ""
echo "--- 2c. Recent phases (last 10 in Section 5) ---"
grep -n "^### Phase" HANDOFF.md | tail -10
echo ""
echo "--- 2d. Remaining work (Section 11) ---"
sed -n '/## 11. Remaining Work/,/## 12/p' HANDOFF.md | head -60
echo ""
echo "=== 3. TAG + LAST COMMITS ==="
git tag -l | sort -V | tail -5
echo "---"
git log --oneline -5
echo ""
echo "=== 4. TREE + TEST STATUS ==="
git status --short || true
echo "(clean if empty)"
echo ""
echo "=== 5. READY TO START ==="
echo "Now: open the repo in your terminal and continue from the"
echo "'NEXT STEP' section in the Quickstart above."
echo ""
echo "Essential commands:"
echo "  cd ~/platform-x"
echo "  source venv/bin/activate"
echo "  pytest tests/ -n auto            # full suite, ~50s"
echo "  bash scripts/step.sh --test <path> --message '<msg>' --label <lbl>"
echo "  bash scripts/handoff.sh '<desc>' <sha> '<msg>'"
echo "==================================================================="
