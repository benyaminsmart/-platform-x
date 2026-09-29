#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — Public API v1 smoke test
BASE="${BASE:-http://127.0.0.1:8030}"
SLUG="${SLUG:-trianon-hotel}"
EMAIL="${EMAIL:-owner@trianon-hotel.com}"
PASSWORD="${PASSWORD:-OwnerPass123}"

SMOKE="$HOME/platform-x/logs/smoke"
mkdir -p "$SMOKE"

pass=0; fail=0
ok() { echo "  ✔ $1"; pass=$((pass+1)); }
ko() { echo "  ✘ $1"; fail=$((fail+1)); }
get() { python3 -c "import json;d=json.load(open('$SMOKE/r.json'));print($1)" 2>/dev/null || echo ""; }

echo "Platform-X — Public API smoke"
echo "BASE=$BASE  SLUG=$SLUG"
echo ""

echo "▶ 1) Business login"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" -X POST "$BASE/business/api/auth/login" -H "X-Tenant-Slug: $SLUG" -H "Content-Type: application/json" -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
BTOK=$(get "d.get('access_token','')")
[ "$c" = "200" ] && [ -n "$BTOK" ] && ok "login 200" || { ko "login $c"; exit 1; }

echo "▶ 2) Create API key (read:services, read:bookings, read:reviews, read:analytics)"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" -X POST "$BASE/business/api/keys" -H "X-Tenant-Slug: $SLUG" -H "Content-Type: application/json" -H "Authorization: Bearer $BTOK" -d '{"name":"Smoke key","scopes":["read:services","read:bookings","read:reviews","read:analytics"]}')
APIKEY=$(get "d.get('plaintext','')")
KID=$(get "d.get('key',{}).get('id','')")
[ "$c" = "200" ] && [ -n "$APIKEY" ] && ok "key created (${APIKEY:0:15}...)" || { ko "create key $c"; exit 1; }

echo "▶ 3) GET /api/v1/me"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" -X GET "$BASE/api/v1/me" -H "X-API-Key: $APIKEY")
tid=$(get "d.get('tenant_slug','')")
[ "$c" = "200" ] && [ "$tid" = "$SLUG" ] && ok "me 200 (tenant=$tid)" || ko "me $c tenant=$tid"

echo "▶ 4) GET /api/v1/services"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" -X GET "$BASE/api/v1/services?page_size=3" -H "X-API-Key: $APIKEY")
tot=$(get "d.get('total',0)")
[ "$c" = "200" ] && ok "services 200 (total=$tot)" || ko "services $c"

echo "▶ 5) GET /api/v1/bookings"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" -X GET "$BASE/api/v1/bookings?page_size=3" -H "X-API-Key: $APIKEY")
tot=$(get "d.get('total',0)")
[ "$c" = "200" ] && ok "bookings 200 (total=$tot)" || ko "bookings $c"

echo "▶ 6) GET /api/v1/reviews"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" -X GET "$BASE/api/v1/reviews?page_size=3" -H "X-API-Key: $APIKEY")
tot=$(get "d.get('total',0)")
[ "$c" = "200" ] && ok "reviews 200 (total=$tot)" || ko "reviews $c"

echo "▶ 7) GET /api/v1/analytics/summary?days=30"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" -X GET "$BASE/api/v1/analytics/summary?days=30" -H "X-API-Key: $APIKEY")
tot=$(get "d.get('total_bookings',0)")
[ "$c" = "200" ] && ok "analytics 200 (total_bookings=$tot)" || ko "analytics $c"

echo "▶ 8) Missing API key -> 401"
c=$(curl -sS -o /dev/null -w "%{http_code}" -X GET "$BASE/api/v1/me")
[ "$c" = "401" ] && ok "no key 401" || ko "no key $c"

echo "▶ 9) Invalid API key -> 401"
c=$(curl -sS -o /dev/null -w "%{http_code}" -X GET "$BASE/api/v1/me" -H "X-API-Key: pk_live_deadbeefdeadbeef")
[ "$c" = "401" ] && ok "bad key 401" || ko "bad key $c"

echo "▶ 10) Revoke key"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" -X POST "$BASE/business/api/keys/$KID/revoke" -H "X-Tenant-Slug: $SLUG" -H "Authorization: Bearer $BTOK")
act=$(get "d.get('active')")
[ "$c" = "200" ] && [ "$act" = "False" ] && ok "revoked" || ko "revoke $c active=$act"

echo "▶ 11) Revoked key rejected -> 401"
c=$(curl -sS -o /dev/null -w "%{http_code}" -X GET "$BASE/api/v1/services" -H "X-API-Key: $APIKEY")
[ "$c" = "401" ] && ok "revoked key 401" || ko "revoked key $c"

echo "▶ 12) Public docs page /docs/api"
c=$(curl -sS -o "$SMOKE/d.html" -w "%{http_code}" "$BASE/docs/api")
has=$(grep -c "Public API" "$SMOKE/d.html")
[ "$c" = "200" ] && [ "$has" -ge "1" ] && ok "docs page 200" || ko "docs page $c"

echo "▶ 13) Business API keys page"
c=$(curl -sS -o "$SMOKE/k.html" -w "%{http_code}" "$BASE/business/api-keys")
has=$(grep -c "API Keys" "$SMOKE/k.html")
[ "$c" = "200" ] && [ "$has" -ge "1" ] && ok "keys page 200" || ko "keys page $c"

echo ""
echo "RESULT: $pass passed, $fail failed"
[ "$fail" -eq 0 ] && exit 0 || exit 1
