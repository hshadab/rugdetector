#!/bin/bash
echo "Monitoring deployment..."
echo "Old version has 'demo mode' mention in error"
echo "New version has CDP x402Version in response"
echo ""

for i in {1..12}; do
  echo "[$i/12] Checking at $(date +%H:%M:%S)..."
  
  RESPONSE=$(curl -s https://rugdetector.ai/check \
    -H "Content-Type: application/json" \
    -d '{"contract_address":"0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"}')
  
  if echo "$RESPONSE" | grep -q "x402Version"; then
    echo "🎉 NEW CDP VERSION IS LIVE!"
    echo "$RESPONSE" | jq '{x402Version, error, discoverable: .accepts[0].outputSchema.input.discoverable}'
    exit 0
  elif echo "$RESPONSE" | grep -q "demo mode"; then
    echo "   Still old version (has demo mode)"
  fi
  
  if [ $i -lt 12 ]; then
    sleep 30
  fi
done

echo "⏰ Timeout - deployment still not live after 6 minutes"
