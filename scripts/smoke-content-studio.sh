#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — Content Studio smoke test (no browser needed).
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
  local args=(-sS -o "$SMOKE_DIR/cs.json" -w "%{http_code}" -X "$m" "$BASE$p")
  [ -n "$auth" ] && args+=(-H "Authorization: Bearer $auth")
  args+=(-H "X-Tenant-Slug: $SLUG" -H "Content-Type: application/json")
  [ -n "$d" ] && args+=(-d "$d")
  curl "${args[@]}"
}

jq_get() { python3 -c "import json;d=json.load(open('$SMOKE_DIR/cs.json'));print($1)" 2>/dev/null || echo ""; }

echo "=========================================="
echo "Platform-X — Content Studio smoke test"
echo "BASE=$BASE  SLUG=$SLUG"
echo "=========================================="

step "1) Login"
code=$(req POST /business/api/auth/login "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
TOKEN=$(jq_get "d.get('access_token','')")
[ "$code" = "200" ] && [ -n "$TOKEN" ] && ok "login -> 200" || { ko "login -> $code"; exit 1; }

step "2) Generate tagline (EN)"
code=$(req POST /business/api/ai/content/tagline '{"language":"en","tone":"professional"}' "$TOKEN")
tg=$(jq_get "d.get('tagline','')")
[ "$code" = "200" ] && [ -n "$tg" ] && ok "tagline: ${tg:0:60}" || ko "tagline -> $code"

step "3) Generate tagline (AR)"
code=$(req POST /business/api/ai/content/tagline '{"language":"ar","tone":"professional"}' "$TOKEN")
[ "$code" = "200" ] && ok "tagline AR -> 200" || ko "tagline AR -> $code"

step "4) Preview import (simple text)"
code=$(req POST /business/api/ai/content/import/preview '{"text":"Smoke Room A - 100\nSmoke Room B - 200","default_type":"room","language":"en"}' "$TOKEN")
cnt=$(jq_get "d.get('count',0)")
prov=$(jq_get "d.get('provider','?')")
[ "$code" = "200" ] && [ "$cnt" -ge "2" ] && ok "preview: $cnt candidates (provider=$prov)" || ko "preview -> $code count=$cnt"

step "5) Import create (2 candidates)"
code=$(req POST /business/api/ai/content/import/create '{"candidates":[{"name":"Smoke A","type":"room","price":"100"},{"name":"Smoke B","type":"room","price":"200"}]}' "$TOKEN")
created=$(jq_get "d.get('created',0)")
SID1=$(jq_get "d.get('service_ids',[None])[0]" 2>/dev/null || echo "")
[ "$code" = "200" ] && [ "$created" = "2" ] && ok "created: 2 services" || ko "create -> $code created=$created"

step "6) Generate description for created service"
code=$(req POST "/business/api/ai/content/service/$SID1" '{"language":"en","tone":"luxury"}' "$TOKEN")
desc=$(jq_get "d.get('description','')")
[ "$code" = "200" ] && [ -n "$desc" ] && ok "description: ${desc:0:60}..." || ko "desc -> $code"

step "7) Apply description"
code=$(req POST "/business/api/ai/content/service/$SID1/apply" '{"language":"en","tone":"professional"}' "$TOKEN")
[ "$code" = "200" ] && ok "apply -> 200" || ko "apply -> $code"

step "8) Suggest image keywords"
code=$(req POST "/business/api/ai/content/image-keywords/$SID1" "{}" "$TOKEN")
kw=$(jq_get "' | '.join(d.get('keywords',[]))")
[ "$code" = "200" ] && ok "keywords: $kw" || ko "keywords -> $code"

step "9) Auth guard — no token"
code=$(curl -sS -o /dev/null -w "%{http_code}" -X POST "$BASE/business/api/ai/content/tagline" -H "X-Tenant-Slug: $SLUG" -H "Content-Type: application/json" -d "{}")
[ "$code" = "401" ] && ok "no token -> 401" || ko "no token -> $code"

step "10) HTML page renders"
code=$(curl -sS -o "$SMOKE_DIR/cs.html" -w "%{http_code}" "$BASE/business/content")
has_title=$(grep -c "Content Studio" "$SMOKE_DIR/cs.html" || echo "0")
[ "$code" = "200" ] && [ "$has_title" -gt "0" ] && ok "page -> 200 (Content Studio present)" || ko "page -> $code"

echo ""
echo "=========================================="
echo "RESULT: $pass passed, $fail failed"
echo "=========================================="
[ "$fail" -eq 0 ] && exit 0 || exit 1
