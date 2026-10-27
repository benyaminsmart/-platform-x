#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — print compact context for a new AI chat.
# Reads QUICKSTART + HANDOFF + git state. Output is designed to fit in
# one AI message.

set -uo pipefail
cd ~/platform-x

echo "==================================================================="
echo "Platform-X — Compact Context for New Chat"
echo "Generated: $(date)"
echo "==================================================================="
echo ""
echo "READ THIS FIRST, THEN CONTINUE FROM 'NEXT STEP'."
echo ""

# ---- 1. Quickstart ----
echo "=== 1. NEW CHAT QUICKSTART (authoritative for behavior) ==="
cat docs/00-NEW-CHAT-QUICKSTART.md
echo ""

# ---- 2. HANDOFF strategic sections ----
echo "=== 2. HANDOFF — STRATEGIC SECTIONS ONLY ==="
echo ""
echo "--- 2a. Version / current tag ---"
head -8 HANDOFF.md
echo ""
echo "--- 2b. Roadmap (Section 3) ---"
sed -n '/^## 3\. Roadmap Zero-to-Sale/,/^## 4\./p' HANDOFF.md | head -40
echo ""
echo "--- 2c. What is Built (Section 4) ---"
sed -n '/^## 4\. What is Built/,/^## 5\./p' HANDOFF.md | head -40
echo ""
echo "--- 2d. Known Gaps (Section 9) ---"
sed -n '/^## 9\. Known Gaps/,/^## 10\./p' HANDOFF.md | head -40
echo ""

# ---- 3. Tags + last commits ----
echo "=== 3. TAG + LAST COMMITS ==="
git tag -l | sort -V | tail -5
echo "---"
git log --oneline -5
echo ""

# ---- 4. Tree + test status ----
echo "=== 4. TREE + TEST STATUS ==="
git status --short
echo "(clean if empty)"
echo ""

# ---- 5. Ready to start ----
echo "=== 5. READY TO START ==="
echo "Now: open the repo in your terminal and continue from the"
echo "'NEXT STEP' section in the Quickstart above."
echo ""
echo "Essential commands:"
echo "  cd ~/platform-x"
echo "  source venv/bin/activate"
echo "  pytest tests/ -n auto            # full suite, ~60s"
echo "  bash scripts/step.sh --test <path> --message '<msg>' --label <lbl>"
echo "  bash scripts/handoff.sh '<desc>' <sha> '<msg>'"
echo "==================================================================="
