#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — HANDOFF progress sync helper.
#
# Usage:
#   bash scripts/handoff.sh <marker-line> <commit-sha> [<message>]
#
# Example:
#   bash scripts/handoff.sh "Step 10b — Gallery section on tenant page" "abc1234"
#
# What it does:
#   1. Flip the matching [ ] line in Section 0.5 to [x] (if text matches)
#   2. Update "Last step:" line with the new commit
#   3. Prepend the new commit line to "Commits (recent)"
#   4. Stage + commit + backup
#
# NOTE: if the marker line is not found, it is added under the checklist.

set -e
MARKER="${1:?usage: handoff.sh <marker-line> <commit-sha> [<message>]}"
SHA="${2:?missing commit sha}"
MSG="${3:-docs: HANDOFF progress -> $MARKER}"

cd ~/platform-x
export HND_MARKER="$MARKER"
export HND_SHA="$SHA"
export HND_MSG="$MSG"

python3 - <<'PYH'
import os, re
from datetime import datetime

path = "HANDOFF.md"
src = open(path, encoding="utf-8").read()

marker = os.environ["HND_MARKER"]
sha = os.environ["HND_SHA"]
now = datetime.now().strftime("%Y-%m-%d %H:%M")

# 1. Update "Last step:"
src = re.sub(
    r"^Last step: .*$",
    f"Last step: {marker} ({now})",
    src, count=1, flags=re.MULTILINE,
)

# 2. Flip [ ] -> [x] if the marker text exists in a checklist line
#    We match by the part of the marker after the em-dash or as-is
text_for_match = marker.split("—", 1)[-1].strip() if "—" in marker else marker.strip()
pattern_flip = re.compile(r"^- \[ \] (.*" + re.escape(text_for_match) + r".*)$", re.MULTILINE)
if pattern_flip.search(src):
    src = pattern_flip.sub(lambda m: "- [x] " + m.group(1), src)
else:
    # Add a new [x] line right after the "Started:" line
    add_line = f"- [x] {marker}"
    src = re.sub(
        r"(Started: \d{4}-\d{2}-\d{2}\n)",
        r"\1" + add_line + "\n",
        src, count=1,
    )

# 3. Prepend to "Commits (recent)" block
commit_line = f"- {sha} {marker}"
if "**Commits (recent):**" in src:
    # insert right after the marker line
    src = re.sub(
        r"(\*\*Commits \(recent\):\*\*\n)",
        r"\1" + commit_line + "\n",
        src, count=1,
    )

open(path, "w", encoding="utf-8").write(src)
print("HANDOFF updated:", marker)
PYH

git add HANDOFF.md
git commit -m "$MSG"
bash scripts/backup.sh "handoff-$SHA"
