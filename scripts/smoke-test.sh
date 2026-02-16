#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${ORCHESTRATOR_URL:-http://localhost:3000}"
AI_URL="${AI_SERVICES_URL:-http://localhost:8000}"
RENDERER_URL="${RENDERER_URL:-http://localhost:8001}"
PASS=0
FAIL=0

check() {
    local name="$1"
    local result="$2"
    if [ "$result" = "0" ]; then
        echo "  ✓ $name"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $name"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== AI Brain Pipeline Smoke Test ==="
echo ""

# 1. Health checks
echo "1. Service Health"
curl -sf "$BASE_URL/api/v1/health" > /dev/null 2>&1; check "Orchestrator" "$?"
curl -sf "$AI_URL/api/v1/health" > /dev/null 2>&1; check "AI Services" "$?"
curl -sf "$RENDERER_URL/api/v1/health" > /dev/null 2>&1; check "Renderer" "$?"

# 2. Brand exists
echo ""
echo "2. Brand Configuration"
BRAND_ID=$(curl -sf "$BASE_URL/api/v1/brands" | python3 -c "
import sys,json
d=json.load(sys.stdin)['data']
print(d[0]['id'] if d else '')
" 2>/dev/null)
[ -n "$BRAND_ID" ]; check "Default brand exists" "$?"

# 3. Job creation and state machine
echo ""
echo "3. Job State Machine"
JOB=$(curl -sf -X POST "$BASE_URL/api/v1/jobs" \
    -H "Content-Type: application/json" \
    -d "{
        \"brand_id\": \"$BRAND_ID\",
        \"platform\": \"youtube\",
        \"platform_target_date\": \"$(date +%Y-%m-%d)\",
        \"topic\": \"Smoke test: $(date +%s)\"
    }" 2>/dev/null)
JOB_ID=$(echo "$JOB" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)
[ -n "$JOB_ID" ]; check "Create job" "$?"

# Test state transitions
curl -sf -X PATCH "$BASE_URL/api/v1/jobs/$JOB_ID/state" \
    -H "Content-Type: application/json" \
    -d '{"target_state": "RESEARCHING"}' > /dev/null 2>&1; check "QUEUED -> RESEARCHING" "$?"

curl -sf -X PATCH "$BASE_URL/api/v1/jobs/$JOB_ID/state" \
    -H "Content-Type: application/json" \
    -d '{"target_state": "WRITING"}' > /dev/null 2>&1; check "RESEARCHING -> WRITING" "$?"

curl -sf -X PATCH "$BASE_URL/api/v1/jobs/$JOB_ID/state" \
    -H "Content-Type: application/json" \
    -d '{"target_state": "FAILED", "message": "Smoke test"}' > /dev/null 2>&1; check "WRITING -> FAILED" "$?"

# 4. Budget endpoint
echo ""
echo "4. Budget & Analytics"
curl -sf "$BASE_URL/api/v1/budget/daily" > /dev/null 2>&1; check "Budget endpoint" "$?"

# 5. AI Services endpoints
echo ""
echo "5. AI Service Endpoints"
curl -sf "$AI_URL/docs" > /dev/null 2>&1; check "API docs (OpenAPI)" "$?"

# 6. New endpoints (rotation, hook gate, assets, reports)
echo ""
echo "6. New Feature Endpoints"
curl -sf "$AI_URL/api/v1/rotation/check" -X POST \
    -H "Content-Type: application/json" \
    -d "{\"brand_id\": \"$BRAND_ID\", \"proposed_content_type\": \"quote\", \"proposed_hook_archetype\": \"curiosity\", \"proposed_visual_family\": \"cinematic_quote\"}" > /dev/null 2>&1
check "Rotation check" "$?"

curl -sf "$AI_URL/api/v1/assets/usage/$BRAND_ID" > /dev/null 2>&1; check "Asset usage caps" "$?"

# Summary
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
