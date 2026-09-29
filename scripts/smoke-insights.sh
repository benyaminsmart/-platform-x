#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — Insights smoke test (no browser needed).
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
  local args=(-sS -o "$SMOKE_DIR/in.json" -w "%{http_code}" -X "$m" "$BASE$p")
  [ -n "$auth" ] && args+=(-H "Authorization: Bearer $auth")
  args+=(-H "X-Tenant-Slug: $SLUG" -H "Content-Type: application/json")
  [ -n "$d" ] && args+=(-d "$d")
  curl "${args[@]}"
}

jq_get() { python3 -c "import json;d=json.load(open('$SMOKE_DIR/in.json'));print($1)" 2>/dev/null || echo ""; }

echo "=========================================="
echo "Platform-X — Insights smoke test"
echo "BASE=$BASE  SLUG=$SLUG"
echo "=========================================="

step "1) Login"
code=$(req POST /business/api/auth/login "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
TOKEN=$(jq_get "d.get('access_token','')")
[ "$code" = "200" ] && [ -n "$TOKEN" ] && ok "login -> 200" || { ko "login -> $code"; exit 1; }

step "2) Occupancy summary"
code=$(req GET "/business/api/insights/occupancy?days=30" "" "$TOKEN")
occ=$(jq_get "d.get('occupancy_pct',0)")
[ "$code" = "200" ] && ok "occupancy -> 200 ($occ%)" || ko "occupancy -> $code"

step "3) Occupancy trend"
code=$(req GET "/business/api/insights/occupancy/trend?days=30" "" "$TOKEN")
has_cur=$(jq_get "'current' in d")
[ "$code" = "200" ] && [ "$has_cur" = "True" ] && ok "trend -> 200" || ko "trend -> $code"

step "4) Occupancy by service"
code=$(req GET "/business/api/insights/occupancy/by-service?days=30" "" "$TOKEN")
n=$(jq_get "len(d)")
[ "$code" = "200" ] && ok "by-service -> 200 ($n services)" || ko "by-service -> $code"

step "5) Day-of-week heatmap"
code=$(req GET "/business/api/insights/heatmap/day-of-week?days=90" "" "$TOKEN")
n=$(jq_get "len(d.get('items',[]))")
[ "$code" = "200" ] && [ "$n" = "7" ] && ok "dow -> 200 (7 items)" || ko "dow -> $code n=$n"

step "6) Hour-of-day heatmap"
code=$(req GET "/business/api/insights/heatmap/hour-of-day?days=90" "" "$TOKEN")
n=$(jq_get "len(d.get('items',[]))")
[ "$code" = "200" ] && [ "$n" = "24" ] && ok "hod -> 200 (24 items)" || ko "hod -> $code n=$n"

step "7) Calendar heatmap"
code=$(req GET "/business/api/insights/heatmap/calendar?days=30" "" "$TOKEN")
n=$(jq_get "len(d.get('items',[]))")
[ "$code" = "200" ] && [ "$n" = "30" ] && ok "calendar -> 200 (30 days)" || ko "calendar -> $code n=$n"

step "8) Revenue forecast (metrics only)"
code=$(req GET "/business/api/insights/revenue/forecast?days=30" "" "$TOKEN")
exp=$(jq_get "d.get('metrics',{}).get('expected_revenue',0)")
[ "$code" = "200" ] && ok "forecast -> 200 (expected=$exp AED)" || ko "forecast -> $code"

step "9) Revenue forecast with AI advice"
code=$(req GET "/business/api/insights/revenue/forecast?days=30&with_advice=true" "" "$TOKEN")
adv=$(jq_get "len(d.get('advice',''))")
[ "$code" = "200" ] && [ "$adv" -gt "20" ] && ok "forecast+advice -> 200 (advice ${adv} chars)" || ko "forecast+advice -> $code"

step "10) Capacity available"
code=$(req GET "/business/api/insights/capacity/available?days=30" "" "$TOKEN")
cap=$(jq_get "d.get('total_capacity_per_day',0)")
[ "$code" = "200" ] && ok "capacity -> 200 ($cap/day)" || ko "capacity -> $code"

step "11) Capacity near-full"
code=$(req GET "/business/api/insights/capacity/near-full?days=30&threshold=80" "" "$TOKEN")
cnt=$(jq_get "d.get('count',0)")
[ "$code" = "200" ] && ok "near-full -> 200 ($cnt days)" || ko "near-full -> $code"

step "12) Auth guard — no token"
code=$(curl -sS -o /dev/null -w "%{http_code}" -X GET "$BASE/business/api/insights/occupancy" -H "X-Tenant-Slug: $SLUG")
[ "$code" = "401" ] && ok "no token -> 401" || ko "no token -> $code"

step "13) HTML page renders"
code=$(curl -sS -o "$SMOKE_DIR/in.html" -w "%{http_code}" "$BASE/business/insights")
has=$(grep -c "Business Insights" "$SMOKE_DIR/in.html" || echo "0")
[ "$code" = "200" ] && [ "$has" -gt "0" ] && ok "page -> 200" || ko "page -> $code"

echo ""
echo "=========================================="
echo "RESULT: $pass passed, $fail failed"
echo "=========================================="
[ "$fail" -eq 0 ] && exit 0 || exit 1
