#!/bin/bash
echo "Monitoring deployment dep-d3uil7ndiees73eahrd0..."
echo ""

for i in {1..30}; do
  echo "[$i/30] Checking deployment status..."

  STATUS=$(curl -s "https://api.render.com/v1/services/srv-d3uh21v5r7bs73fhq05g/deploys/dep-d3uil7ndiees73eahrd0" \
    -H "Authorization: Bearer rnd_1qYdkGuHRHGB13aorQUdxwaE9GE2")

  DEPLOY_STATUS=$(echo "$STATUS" | jq -r '.status')

  echo "   Status: $DEPLOY_STATUS"

  if [ "$DEPLOY_STATUS" = "live" ]; then
    echo ""
    echo "========================================="
    echo "✅ DEPLOYMENT IS LIVE!"
    echo "========================================="
    echo ""
    sleep 5
    echo "Testing ONNX fix..."
    curl -s https://rugdetector.ai/check \
      -H "Content-Type: application/json" \
      -d '{"payment_id":"final_test","contract_address":"0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984","blockchain":"ethereum"}' \
      | jq '{success, error, riskScore: .result.riskScore}'
    exit 0
  elif [ "$DEPLOY_STATUS" = "build_failed" ] || [ "$DEPLOY_STATUS" = "deploy_failed" ]; then
    echo ""
    echo "❌ DEPLOYMENT FAILED: $DEPLOY_STATUS"
    echo "$STATUS" | jq '.'
    exit 1
  fi

  if [ $i -lt 30 ]; then
    sleep 20
  fi
done

echo ""
echo "⏰ Timeout - deployment still not live after 10 minutes"
