#!/bin/bash

# Create wallet using CDP REST API
curl -X POST "https://api.cdp.coinbase.com/platform/v1/wallets" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 93d8abc8-7555-44e0-a634-aafa4e1b0fb6:tJrg42SpprPI+uMhSRjBpBElJJb0XdmQrqJSa2xqZtKRrusz/xuKjtVxmMTnpRBl8Jh3QKJ1KoNIn6LzxFi3Mw==" \
  -d '{
    "wallet": {
      "network_id": "base-mainnet"
    }
  }'
