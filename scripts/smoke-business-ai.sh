#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — Business AI smoke test (no browser needed).
# Runs against localhost by default. Override BASE=... to test remote.
#
# Usage:
#   bash scripts/smoke-business-ai.sh
#   BASE=https://looks-...trycloudflare.com bash scripts/smoke-business-ai.sh

set -e

SMOKE_DIR="$HOME/platform-x/logs/smoke"
mkdir -p "$SMOKE_DIR"

BASE="${BASE:-http://127.0.0.1:8030}"
SLUG="${SLUG:-trianon-hotel}"
EMAIL="${EMAIL:-owner@trianon-hotel.com}"
PASSWORD="${PASSWORD:-OwnerPass123}"

pass=0
fail=0
step() { echo ""; echo "▶ $1"; }
ok()   { echo "  ✔ $1"; pass=$((pass+1)); }
ko()   { echo "  ✘ $1"; fail=$((fail+1)); }

req() {
  # req METHOD PATH [DATA] [AUTH_HEADER_VALUE]
  local m="$1" p="$2" d="${3:-}" auth="${4:-}"
  local args=(-sS -o $SMOKE_DIR/out.json -w "%{http_code}" -X "$m" "$BASE$p")
  [ -n "$auth" ] && args+=(-H "Authorization: Bearer $auth")
  args+=(-H "X-Tenant-Slug: $SLUG" -H "Content-Type: application/json")
  [ -n "$d" ] && args+=(-d "$d")
  curl "${args[@]}"
}

# ---------------------------------------------------------------
echo "=========================================="
echo "Platform-X — Business AI smoke test"
echo "BASE=$BASE  SLUG=$SLUG  EMAIL=$EMAIL"
echo "=========================================="

step "1) Health check"
code=$(curl -sS -o $SMOKE_DIR/health.json -w "%{http_code}" "$BASE/health")
[ "$code" = "200" ] && ok "GET /health -> 200" || ko "GET /health -> $code"

step "2) AI health"
code=$(curl -sS -o $SMOKE_DIR/aihealth.json -w "%{http_code}" "$BASE/ai/health")
[ "$code" = "200" ] && ok "GET /ai/health -> 200" || ko "GET /ai/health -> $code"

step "3) Business login"
code=$(req POST /business/api/auth/login "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
TOKEN=$(python3 -c "import json;print(json.load(open('$SMOKE_DIR/out.json')).get('access_token',''))" 2>/dev/null || echo "")
if [ "$code" = "200" ] && [ -n "$TOKEN" ]; then ok "login -> 200 (token ${TOKEN:0:20}...)"; else ko "login -> $code"; fi
[ -z "$TOKEN" ] && { echo "  Cannot continue without token."; exit 1; }

step "4) /business/api/me"
code=$(req GET /business/api/me "" "$TOKEN")
slug_echo=$(python3 -c "import json;print(json.load(open('$SMOKE_DIR/out.json')).get('tenant_slug',''))" 2>/dev/null || echo "")
[ "$code" = "200" ] && ok "me -> 200 (tenant_slug=$slug_echo)" || ko "me -> $code"

step "5) /business/api/ai/chat"
code=$(req POST /business/api/ai/chat "{\"message\":\"How is my pricing?\"}" "$TOKEN")
content=$(python3 -c "import json;print((json.load(open('$SMOKE_DIR/out.json')).get('content') or '')[:60])" 2>/dev/null || echo "")
[ "$code" = "200" ] && [ -n "$content" ] && ok "chat -> 200 (content='$content...')" || ko "chat -> $code"

step "6) /business/api/ai/pricing/analyze"
code=$(req POST /business/api/ai/pricing/analyze "{}" "$TOKEN")
dt=$(python3 -c "import json;d=json.load(open('$SMOKE_DIR/out.json'));print(d['metrics'].get('dominant_type'))" 2>/dev/null || echo "")
[ "$code" = "200" ] && ok "analyze -> 200 (dominant_type=$dt)" || ko "analyze -> $code"

step "7) /business/api/ai/pricing/suggest"
code=$(req POST /business/api/ai/pricing/suggest "{}" "$TOKEN")
stype=$(python3 -c "import json;d=json.load(open('$SMOKE_DIR/out.json'));print(d['metrics']['suggestions'][0].get('type'))" 2>/dev/null || echo "")
[ "$code" = "200" ] && ok "suggest -> 200 (first suggestion type=$stype)" || ko "suggest -> $code"

step "8) /business/api/ai/demand/forecast?days=30"
code=$(req POST "/business/api/ai/demand/forecast?days=30" "{}" "$TOKEN")
days=$(python3 -c "import json;print(json.load(open('$SMOKE_DIR/out.json'))['metrics'].get('days'))" 2>/dev/null || echo "")
[ "$code" = "200" ] && [ "$days" = "30" ] && ok "forecast -> 200 (days=$days)" || ko "forecast -> $code days=$days"

step "9) /business/api/ai/demand/forecast?days=500 (clamp to 90)"
code=$(req POST "/business/api/ai/demand/forecast?days=500" "{}" "$TOKEN")
days=$(python3 -c "import json;print(json.load(open('$SMOKE_DIR/out.json'))['metrics'].get('days'))" 2>/dev/null || echo "")
[ "$code" = "200" ] && [ "$days" = "90" ] && ok "forecast clamp -> 90" || ko "forecast clamp -> $code days=$days"

step "10) /business/api/ai/insights"
code=$(req POST /business/api/ai/insights "{}" "$TOKEN")
sz=$(python3 -c "import json;print(json.load(open('$SMOKE_DIR/out.json'))['metrics'].get('cohort_size'))" 2>/dev/null || echo "")
[ "$code" = "200" ] && ok "insights -> 200 (cohort_size=$sz)" || ko "insights -> $code"

step "11) Auth guard — no token"
code=$(curl -sS -o /dev/null -w "%{http_code}" -X POST "$BASE/business/api/ai/pricing/analyze" -H "X-Tenant-Slug: $SLUG" -H "Content-Type: application/json" -d "{}")
[ "$code" = "401" ] || [ "$code" = "403" ] && ok "no-token -> $code (expected 401/403)" || ko "no-token -> $code"

echo ""
echo "=========================================="
echo "RESULT: $pass passed, $fail failed"
echo "=========================================="
[ "$fail" -eq 0 ] && exit 0 || exit 1
