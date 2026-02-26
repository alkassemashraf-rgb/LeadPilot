#!/usr/bin/env bash
# ============================================================================
# Mission 14 — Entitlements Smoke Test
# Curl-based E2E test verifying the entitlements pipeline end-to-end.
#
# Usage:
#   ./scripts/smoke_entitlements.sh [BASE_URL]
#
# Defaults to http://localhost:8000 if no BASE_URL provided.
# Requires an admin user to exist (ADMIN_EMAIL / ADMIN_PASSWORD env vars).
# ============================================================================
set -euo pipefail

BASE="${1:-http://localhost:8000}"
API="${BASE}/api/v1"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@leadpilot.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"

PASS=0
FAIL=0
TOTAL=0

# ---------- helpers ----------------------------------------------------------

green()  { printf "\033[32m%s\033[0m\n" "$1"; }
red()    { printf "\033[31m%s\033[0m\n" "$1"; }
yellow() { printf "\033[33m%s\033[0m\n" "$1"; }

assert_eq() {
    TOTAL=$((TOTAL + 1))
    local label="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        green "  ✓ $label"
        PASS=$((PASS + 1))
    else
        red "  ✗ $label — expected '$expected', got '$actual'"
        FAIL=$((FAIL + 1))
    fi
}

assert_contains() {
    TOTAL=$((TOTAL + 1))
    local label="$1" needle="$2" haystack="$3"
    if echo "$haystack" | grep -q "$needle"; then
        green "  ✓ $label"
        PASS=$((PASS + 1))
    else
        red "  ✗ $label — '$needle' not found in response"
        FAIL=$((FAIL + 1))
    fi
}

assert_gte() {
    TOTAL=$((TOTAL + 1))
    local label="$1" expected="$2" actual="$3"
    if [ "$actual" -ge "$expected" ] 2>/dev/null; then
        green "  ✓ $label (got $actual >= $expected)"
        PASS=$((PASS + 1))
    else
        red "  ✗ $label — expected >= $expected, got '$actual'"
        FAIL=$((FAIL + 1))
    fi
}

# ---------- 1. Admin login ---------------------------------------------------

echo ""
yellow "═══════════════════════════════════════════════════"
yellow "  Mission 14 — Entitlements Smoke Test"
yellow "  Target: $BASE"
yellow "═══════════════════════════════════════════════════"
echo ""

echo "► Step 1: Admin login"
LOGIN_RES=$(curl -s -X POST "${API}/admin_auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"${ADMIN_EMAIL}\", \"password\": \"${ADMIN_PASSWORD}\"}")

ADMIN_TOKEN=$(echo "$LOGIN_RES" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('access_token','') or d.get('access_token',''))" 2>/dev/null || echo "")

if [ -z "$ADMIN_TOKEN" ]; then
    red "  ✗ Admin login failed. Response: $LOGIN_RES"
    red "  Set ADMIN_EMAIL and ADMIN_PASSWORD env vars if needed."
    exit 1
fi
green "  ✓ Admin logged in"

AUTH="Authorization: Bearer ${ADMIN_TOKEN}"

# ---------- 2. List plans (expect >= 3) --------------------------------------

