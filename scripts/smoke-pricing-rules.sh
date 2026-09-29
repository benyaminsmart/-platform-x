#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — Pricing Rules smoke test (no browser needed).
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
  local args=(-sS -o "$SMOKE_DIR/out.json" -w "%{http_code}" -X "$m" "$BASE$p")
  [ -n "$auth" ] && args+=(-H "Authorization: Bearer $auth")
  args+=(-H "X-Tenant-Slug: $SLUG" -H "Content-Type: application/json")
  [ -n "$d" ] && args+=(-d "$d")
  curl "${args[@]}"
}

jq_get() { python3 -c "import json,sys;d=json.load(open('$SMOKE_DIR/out.json'));print($1)" 2>/dev/null || echo ""; }

echo "=========================================="
echo "Platform-X — Pricing Rules smoke test"
echo "BASE=$BASE  SLUG=$SLUG"
echo "=========================================="

step "1) Login"
code=$(req POST /business/api/auth/login "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
TOKEN=$(jq_get "d.get('access_token','')")
[ "$code" = "200" ] && [ -n "$TOKEN" ] && ok "login -> 200" || { ko "login -> $code"; exit 1; }

step "2) List rules initially"
code=$(req GET /business/api/pricing/rules "" "$TOKEN")
count=$(jq_get "len(d)")
ok "list -> 200 (count=$count)"

step "3) Create weekend rule (+20%)"
code=$(req POST /business/api/pricing/rules \
  '{"name":"Smoke weekend","rule_type":"weekend","conditions":{"days_of_week":[5,6]},"action":{"type":"percent","value":20},"priority":100}' \
  "$TOKEN")
RID=$(jq_get "d.get('id','')")
[ "$code" = "201" ] && [ -n "$RID" ] && ok "create -> 201 id=${RID:0:8}..." || ko "create -> $code"

step "4) Create second rule (last_minute -10%)"
code=$(req POST /business/api/pricing/rules \
  '{"name":"Smoke last-minute","rule_type":"last_minute","conditions":{"days_ahead_max":2},"action":{"type":"percent","value":-10},"priority":200}' \
  "$TOKEN")
[ "$code" = "201" ] && ok "create -> 201" || ko "create -> $code"

step "5) Get rule detail"
code=$(req GET "/business/api/pricing/rules/$RID" "" "$TOKEN")
name=$(jq_get "d.get('name','')")
[ "$code" = "200" ] && [ "$name" = "Smoke weekend" ] && ok "get -> 200 name=$name" || ko "get -> $code name=$name"

step "6) Update rule priority"
code=$(req PATCH "/business/api/pricing/rules/$RID" '{"priority":42}' "$TOKEN")
prio=$(jq_get "d.get('priority')")
[ "$code" = "200" ] && [ "$prio" = "42" ] && ok "patch -> 200 priority=42" || ko "patch -> $code priority=$prio"

step "7) Invalid rule_type -> 400"
code=$(req POST /business/api/pricing/rules '{"name":"x","rule_type":"bogus","action":{"type":"percent","value":10}}' "$TOKEN")
[ "$code" = "400" ] && ok "invalid type -> 400" || ko "invalid type -> $code"

step "8) Invalid action type -> 400"
code=$(req POST /business/api/pricing/rules '{"name":"x","rule_type":"weekend","action":{"type":"bogus","value":10}}' "$TOKEN")
[ "$code" = "400" ] && ok "invalid action -> 400" || ko "invalid action -> $code"

step "9) No token -> 401"
code=$(curl -sS -o /dev/null -w "%{http_code}" -X GET "$BASE/business/api/pricing/rules" -H "X-Tenant-Slug: $SLUG")
[ "$code" = "401" ] && ok "no token -> 401" || ko "no token -> $code"

step "10) Soft delete"
code=$(req DELETE "/business/api/pricing/rules/$RID" "" "$TOKEN")
active=$(jq_get "d.get('active')" 2>/dev/null || echo "")
[ "$code" = "200" ] && ok "delete -> 200 (soft)" || ko "delete -> $code"

step "11) Deleted rule still visible with active=False"
code=$(req GET "/business/api/pricing/rules/$RID" "" "$TOKEN")
act=$(jq_get "d.get('active')")
[ "$code" = "200" ] && [ "$act" = "False" ] && ok "rule inactive after delete" || ko "rule active=$act"

echo ""
echo "=========================================="
echo "RESULT: $pass passed, $fail failed"
echo "=========================================="
[ "$fail" -eq 0 ] && exit 0 || exit 1
