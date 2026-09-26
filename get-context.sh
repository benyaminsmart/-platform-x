#!/data/data/com.termux/files/usr/bin/bash
# =====================================================
# Platform-X - Full Context Generator
# =====================================================
# يک دستور، يک خروجي: همه چيز براي چت جديد
# Usage: bash get-context.sh
# Output: CONTEXT-FULL.txt (in project root)
# =====================================================

cd ~/platform-x || exit 1
OUT="CONTEXT-FULL.txt"

{
echo "======================================================"
echo "PLATFORM-X - FULL CONTEXT FOR NEW CHAT"
echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================"
echo ""

echo "######################################################"
echo "# PART 1: AI-CONTEXT.md (READ FIRST)"
echo "######################################################"
echo ""
cat AI-CONTEXT.md 2>/dev/null
echo ""

echo "######################################################"
echo "# PART 2: PROJECT-RULES.md (QUALITY STANDARDS)"
echo "######################################################"
echo ""
cat PROJECT-RULES.md 2>/dev/null
echo ""

echo "######################################################"
echo "# PART 3: HANDOFF.md (PROJECT OVERVIEW + ROADMAP)"
echo "######################################################"
echo ""
cat HANDOFF.md 2>/dev/null
echo ""

echo "######################################################"
echo "# PART 4: PROJECT-NOTES.md (TECHNICAL DECISIONS)"
echo "######################################################"
echo ""
cat PROJECT-NOTES.md 2>/dev/null
echo ""

echo "######################################################"
echo "# PART 5: HANDOFF-STATE.txt (CURRENT STATE - AUTO)"
echo "######################################################"
echo ""
bash generate-handoff.sh > /dev/null 2>&1
cat HANDOFF-STATE.txt 2>/dev/null
echo ""

echo "######################################################"
echo "# PART 6: DOCS/ FOLDER (ARCHITECTURE + ROADMAP DETAILS)"
echo "######################################################"
echo ""

for doc in docs/01-ARCHITECTURE.md docs/02-ROADMAP.md docs/03-BUSINESS-MODEL.md docs/04-FEATURES.md docs/05-TENANT-GUIDE.md docs/06-DECISIONS.md; do
  if [ -f "$doc" ]; then
    echo "======================================================"
    echo "# $doc"
    echo "======================================================"
    echo ""
    cat "$doc"
    echo ""
  fi
done

echo "######################################################"
echo "# END OF CONTEXT"
echo "######################################################"

} > "$OUT" 2>&1

echo "✅ Full context generated: $OUT"
echo "📊 Size: $(wc -c < $OUT) bytes"
echo "📄 Lines: $(wc -l < $OUT)"
echo ""
echo "Copy it to clipboard:"
echo "  termux-clipboard-set < $OUT"
echo ""
echo "Or view it:"
echo "  cat $OUT"