echo ""
echo "► Step 2: List plans"
PLANS_RES=$(curl -s -X GET "${API}/admin/plans" -H "$AUTH")
PLAN_COUNT=$(echo "$PLANS_RES" | python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d.get('data', {}).get('items', d.get('data', []))
if isinstance(items, list):
    print(len(items))
else:
    print(0)
" 2>/dev/null || echo "0")

assert_gte "Plans list has >= 3 plans" 3 "$PLAN_COUNT"

# Extract plan IDs for later use
PLAN_IDS=$(echo "$PLANS_RES" | python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d.get('data', {}).get('items', d.get('data', []))
if isinstance(items, list):
    for p in items:
        print(p.get('name',''), p.get('id',''))
" 2>/dev/null || echo "")

FREE_PLAN_ID=$(echo "$PLAN_IDS" | grep "^free " | awk '{print $2}')
GROWTH_PLAN_ID=$(echo "$PLAN_IDS" | grep "^growth " | awk '{print $2}')

if [ -n "$FREE_PLAN_ID" ]; then
    green "  ✓ Free plan found: $FREE_PLAN_ID"
else
    yellow "  ⚠ Could not find free plan ID"
fi

if [ -n "$GROWTH_PLAN_ID" ]; then
    green "  ✓ Growth plan found: $GROWTH_PLAN_ID"
else
    yellow "  ⚠ Could not find growth plan ID"
fi

# ---------- 3. Get plan detail -----------------------------------------------

echo ""
echo "► Step 3: Plan detail (free)"
if [ -n "$FREE_PLAN_ID" ]; then
    PLAN_DETAIL=$(curl -s -X GET "${API}/admin/plans/${FREE_PLAN_ID}" -H "$AUTH")
    assert_contains "Free plan detail contains entitlements" "entitlements" "$PLAN_DETAIL"

    ENT_COUNT=$(echo "$PLAN_DETAIL" | python3 -c "
import sys, json
d = json.load(sys.stdin)
detail = d.get('data', {})
ents = detail.get('entitlements', [])
print(len(ents))
" 2>/dev/null || echo "0")
    assert_gte "Free plan has >= 5 entitlements" 5 "$ENT_COUNT"
else
    yellow "  ⚠ Skipped — no free plan ID"
fi

# ---------- 4. List workspaces ------------------------------------------------

echo ""
echo "► Step 4: List workspaces"
WS_RES=$(curl -s -X GET "${API}/admin/workspaces?limit=5" -H "$AUTH")
assert_contains "Workspaces endpoint returns data" "success" "$WS_RES"

FIRST_WS_ID=$(echo "$WS_RES" | python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d.get('data', {}).get('items', [])
if items:
    print(items[0].get('id', ''))
else:
    print('')
" 2>/dev/null || echo "")

if [ -n "$FIRST_WS_ID" ]; then
    green "  ✓ Found workspace: $FIRST_WS_ID"
else
    yellow "  ⚠ No workspaces found — some tests will be skipped"
fi

# ---------- 5. Get workspace plan ---------------------------------------------

echo ""
echo "► Step 5: Workspace plan"
if [ -n "$FIRST_WS_ID" ]; then
    WS_PLAN_RES=$(curl -s -X GET "${API}/admin/workspaces/${FIRST_WS_ID}/plan" -H "$AUTH")
    assert_contains "Workspace plan endpoint returns data" "success" "$WS_PLAN_RES"
    assert_contains "Workspace has a plan assigned" "plan" "$WS_PLAN_RES"
else
    yellow "  ⚠ Skipped — no workspace available"
fi

# ---------- 6. Assign growth plan to workspace --------------------------------

echo ""
echo "► Step 6: Assign growth plan"
if [ -n "$FIRST_WS_ID" ] && [ -n "$GROWTH_PLAN_ID" ]; then
    ASSIGN_RES=$(curl -s -X PUT "${API}/admin/workspaces/${FIRST_WS_ID}/plan" \
        -H "$AUTH" \
        -H "Content-Type: application/json" \
        -d "{\"plan_id\": \"${GROWTH_PLAN_ID}\"}")
    assert_contains "Plan assignment succeeded" "success" "$ASSIGN_RES"

    # Verify the plan changed
    VERIFY_RES=$(curl -s -X GET "${API}/admin/workspaces/${FIRST_WS_ID}/plan" -H "$AUTH")
    ASSIGNED_PLAN=$(echo "$VERIFY_RES" | python3 -c "
import sys, json
d = json.load(sys.stdin)
plan = d.get('data', {}).get('plan', {})
print(plan.get('name', ''))
" 2>/dev/null || echo "")
    assert_eq "Workspace now on growth plan" "growth" "$ASSIGNED_PLAN"
else
    yellow "  ⚠ Skipped — missing workspace or growth plan"
fi

# ---------- 7. Check workspace usage ------------------------------------------

echo ""
echo "► Step 7: Workspace usage"
if [ -n "$FIRST_WS_ID" ]; then
    USAGE_RES=$(curl -s -X GET "${API}/admin/workspaces/${FIRST_WS_ID}/usage" -H "$AUTH")
    assert_contains "Usage endpoint returns data" "success" "$USAGE_RES"
else
    yellow "  ⚠ Skipped — no workspace available"
fi

# ---------- 8. Set workspace override -----------------------------------------

echo ""
echo "► Step 8: Workspace override"
if [ -n "$FIRST_WS_ID" ]; then
    OVERRIDE_RES=$(curl -s -X PUT "${API}/admin/workspaces/${FIRST_WS_ID}/overrides" \
        -H "$AUTH" \
        -H "Content-Type: application/json" \
        -d '{"overrides": [{"module_key": "prompt_studio", "hard_limit": 999}]}')
    assert_contains "Override set succeeded" "success" "$OVERRIDE_RES"

    # Verify override is reflected in plan data
    PLAN_AFTER=$(curl -s -X GET "${API}/admin/workspaces/${FIRST_WS_ID}/plan" -H "$AUTH")
    assert_contains "Override reflected in plan response" "override" "$PLAN_AFTER"

    # Clean up override
    curl -s -X DELETE "${API}/admin/workspaces/${FIRST_WS_ID}/overrides/prompt_studio" \
        -H "$AUTH" > /dev/null 2>&1
    green "  ✓ Override cleaned up"
else
    yellow "  ⚠ Skipped — no workspace available"
fi

# ---------- 9. Restore workspace to free plan ---------------------------------

echo ""
echo "► Step 9: Restore workspace to free plan"
if [ -n "$FIRST_WS_ID" ] && [ -n "$FREE_PLAN_ID" ]; then
    RESTORE_RES=$(curl -s -X PUT "${API}/admin/workspaces/${FIRST_WS_ID}/plan" \
        -H "$AUTH" \
        -H "Content-Type: application/json" \
        -d "{\"plan_id\": \"${FREE_PLAN_ID}\"}")
    assert_contains "Plan restored to free" "success" "$RESTORE_RES"
else
    yellow "  ⚠ Skipped — missing workspace or free plan"
fi

# ---------- Summary -----------------------------------------------------------

echo ""
yellow "═══════════════════════════════════════════════════"
if [ "$FAIL" -eq 0 ]; then
    green "  ALL $TOTAL CHECKS PASSED ($PASS/$TOTAL)"
else
    red "  $FAIL FAILED, $PASS PASSED ($TOTAL total)"
fi
yellow "═══════════════════════════════════════════════════"
echo ""

exit "$FAIL"
