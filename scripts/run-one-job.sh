#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${ORCHESTRATOR_URL:-http://localhost:3000}"
TOPIC="${1:-5 surprising psychology facts about first impressions}"
PLATFORM="${2:-youtube}"

echo "=== AI Brain — Run One Job ==="

# 1. Get brand
echo "1. Getting default brand..."
BRAND_ID=$(curl -sf "$BASE_URL/api/v1/brands" | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']
print(d[0]['id'] if d else '')
" 2>/dev/null)

if [ -z "$BRAND_ID" ]; then
    echo "   ERROR: No brands found. Run 'make db-seed' first."
    exit 1
fi
echo "   Brand: $BRAND_ID"

# 2. Create job
echo "2. Creating job..."
JOB=$(curl -sf -X POST "$BASE_URL/api/v1/jobs" \
    -H "Content-Type: application/json" \
    -d "{
        \"brand_id\": \"$BRAND_ID\",
        \"platform\": \"$PLATFORM\",
        \"platform_target_date\": \"$(date +%Y-%m-%d)\",
        \"topic\": \"$TOPIC\"
    }")

JOB_ID=$(echo "$JOB" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "   Job ID: $JOB_ID"
echo "   State:  $(echo "$JOB" | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")"

# 3. Trigger pipeline steps
echo "3. Running pipeline..."

for STATE in RESEARCHING WRITING AUDITING RENDERING UPLOADING POSTED; do
    echo -n "   -> $STATE... "
    RESULT=$(curl -sf -X PATCH "$BASE_URL/api/v1/jobs/$JOB_ID/state" \
        -H "Content-Type: application/json" \
        -d "{\"target_state\": \"$STATE\", \"message\": \"Manual pipeline run\"}" 2>&1)

    STATUS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('state', 'ERROR'))" 2>/dev/null || echo "ERROR")
    echo "$STATUS"

    if [ "$STATUS" = "ERROR" ] || [ "$STATUS" = "FAILED" ]; then
        echo "   Pipeline stopped at $STATE"
        break
    fi
    sleep 1
done

# 4. Final status
echo ""
echo "4. Final job status:"
curl -sf "$BASE_URL/api/v1/jobs/$JOB_ID" | python3 -c "
import sys, json
j = json.load(sys.stdin)
print(f\"   State: {j['state']}\")
print(f\"   Video: {j.get('video_url', 'N/A')}\")
print(f\"   Cost:  \${j.get('openai_cost_usd', 0):.4f}\")
"
echo ""
echo "=== Done ==="
