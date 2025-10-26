#!/bin/bash
echo "========================================="
echo "CDP DEPLOYMENT MONITOR"
echo "========================================="
echo "Looking for CDP facilitator (x402Version field)"
echo "Old version has: 'demo mode' in error"
echo "New version has: x402Version field"
echo ""

for i in {1..24}; do
  echo "[$i/24] Checking at $(date +%H:%M:%S)..."
  
  RESPONSE=$(curl -s https://rugdetector.ai/check \
    -H "Content-Type: application/json" \
    -d '{"contract_address":"0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"}')
  
  # Check for CDP version (new)
  if echo "$RESPONSE" | grep -q "x402Version"; then
    echo ""
    echo "========================================="
    echo "🎉 NEW CDP VERSION IS LIVE!"
    echo "========================================="
    echo ""
    echo "Full response:"
    echo "$RESPONSE" | jq '.'
    echo ""
    echo "Key fields:"
    echo "$RESPONSE" | jq '{x402Version, error, discoverable: .accepts[0].config.discoverable}'
    exit 0
  # Check for old version (demo mode)
  elif echo "$RESPONSE" | grep -q "demo mode"; then
    echo "   ⏳ Still old version (has demo mode)"
  # Unknown response
  else
    echo "   ❓ Unexpected response format"
    echo "$RESPONSE" | jq -r '.error' 2>/dev/null || echo "$RESPONSE"
  fi
  
  if [ $i -lt 24 ]; then
    sleep 30
  fi
done

echo ""
echo "========================================="
echo "⏰ TIMEOUT - 12 minutes elapsed"
echo "========================================="
echo "Deployment may still be in progress."
echo "Check Render dashboard for details."
