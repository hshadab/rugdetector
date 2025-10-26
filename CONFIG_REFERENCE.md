# Configuration Reference

This document provides a quick reference for all API keys and configuration values used in RugDetector.

## Configuration Files

### `.env` - Local Development
Your main configuration file for local development. Contains all API keys and settings.

### `.env.example` - Template
Template file with placeholder values. Safe to commit to git. Use this to create your own `.env` file.

### `.env.render` - Render.com Reference
**⚠️ DO NOT COMMIT TO GIT** - Contains actual production values from Render.com deployment.

---

## Quick Reference

### Alchemy API
- **Dashboard**: https://dashboard.alchemy.com/
- **API Key**: `7OimkSMssMZr7nYzzenak`
- **Base RPC**: `https://base-mainnet.g.alchemy.com/v2/7OimkSMssMZr7nYzzenak`
- **Solana RPC**: `https://solana-mainnet.g.alchemy.com/v2/7OimkSMssMZr7nYzzenak`

### Coinbase Developer Platform (CDP)
- **Dashboard**: https://portal.cdp.coinbase.com/
- **API Key ID**: `93d8abc8-7555-44e0-a634-aafa4e1b0fb6`
- **API Key Secret**: `tJrg42SpprPI+uMhSRjBpBElJJb0XdmQrqJSa2xqZtKRrusz/xuKjtVxmMTnpRBl8Jh3QKJ1KoNIn6LzxFi3Mw==`

### Moralis API
- **Dashboard**: https://admin.moralis.io/
- **API Key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (JWT token)

### The Graph API
- **Dashboard**: https://thegraph.com/studio/
- **API Key**: `e3af3c542937403f686cf2f277a05820`

### Payment Configuration
- **Payment Address**: `0x1f409E94684804e5158561090Ced8941B47B0CC6`
- **USDC Contract** (Base): `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- **Payment Amount**: `10000` (0.01 USDC in units)

### Render.com
- **Dashboard**: https://dashboard.render.com/web/srv-d3uh21v5r7bs73fhq05g
- **Service ID**: `srv-d3uh21v5r7bs73fhq05g`
- **API Key**: `rnd_1qYdkGuHRHGB13aorQUdxwaE9GE2`
- **Service URL**: https://rugdetector-0i4y.onrender.com

---

## API Keys to Add (Optional)

These are currently empty but can enhance feature extraction:

### Basescan API Key
- **Get free key**: https://basescan.org/apis
- **Purpose**: Better Base network contract analysis
- **Current value**: Empty

### Solscan API Key
- **Get free key**: https://pro-api.solscan.io
- **Purpose**: Better Solana network program analysis
- **Current value**: Empty

---

## Supported Networks

- ✅ **Base** (Coinbase L2) - Primary chain
- ✅ **Solana** - Secondary chain
- ❌ Ethereum - Removed
- ❌ BSC - Removed
- ❌ Polygon - Removed

---

## File Locations

```
/home/hshadab/rugdetector/
├── .env                    # Local development config (DO NOT COMMIT)
├── .env.example            # Template (safe to commit)
├── .env.render             # Render production values (DO NOT COMMIT)
├── CONFIG_REFERENCE.md     # This file
└── RENDER_BASE_SOLANA_UPDATE.md  # Deployment details
```

---

## Environment Variables List

| Variable | Value | Source |
|----------|-------|--------|
| `PORT` | `3000` | Standard |
| `NODE_ENV` | `production` | Render |
| `PAYMENT_ADDRESS` | `0x1f409E94684804e5158561090Ced8941B47B0CC6` | Your wallet |
| `CDP_API_KEY_ID` | `93d8abc8-7555-44e0-a634-aafa4e1b0fb6` | Coinbase CDP |
| `CDP_API_KEY_SECRET` | `tJrg42SpprPI+...` | Coinbase CDP |
| `BASE_RPC_URL` | `https://base-mainnet.g.alchemy.com/v2/7OimkSMssMZr7nYzzenak` | Alchemy |
| `SOLANA_RPC_URL` | `https://solana-mainnet.g.alchemy.com/v2/7OimkSMssMZr7nYzzenak` | Alchemy |
| `BASESCAN_API_KEY` | (empty) | Optional |
| `SOLSCAN_API_KEY` | (empty) | Optional |
| `MORALIS_API_KEY` | `eyJhbGci...` | Moralis |
| `THE_GRAPH_API_KEY` | `e3af3c542937403f686cf2f277a05820` | The Graph |
| `USDC_CONTRACT_ADDRESS` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | Base USDC |
| `PAYMENT_AMOUNT` | `10000` | 0.01 USDC |

---

## Security Notes

⚠️ **Never commit these files to git**:
- `.env`
- `.env.render`
- Any file containing actual API keys

✅ **Safe to commit**:
- `.env.example`
- `CONFIG_REFERENCE.md`
- Documentation files

---

## Updating Render Environment Variables

### Via Dashboard (Easiest)
1. Go to https://dashboard.render.com/web/srv-d3tqk1mr433s73dtdec0
2. Click "Environment" tab
3. Edit variables
4. Save (auto-deploys)

### Via API
```bash
curl -X PUT \
  -H "Authorization: Bearer rnd_1qYdkGuHRHGB13aorQUdxwaE9GE2" \
  -H "Content-Type: application/json" \
  -d '[{"key":"BASE_RPC_URL","value":"YOUR_VALUE"}]' \
  "https://api.render.com/v1/services/srv-d3uh21v5r7bs73fhq05g/env-vars"
```

---

Last updated: 2025-10-26
