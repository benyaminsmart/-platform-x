#!/data/data/com.termux/files/usr/bin/bash
# Platform-X — Reviews smoke test (v2, simpler)
BASE="${BASE:-http://127.0.0.1:8030}"
SLUG="${SLUG:-trianon-hotel}"
EMAIL="${EMAIL:-owner@trianon-hotel.com}"
PASSWORD="${PASSWORD:-OwnerPass123}"
GUEST_EMAIL="smoke-$(date +%s)@test.com"
GUEST_PASS="GuestPass123"

SMOKE="$HOME/platform-x/logs/smoke"
mkdir -p "$SMOKE"

pass=0; fail=0
ok() { echo "  ✔ $1"; pass=$((pass+1)); }
ko() { echo "  ✘ $1"; fail=$((fail+1)); }
get() { python3 -c "import json;d=json.load(open('$SMOKE/r.json'));print($1)" 2>/dev/null || echo ""; }

echo "Platform-X — Reviews smoke"
echo "BASE=$BASE  SLUG=$SLUG"
echo ""

echo "▶ 1) Business login"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" -X POST "$BASE/business/api/auth/login" -H "X-Tenant-Slug: $SLUG" -H "Content-Type: application/json" -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
BTOK=$(get "d.get('access_token','')")
[ "$c" = "200" ] && [ -n "$BTOK" ] && ok "login 200" || { ko "login $c"; exit 1; }

echo "▶ 2) Register guest"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" -X POST "$BASE/auth/register" -H "X-Tenant-Slug: $SLUG" -H "Content-Type: application/json" -d "{\"email\":\"$GUEST_EMAIL\",\"password\":\"$GUEST_PASS\",\"first_name\":\"S\",\"last_name\":\"G\"}")
GTOK=$(get "d.get('access_token','')")
[ "$c" = "201" ] && [ -n "$GTOK" ] && ok "register 201" || ko "register $c"

echo "▶ 3) Guest creates review"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" -X POST "$BASE/reviews" -H "X-Tenant-Slug: $SLUG" -H "Content-Type: application/json" -H "Authorization: Bearer $GTOK" -d '{"rating":5,"content":"Smoke review - amazing stay, loved it"}')
RID=$(get "d.get('id','')")
SENT=$(get "d.get('sentiment','')")
[ "$c" = "201" ] && [ -n "$RID" ] && ok "create 201 sentiment=$SENT" || ko "create $c"

echo "▶ 4) Public list shows review"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" "$BASE/reviews/tenant/$SLUG")
FOUND=$(get "any(x['id']=='$RID' for x in d.get('items',[]))")
[ "$c" = "200" ] && [ "$FOUND" = "True" ] && ok "public contains it" || ko "public $c found=$FOUND"

echo "▶ 5) Business summary"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" -X GET "$BASE/business/api/reviews/summary" -H "X-Tenant-Slug: $SLUG" -H "Authorization: Bearer $BTOK")
TOT=$(get "d.get('total',0)")
[ "$c" = "200" ] && [ "$TOT" -ge "1" ] && ok "summary 200 total=$TOT" || ko "summary $c total=$TOT"

echo "▶ 6) AI respond preview"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" -X POST "$BASE/business/api/reviews/$RID/respond/preview" -H "X-Tenant-Slug: $SLUG" -H "Content-Type: application/json" -H "Authorization: Bearer $BTOK" -d '{"language":"en","tone":"professional"}')
LEN=$(get "len(d.get('content',''))")
PROV=$(get "d.get('provider','')")
[ "$c" = "200" ] && [ "$LEN" -gt "10" ] && ok "preview 200 ${LEN}chars provider=$PROV" || ko "preview $c"

echo "▶ 7) Business responds (AI)"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" -X POST "$BASE/business/api/reviews/$RID/respond" -H "X-Tenant-Slug: $SLUG" -H "Content-Type: application/json" -H "Authorization: Bearer $BTOK" -d '{"response_text":null,"language":"en","tone":"professional","use_ai":true}')
LEN=$(get "len(d.get('response_text',''))")
PROV=$(get "d.get('response_provider','')")
[ "$c" = "200" ] && [ "$LEN" -gt "10" ] && ok "respond 200 ${LEN}chars provider=$PROV" || ko "respond $c"

echo "▶ 8) Tenant page has reviews section"
c=$(curl -sS -o "$SMOKE/p.html" -w "%{http_code}" "$BASE/$SLUG/")
HAS=$(grep -c "Guest reviews" "$SMOKE/p.html")
[ "$c" = "200" ] && [ "$HAS" -ge "1" ] && ok "page 200 section present" || ko "page $c has=$HAS"

echo "▶ 9) Business hides review"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" -X POST "$BASE/business/api/reviews/$RID/hide" -H "X-Tenant-Slug: $SLUG" -H "Authorization: Bearer $BTOK")
ST=$(get "d.get('status','')")
[ "$c" = "200" ] && [ "$ST" = "hidden" ] && ok "hide 200" || ko "hide $c st=$ST"

echo "▶ 10) Public no longer contains it"
c=$(curl -sS -o "$SMOKE/r.json" -w "%{http_code}" "$BASE/reviews/tenant/$SLUG")
FOUND=$(get "any(x['id']=='$RID' for x in d.get('items',[]))")
[ "$c" = "200" ] && [ "$FOUND" = "False" ] && ok "hidden removed from public" || ko "public $c found=$FOUND"

echo "▶ 11) Auth guard"
c=$(curl -sS -o /dev/null -w "%{http_code}" -X GET "$BASE/business/api/reviews" -H "X-Tenant-Slug: $SLUG")
[ "$c" = "401" ] && ok "no token 401" || ko "no token $c"

echo "▶ 12) Business page renders"
c=$(curl -sS -o "$SMOKE/bp.html" -w "%{http_code}" "$BASE/business/reviews")
HAS=$(grep -c "Guest Reviews" "$SMOKE/bp.html")
[ "$c" = "200" ] && [ "$HAS" -ge "1" ] && ok "page 200" || ko "page $c"

echo ""
echo "RESULT: $pass passed, $fail failed"
[ "$fail" -eq 0 ] && exit 0 || exit 1
