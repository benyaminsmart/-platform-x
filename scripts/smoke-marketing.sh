#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — Marketing Copilot smoke test (no browser needed).
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
  local args=(-sS -o "$SMOKE_DIR/mk.json" -w "%{http_code}" -X "$m" "$BASE$p")
  [ -n "$auth" ] && args+=(-H "Authorization: Bearer $auth")
  args+=(-H "X-Tenant-Slug: $SLUG" -H "Content-Type: application/json")
  [ -n "$d" ] && args+=(-d "$d")
  curl "${args[@]}"
}

jq_get() { python3 -c "import json;d=json.load(open('$SMOKE_DIR/mk.json'));print($1)" 2>/dev/null || echo ""; }

echo "=========================================="
echo "Platform-X — Marketing Copilot smoke test"
echo "BASE=$BASE  SLUG=$SLUG"
echo "=========================================="

step "1) Login"
code=$(req POST /business/api/auth/login "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
TOKEN=$(jq_get "d.get('access_token','')")
[ "$code" = "200" ] && [ -n "$TOKEN" ] && ok "login -> 200" || { ko "login -> $code"; exit 1; }

step "2) Marketing config"
code=$(req GET /business/api/marketing/config "" "$TOKEN")
enabled=$(jq_get "d.get('email_enabled')")
[ "$code" = "200" ] && ok "config -> 200 (email_enabled=$enabled)" || ko "config -> $code"

step "3) Segments summary"
code=$(req GET /business/api/marketing/segments "" "$TOKEN")
total=$(jq_get "d.get('totals',{}).get('customers',0)")
[ "$code" = "200" ] && ok "segments -> 200 (customers=$total)" || ko "segments -> $code"

step "4) Segment users (past_bookers)"
code=$(req GET /business/api/marketing/segments/past_bookers "" "$TOKEN")
cnt=$(jq_get "d.get('count',0)")
[ "$code" = "200" ] && ok "segment users -> 200 ($cnt emails)" || ko "segment users -> $code"

step "5) AI campaign suggestions"
code=$(req POST /business/api/marketing/campaigns/suggest '{"language":"en"}' "$TOKEN")
n=$(jq_get "len(d.get('campaigns',[]))")
prov=$(jq_get "d.get('provider','?')")
[ "$code" = "200" ] && [ "$n" -ge "3" ] && ok "suggest -> 200 ($n campaigns, provider=$prov)" || ko "suggest -> $code n=$n"

step "6) AI targeted campaign"
code=$(req POST /business/api/marketing/campaigns/generate '{"segment":"past_bookers","goal":"boost weekend bookings","language":"en"}' "$TOKEN")
seg=$(jq_get "d.get('campaign',{}).get('target_segment','')")
[ "$code" = "200" ] && [ "$seg" = "past_bookers" ] && ok "generate -> 200 (segment=$seg)" || ko "generate -> $code seg=$seg"

step "7) AI discount suggestions"
code=$(req POST /business/api/marketing/discounts/suggest '{"language":"en"}' "$TOKEN")
n=$(jq_get "len(d.get('suggestions',[]))")
[ "$code" = "200" ] && [ "$n" -ge "1" ] && ok "discounts -> 200 ($n suggestions)" || ko "discounts -> $code n=$n"

step "8) Send campaign (dry-run expected)"
code=$(req POST /business/api/marketing/campaigns/send '{"segment":"past_bookers","subject":"Smoke test","body":"Just a test","language":"en"}' "$TOKEN")
dry=$(jq_get "d.get('dry_run')")
sent=$(jq_get "d.get('sent',0)")
[ "$code" = "200" ] && ok "send -> 200 (dry_run=$dry, sent=$sent)" || ko "send -> $code"

step "9) Auth guard — no token"
code=$(curl -sS -o /dev/null -w "%{http_code}" -X GET "$BASE/business/api/marketing/segments" -H "X-Tenant-Slug: $SLUG")
[ "$code" = "401" ] && ok "no token -> 401" || ko "no token -> $code"

step "10) HTML page renders"
code=$(curl -sS -o "$SMOKE_DIR/mk.html" -w "%{http_code}" "$BASE/business/marketing")
has=$(grep -c "Marketing Copilot" "$SMOKE_DIR/mk.html" || echo "0")
[ "$code" = "200" ] && [ "$has" -gt "0" ] && ok "page -> 200 (Marketing Copilot present)" || ko "page -> $code"

echo ""
echo "=========================================="
echo "RESULT: $pass passed, $fail failed"
echo "=========================================="
[ "$fail" -eq 0 ] && exit 0 || exit 1
