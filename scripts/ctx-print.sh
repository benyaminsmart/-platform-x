#!/data/data/com.termux/files/usr/bin/bash
set -e
cd ~/platform-x
echo "Platform-X — Complete Context for New Chat"
echo "Generated: $(date)"
echo ""
echo "=== INSTRUCTIONS FOR AI IN NEW CHAT ==="
echo "You are Senior Software Engineer + Tech Lead for Platform-X."
echo "Read ALL 3 documents below COMPLETELY before responding."
echo "Rules: Persian only. Excellence. Backup+test+commit every step."
echo "One step at a time. No features outside roadmap. No architecture"
echo "changes without approval. Decide technical matters yourself."
echo "After reading, confirm mastery and ask what to do next."
echo ""
echo "=== DOCUMENT 1: HANDOFF.md ==="
cat HANDOFF.md
echo ""
echo "=== DOCUMENT 2: WORKING-METHOD.md ==="
cat WORKING-METHOD.md
echo ""
echo "=== DOCUMENT 3: docs/14-ROADMAP-V3-COMPETITIVE.md ==="
cat docs/14-ROADMAP-V3-COMPETITIVE.md
echo ""
echo "=== DOCUMENT 4: docs/15-AI-PLAYBOOK.md ==="
cat docs/15-AI-PLAYBOOK.md
