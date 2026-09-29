#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — Market Insights smoke test (no browser needed).
set -e

BASE="${BASE:-http://127.0.0.1:8030}"
SLUG="${SLUG:-trianon-hotel}"
EMAIL="${EMAIL:-owner@trianon-hotel.com}"
PASSWORD="${PASSWORD:-OwnerPass123}"

SMOKE_DIR="$HOME/platform-x/logs/smoke"
mkdir -p "$SMOKE_DIR"

pass=0; fail=0
step() { echo ""; echo "▶ $1"; }
ok()   { echo "  ✔ $1"; pass=$((pass+1)); }
ko()   { echo "  ✘ $1"; fail=$((fail+1)); }

req() {
  local m="$1" p="$2" d="${3:-}" auth="${4:-}"
  local args=(-sS -o "$SMOKE_DIR/mkt.json" -w "%{http_code}" -X "$m" "$BASE$p")
  [ -n "$auth" ] && args+=(-H "Authorization: Bearer $auth")
  args+=(-H "X-Tenant-Slug: $SLUG" -H "Content-Type: application/json")
  [ -n "$d" ] && args+=(-d "$d")
  curl "${args[@]}"
}

jq_get() { python3 -c "import json;d=json.load(open('$SMOKE_DIR/mkt.json'));print($1)" 2>/dev/null || echo ""; }

echo "=========================================="
echo "Platform-X — Market Insights smoke test"
echo "BASE=$BASE  SLUG=$SLUG"
echo "=========================================="

step "1) Login"
code=$(req POST /business/api/auth/login "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
TOKEN=$(jq_get "d.get('access_token','')")
[ "$code" = "200" ] && [ -n "$TOKEN" ] && ok "login -> 200" || { ko "login -> $code"; exit 1; }

step "2) Category summary"
code=$(req GET /business/api/market/summary "" "$TOKEN")
cat=$(jq_get "d.get('category','')")
sz=$(jq_get "d.get('cohort_size',0)")
[ "$code" = "200" ] && ok "summary -> 200 (cat=$cat, cohort=$sz)" || ko "summary -> $code"

step "3) Tenant position"
code=$(req GET /business/api/market/position "" "$TOKEN")
sz=$(jq_get "d.get('cohort_size',0)")
[ "$code" = "200" ] && ok "position -> 200 (cohort=$sz)" || ko "position -> $code"

step "4) Region summary (UAE)"
code=$(req GET "/business/api/market/region?region=UAE" "" "$TOKEN")
sz=$(jq_get "d.get('cohort_size',0)")
[ "$code" = "200" ] && ok "region -> 200 (peers=$sz)" || ko "region -> $code"

step "5) Combined insights (deterministic)"
code=$(req GET /business/api/market/insights "" "$TOKEN")
prov=$(jq_get "d.get('provider','')")
sl=$(jq_get "len(d.get('strengths',[]))")
wl=$(jq_get "len(d.get('weaknesses',[]))")
[ "$code" = "200" ] && ok "insights -> 200 (provider=$prov, strengths=$sl, weaknesses=$wl)" || ko "insights -> $code"

step "6) AI interpretation"
code=$(req GET "/business/api/market/insights/ai?language=en" "" "$TOKEN")
prov=$(jq_get "d.get('provider','')")
adv=$(jq_get "len(d.get('advice',''))")
[ "$code" = "200" ] && [ "$adv" -gt "20" ] && ok "ai -> 200 (provider=$prov, advice ${adv} chars)" || ko "ai -> $code"

step "7) Invalid language -> 422"
code=$(req GET "/business/api/market/insights/ai?language=xx" "" "$TOKEN")
[ "$code" = "422" ] && ok "invalid language -> 422" || ko "invalid language -> $code"

step "8) Region without query -> 422"
code=$(req GET /business/api/market/region "" "$TOKEN")
[ "$code" = "422" ] && ok "region no query -> 422" || ko "region no query -> $code"

step "9) Auth guard — no token"
code=$(curl -sS -o /dev/null -w "%{http_code}" -X GET "$BASE/business/api/market/summary" -H "X-Tenant-Slug: $SLUG")
[ "$code" = "401" ] && ok "no token -> 401" || ko "no token -> $code"

step "10) HTML page renders"
code=$(curl -sS -o "$SMOKE_DIR/mkt.html" -w "%{http_code}" "$BASE/business/market")
has=$(grep -c "Market Insights" "$SMOKE_DIR/mkt.html" || echo "0")
[ "$code" = "200" ] && [ "$has" -gt "0" ] && ok "page -> 200" || ko "page -> $code"

echo ""
echo "=========================================="
echo "RESULT: $pass passed, $fail failed"
echo "=========================================="
[ "$fail" -eq 0 ] && exit 0 || exit 1
