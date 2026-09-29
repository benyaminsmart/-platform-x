#!/data/data/com.termux/files/usr/bin/bash
# Safely update the version + last updated lines in HANDOFF.md.
# Usage:
#   bash scripts/update-handoff-version.sh v0.20.0-foo "Phases 0-7 complete"
#
# This script is defensive: it anchors on the leading "> " marker used in
# HANDOFF.md so the regex always matches regardless of line numbering.

set -e

VERSION="${1:?usage: bash scripts/update-handoff-version.sh vX.Y.Z-name \"description\"}"
DESC="${2:-}"

python3 - <<PYEOF
import re
from datetime import date

p = "HANDOFF.md"
src = open(p, encoding="utf-8").read()

new_line = "> Version: ${VERSION}" + (f" ({DESC})" if "${DESC}" else "")
src = re.sub(r"^> Version: .*$", new_line, src, count=1, flags=re.MULTILINE)
src = re.sub(r"^Last updated: .*$", "Last updated: " + date.today().isoformat(), src, count=1, flags=re.MULTILINE)

open(p, "w", encoding="utf-8").write(src)
print("HANDOFF version updated to ${VERSION}")
PYEOF
