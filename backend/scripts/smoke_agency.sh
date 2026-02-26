#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Mission 15 — Agency Smoke Test
# Requires: backend running on localhost:8000, jq installed
# Usage: bash scripts/smoke_agency.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

BASE="http://localhost:8000/api/v1"
PASS=0
FAIL=0

check() {
    local label="$1" actual="$2" expected="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  [PASS] $label"
        PASS=$((PASS + 1))
    else
        echo "  [FAIL] $label — expected '$expected', got '$actual'"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Mission 15: Agency Smoke Test ==="
echo ""

# 1. Sign up two users (agency owner + operator)
echo "--- Step 1: Sign up users ---"
OWNER_RES=$(curl -s -X POST "$BASE/auth/signup" \
    -H "Content-Type: application/json" \
    -d '{"email":"agency_smoke_owner@test.com","password":"pass1234","full_name":"Smoke Owner"}')
check "Owner signup" "$(echo "$OWNER_RES" | jq -r '.success')" "true"

OPERATOR_RES=$(curl -s -X POST "$BASE/auth/signup" \
    -H "Content-Type: application/json" \
    -d '{"email":"agency_smoke_op@test.com","password":"pass1234","full_name":"Smoke Operator"}')
check "Operator signup" "$(echo "$OPERATOR_RES" | jq -r '.success')" "true"

# Login as owner
OWNER_LOGIN=$(curl -s -X POST "$BASE/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=agency_smoke_owner@test.com&password=pass1234")
OWNER_TOKEN=$(echo "$OWNER_LOGIN" | jq -r '.data.access_token')
AUTH_OWNER="Authorization: Bearer $OWNER_TOKEN"

echo ""
echo "--- Step 2: Create agency ---"
CREATE_AGENCY=$(curl -s -X POST "$BASE/agency/create" \
    -H "$AUTH_OWNER" -H "Content-Type: application/json" \
    -d '{"name":"Smoke Test Agency"}')
check "Agency created" "$(echo "$CREATE_AGENCY" | jq -r '.success')" "true"
check "Agency name" "$(echo "$CREATE_AGENCY" | jq -r '.data.name')" "Smoke Test Agency"
AGENCY_ID=$(echo "$CREATE_AGENCY" | jq -r '.data.id')

echo ""
echo "--- Step 3: GET /agency/me ---"
ME_RES=$(curl -s "$BASE/agency/me" -H "$AUTH_OWNER")
check "Agency me" "$(echo "$ME_RES" | jq -r '.data.my_role')" "agency_owner"

echo ""
echo "--- Step 4: Invite operator ---"
INVITE_RES=$(curl -s -X POST "$BASE/agency/members/invite" \
    -H "$AUTH_OWNER" -H "Content-Type: application/json" \
    -d '{"email":"agency_smoke_op@test.com","role":"agency_operator"}')
check "Invite member" "$(echo "$INVITE_RES" | jq -r '.success')" "true"

echo ""
echo "--- Step 5: Create 2 client workspaces ---"
WS1=$(curl -s -X POST "$BASE/agency/workspaces" \
    -H "$AUTH_OWNER" -H "Content-Type: application/json" \
    -d '{"name":"Client Alpha"}')
check "WS1 created" "$(echo "$WS1" | jq -r '.success')" "true"
WS1_ID=$(echo "$WS1" | jq -r '.data.id')

WS2=$(curl -s -X POST "$BASE/agency/workspaces" \
    -H "$AUTH_OWNER" -H "Content-Type: application/json" \
    -d '{"name":"Client Beta"}')
check "WS2 created" "$(echo "$WS2" | jq -r '.success')" "true"
WS2_ID=$(echo "$WS2" | jq -r '.data.id')

echo ""
echo "--- Step 6: List agency workspaces ---"
LIST_WS=$(curl -s "$BASE/agency/workspaces" -H "$AUTH_OWNER")
WS_COUNT=$(echo "$LIST_WS" | jq -r '.data.total')
check "Workspace count" "$WS_COUNT" "2"

echo ""
echo "--- Step 7: Access workspace-scoped endpoint ---"
MEMBERS_WS1=$(curl -s "$BASE/workspaces/members" \
    -H "$AUTH_OWNER" -H "X-Workspace-ID: $WS1_ID")
check "WS1 members accessible" "$(echo "$MEMBERS_WS1" | jq -r '.success')" "true"

echo ""
echo "--- Step 8: Workspace isolation ---"
MEMBERS_WS2=$(curl -s "$BASE/workspaces/members" \
    -H "$AUTH_OWNER" -H "X-Workspace-ID: $WS2_ID")
check "WS2 members accessible" "$(echo "$MEMBERS_WS2" | jq -r '.success')" "true"

echo ""
echo "--- Step 9: List agency members ---"
MEM_LIST=$(curl -s "$BASE/agency/members" -H "$AUTH_OWNER")
MEM_COUNT=$(echo "$MEM_LIST" | jq -r '.data.total')
check "Member count is 2" "$MEM_COUNT" "2"

echo ""
echo "==================================================="
echo "  Agency Smoke Results: $PASS passed, $FAIL failed"
echo "==================================================="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
