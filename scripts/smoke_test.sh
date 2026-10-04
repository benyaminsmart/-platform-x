#!/usr/bin/env bash
# Platform-X — smoke test for a running instance.
# Usage: bash scripts/smoke_test.sh https://your-domain.example
set -euo pipefail
BASE="${1:?usage: smoke_test.sh <base_url>}"
PASS=0; FAIL=0
check() {
    local name="$1" url="$2" expect="${3:-200}"
    local code
    code="$(curl -s -o /dev/null -w '%{http_code}' "$url" || echo 000)"
    if [[ "$code" == "$expect" ]]; then
        printf "  [OK]   %-30s %s\n" "$name" "$code"; PASS=$((PASS+1))
    else
        printf "  [FAIL] %-30s got=%s want=%s\n" "$name" "$code" "$expect"; FAIL=$((FAIL+1))
    fi
}
echo "=== Platform-X Smoke Test ==="
echo "target: $BASE"
echo
echo "--- public pages ---"
check "home" "$BASE/"
check "about" "$BASE/about"
check "login page" "$BASE/login"
check "register page" "$BASE/register"
check "search page" "$BASE/search"
check "docs/api" "$BASE/docs/api"
check "wallet page" "$BASE/account/wallet"
echo
echo "--- API (public) ---"
check "health" "$BASE/health" 200
check "api docs" "$BASE/docs" 200
check "openapi" "$BASE/openapi.json" 200
echo
echo "--- auth ---"
check "register endpoint" "$BASE/auth/register" 405
echo
echo "=== RESULT: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]] || exit 1
