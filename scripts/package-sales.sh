#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — Build the SALES package (documents only, no source).
#
# Distinct from scripts/package-delivery.sh (which packages the full
# repo for technical due diligence).
#
# This script packages only the commercial documents a buyer or
# investor needs to evaluate the acquisition.
#
# Usage: bash scripts/package-sales.sh [output-zip-path]

set -euo pipefail

cd ~/platform-x
VERSION=$(git describe --tags --abbrev=0)
DATE=$(date +%Y%m%d-%H%M%S)
OUTPUT="${1:-$HOME/platform-x-sales-${VERSION}-${DATE}.zip}"
STAGE=$(mktemp -d)

echo "=== Package Platform-X SALES bundle ==="
echo "version: $VERSION"
echo "output:  $OUTPUT"
echo "staging: $STAGE"
echo ""

mkdir -p "$STAGE/platform-x-sales"

# --- Overview ---
mkdir -p "$STAGE/platform-x-sales/01-Overview"
cp HANDOFF.md "$STAGE/platform-x-sales/01-Overview/"
cp CHANGELOG.md "$STAGE/platform-x-sales/01-Overview/"
cp docs/17-INVESTMENT-MEMO.md "$STAGE/platform-x-sales/01-Overview/"
cp docs/24-PITCH-DECK.md "$STAGE/platform-x-sales/01-Overview/"
cp docs/16-MASTER-ROADMAP.md "$STAGE/platform-x-sales/01-Overview/"

# --- Valuation ---
mkdir -p "$STAGE/platform-x-sales/02-Valuation"
cp docs/22-VALUATION-DEFENSE.md "$STAGE/platform-x-sales/02-Valuation/"

# --- Technical Summary ---
mkdir -p "$STAGE/platform-x-sales/03-Technical"
cp docs/28-TECHNICAL-DUE-DILIGENCE.md "$STAGE/platform-x-sales/03-Technical/" 2>/dev/null || true
cp docs/21-PG-VERIFICATION.md "$STAGE/platform-x-sales/03-Technical/"
cp docs/20-PAYMENT-TEST-MODE.md "$STAGE/platform-x-sales/03-Technical/"
cp docs/29-LICENSE-AUDIT.md "$STAGE/platform-x-sales/03-Technical/" 2>/dev/null || true

# --- Legal ---
mkdir -p "$STAGE/platform-x-sales/04-Legal"
cp LICENSE "$STAGE/platform-x-sales/04-Legal/"
cp AUTHORS.md "$STAGE/platform-x-sales/04-Legal/"
cp docs/18-SALE-AGREEMENT.md "$STAGE/platform-x-sales/04-Legal/"
cp docs/19-NDA-TEMPLATE.md "$STAGE/platform-x-sales/04-Legal/"

# --- Buyer Docs ---
mkdir -p "$STAGE/platform-x-sales/05-Buyer-Guides"
cp docs/25-DEMO-SETUP.md "$STAGE/platform-x-sales/05-Buyer-Guides/"
cp docs/27-DATA-ROOM.md "$STAGE/platform-x-sales/05-Buyer-Guides/"
cp docs/30-BUYER-ACTIVATION-CHECKLIST.md "$STAGE/platform-x-sales/05-Buyer-Guides/" 2>/dev/null || true
cp -r docs/buyer "$STAGE/platform-x-sales/05-Buyer-Guides/"

# --- Outreach ---
mkdir -p "$STAGE/platform-x-sales/06-Outreach"
cp docs/23-TARGET-BUYERS.md "$STAGE/platform-x-sales/06-Outreach/"
cp docs/26-OUTREACH-EMAILS.md "$STAGE/platform-x-sales/06-Outreach/"

# --- README for the sales bundle ---
cat > "$STAGE/platform-x-sales/README.md" <<EOF
# Platform-X — Sales Bundle

Version: $VERSION
Packaged: $DATE

This bundle contains the commercial documents for evaluating the
acquisition of Platform-X. For the full technical repository
(source, tests, deploy scripts), see the separate delivery package
produced by scripts/package-delivery.sh.

## Structure

- 01-Overview/         Project state, changelog, investment memo,
                       pitch deck, roadmap
- 02-Valuation/        Build vs Buy analysis, valuation defense
- 03-Technical/        Technical due diligence, PostgreSQL verification,
                       payment integration guide, license audit
- 04-Legal/            LICENSE (with transfer clause), AUTHORS,
                       Sale Term Sheet, NDA template
- 05-Buyer-Guides/     Demo setup, data room guide, buyer activation
                       checklist, 12 buyer-facing documents
- 06-Outreach/         Target buyers, outreach email templates

## Suggested reading order

1. 01-Overview/17-INVESTMENT-MEMO.md — start here
2. 01-Overview/24-PITCH-DECK.md
3. 02-Valuation/22-VALUATION-DEFENSE.md
4. 03-Technical/28-TECHNICAL-DUE-DILIGENCE.md
5. 04-Legal/18-SALE-AGREEMENT.md

## Confidentiality

This bundle is confidential. It is shared only after an NDA is
signed (see 04-Legal/19-NDA-TEMPLATE.md).

## Contact

Benjamin Bahoush — platformx2026@gmail.com
EOF

# --- Build zip ---
echo "-> creating zip"
cd "$STAGE"
if command -v zip >/dev/null 2>&1; then
  zip -rq "$OUTPUT" platform-x-sales
else
  OUTPUT="${OUTPUT%.zip}.tar.gz"
  tar -czf "$OUTPUT" platform-x-sales
fi
cd ~/platform-x

# --- Report ---
SIZE=$(du -h "$OUTPUT" | cut -f1)
if command -v sha256sum >/dev/null 2>&1; then
  SHA=$(sha256sum "$OUTPUT" | cut -d' ' -f1)
else
  SHA="(sha256sum not available)"
fi

echo ""
echo "=== DONE ==="
echo "output: $OUTPUT"
echo "size:   $SIZE"
echo "sha256: $SHA"

# --- File count in bundle ---
echo ""
echo "=== files in bundle ==="
cd "$STAGE" && find platform-x-sales -type f | wc -l
cd ~/platform-x

rm -rf "$STAGE"
