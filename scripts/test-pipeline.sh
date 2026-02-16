#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${ORCHESTRATOR_URL:-http://localhost:3000}"
AI_URL="${AI_SERVICES_URL:-http://localhost:8000}"
RENDERER_URL="${RENDERER_URL:-http://localhost:8001}"

echo "=== AI Brain Pipeline Smoke Test ==="

# 1. Health checks
echo ""
echo "1. Checking service health..."
echo "   Orchestrator: $(curl -sf "$BASE_URL/api/v1/health" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo 'UNREACHABLE')"
echo "   AI Services:  $(curl -sf "$AI_URL/api/v1/health" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo 'UNREACHABLE')"
echo "   Renderer:     $(curl -sf "$RENDERER_URL/api/v1/health" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo 'UNREACHABLE')"

# 2. Get or create brand
echo ""
echo "2. Getting default brand..."
BRAND_ID=$(curl -sf "$BASE_URL/api/v1/brands" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(d[0]['id'] if d else '')" 2>/dev/null)

if [ -z "$BRAND_ID" ]; then
    echo "   No brands found. Create one first via seed data."
    exit 1
fi
echo "   Brand ID: $BRAND_ID"

# 3. Create a test job
echo ""
echo "3. Creating test job..."
JOB=$(curl -sf -X POST "$BASE_URL/api/v1/jobs" \
    -H "Content-Type: application/json" \
    -d "{
        \"brand_id\": \"$BRAND_ID\",
        \"platform\": \"youtube\",
        \"platform_target_date\": \"$(date +%Y-%m-%d)\",
        \"topic\": \"5 amazing facts about space that will blow your mind\"
    }")

JOB_ID=$(echo "$JOB" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "   Job ID: $JOB_ID"
echo "   State:  $(echo "$JOB" | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")"

# 4. Check budget
echo ""
echo "4. Checking daily budget..."
curl -sf "$BASE_URL/api/v1/budget/daily" | python3 -c "
import sys, json
b = json.load(sys.stdin)
print(f\"   Spent: \${b['spent_usd']:.2f} / \${b['max_budget_usd']:.2f} ({b['percent_used']:.1f}%)\")
"

# 5. Transition to RESEARCHING then FAILED (test state machine)
echo ""
echo "5. Testing state machine..."
curl -sf -X PATCH "$BASE_URL/api/v1/jobs/$JOB_ID/state" \
    -H "Content-Type: application/json" \
    -d '{"target_state": "RESEARCHING", "message": "Smoke test"}' > /dev/null

echo "   QUEUED -> RESEARCHING: OK"

curl -sf -X PATCH "$BASE_URL/api/v1/jobs/$JOB_ID/state" \
    -H "Content-Type: application/json" \
    -d '{"target_state": "FAILED", "message": "Smoke test failure"}' > /dev/null

echo "   RESEARCHING -> FAILED: OK"

# 6. Check state log
echo ""
echo "6. State log entries:"
curl -sf "$BASE_URL/api/v1/jobs/$JOB_ID/log" | python3 -c "
import sys, json
for entry in json.load(sys.stdin)['data']:
    print(f\"   {entry['from_state'] or 'null'} -> {entry['to_state']}: {entry.get('message', '')}\")
"

echo ""
echo "=== Smoke test complete ==="
