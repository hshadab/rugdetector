# Alchemy API Setup Guide

## Why Use Alchemy?

**Alchemy provides superior blockchain access compared to public RPCs:**

| Feature | Public RPC | Alchemy |
|---------|------------|---------|
| **Rate Limits** | 10-50 req/sec (shared) | 300 req/sec (free tier) |
| **Reliability** | ⚠️ Often down | ✅ 99.9% uptime |
| **Performance** | Slow (shared) | Fast (dedicated) |
| **Archive Data** | Limited | Full archive access |
| **Support** | None | Email support |
| **Cost** | Free | Free tier + paid plans |

**For RugDetector**: Alchemy prevents rate limiting during feature extraction (which makes ~10-20 RPC calls per contract).

---

## Quick Start (5 Minutes)

### Step 1: Get Your Alchemy API Key

1. **Sign up**: Go to https://www.alchemy.com/
2. **Create account** (free, no credit card required)
3. **Create app**:
   - Dashboard → "Create App"
   - Name: "RugDetector"
   - Network: Ethereum Mainnet
   - Click "Create App"
4. **Get API key**:
   - Click on your app
   - Click "API Key" button
   - Copy the key (looks like: `AbC123XyZ...`)

### Step 2: Configure RugDetector

Create or update your `.env` file:

```bash
cd /home/hshadab/rugdetector
cp .env.example .env
nano .env  # or use your favorite editor
```

Update these lines:
```env
# Replace YOUR_ALCHEMY_API_KEY with your actual key
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_API_KEY
SOLANA_RPC_URL=https://solana-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_API_KEY
```

**Example** (with fake key):
```env
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/AbC123XyZ456def789GHI012jkl345M
SOLANA_RPC_URL=https://solana-mainnet.g.alchemy.com/v2/AbC123XyZ456def789GHI012jkl345M
```

### Step 3: Restart the Server

```bash
pkill -f "node.*server.js"
PORT=3000 node api/server.js
```

---

## Alchemy Free Tier Limits

**What you get for free**:
- ✅ **300 million compute units/month** (~300 req/sec sustained)
- ✅ **Unlimited requests** (within compute units)
- ✅ **Archive data access** (full blockchain history)
- ✅ **Enhanced APIs** (NFTs, Transfers, WebSockets)
- ✅ **99.9% uptime SLA**

**Enough for RugDetector?**
- **Feature extraction**: ~20 RPC calls per contract
- **Free tier**: 300M compute units/month
- **Capacity**: ~15 million contract analyses/month
- **Realistic**: 1,000-10,000 analyses/month = **plenty of headroom**

---

## Supported Networks

RugDetector supports only **Base** and **Solana** networks:

- ✅ **Base (Coinbase L2)**: `https://base-mainnet.g.alchemy.com/v2/YOUR_KEY`
- ✅ **Solana**: `https://solana-mainnet.g.alchemy.com/v2/YOUR_KEY`

---

## Advanced Configuration

### Multiple Apps for Better Organization

Create separate Alchemy apps for different chains:

```env
# Base app
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/BASE_KEY_HERE

# Solana app
SOLANA_RPC_URL=https://solana-mainnet.g.alchemy.com/v2/SOLANA_KEY_HERE
```

**Benefits**:
- Separate rate limits per chain
- Better monitoring in dashboard
- Easier to debug

### Fallback Configuration

For maximum reliability, configure fallback RPCs:

```env
# Primary: Alchemy
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_KEY

# Fallback: Public (add this to your code)
BASE_RPC_FALLBACK=https://mainnet.base.org
```

**Note**: Fallback logic is not yet implemented in the code but can be added.

---

## Testing Your Setup

### Test 1: Basic Connectivity

```bash
# Test Base endpoint
curl -X POST https://base-mainnet.g.alchemy.com/v2/YOUR_KEY \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Expected response:
# {"jsonrpc":"2.0","id":1,"result":"0x..."}  # Hex block number
```

### Test 2: RugDetector Integration

```bash
# Test contract analysis on Base (uses your Alchemy key automatically)
curl -X POST http://localhost:3000/check \
  -H "Content-Type: application/json" \
  -d '{
    "contract_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "blockchain": "base",
    "payment_id": "demo_alchemy_test"
  }'
```

Check the logs to see Alchemy being used:
```bash
tail -f /tmp/rugdetector.log | grep -i rpc
```

### Test 3: Feature Extraction

```bash
cd training
source ../venv/bin/activate
python3 -c "
import os
os.environ['BASE_RPC_URL'] = 'https://base-mainnet.g.alchemy.com/v2/YOUR_KEY'
from model.extract_features import extract_features
features = extract_features('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', 'base')
print(f'Extracted {len(features)} features')
"
```

---

## Monitoring Usage

### Alchemy Dashboard

1. Go to https://dashboard.alchemy.com/
2. Click your app
3. View metrics:
   - **Requests/day**
   - **Compute units used**
   - **Response times**
   - **Error rates**

### Check Rate Limit Usage

```bash
# Make request with verbose output
curl -v -X POST https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' 2>&1 | grep -i limit

# Look for headers like:
# x-alchemy-compute-units: 10
# x-ratelimit-limit: 300
# x-ratelimit-remaining: 299
```

---

## Cost Optimization Tips

### 1. Cache Responses
The RugDetector already caches features for 1 hour (configurable):
```env
CACHE_FEATURES=true
CACHE_TTL_SECONDS=3600  # 1 hour
```

### 2. Batch Requests
Instead of analyzing one contract at a time, batch multiple:
```bash
# Extract features for multiple contracts in one session
python3 training/extract_features_batch.py training/real_data/labeled_dataset.csv
```

### 3. Use Archive Data Wisely
Archive queries (historical data) cost more compute units. Only fetch what you need:
```env
MAX_HISTORICAL_DAYS=30  # Instead of 90
```

### 4. Monitor Your Usage
Set up alerts in Alchemy dashboard:
- Alert at 80% of monthly quota
- Alert at 95% of monthly quota

---

## Upgrading to Paid Plans

When you need more:

| Plan | Cost | Compute Units | Use Case |
|------|------|---------------|----------|
| **Free** | $0 | 300M/month | Development, MVP |
| **Growth** | $49/mo | 1B + $2 per 100M | Small production |
| **Scale** | Custom | Custom | Large production |

**When to upgrade**:
- Free tier: Up to ~10,000 analyses/month
- Growth: Up to ~50,000 analyses/month
- Scale: 100,000+ analyses/month

---

## Alternative Providers

If Alchemy doesn't work for you:

### QuickNode
- **Supports**: Ethereum, BSC, Polygon, Solana, +30 chains
- **Pricing**: $9/month starter (includes BSC!)
- **URL format**: `https://YOUR-ENDPOINT.quiknode.pro/YOUR-API-KEY/`
- **Setup**: https://www.quicknode.com/

### Infura
- **Supports**: Ethereum, Polygon, Arbitrum, Optimism
- **Pricing**: Free tier (100k requests/day)
- **URL format**: `https://mainnet.infura.io/v3/YOUR-PROJECT-ID`
- **Setup**: https://www.infura.io/

### Configuration Example (QuickNode for BSC):
```env
# Use Alchemy for Ethereum, Polygon, Base
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_KEY
POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_KEY

# Use QuickNode for BSC (Alchemy doesn't support it)
BSC_RPC_URL=https://YOUR-ENDPOINT.quiknode.pro/YOUR-QUICKNODE-KEY/
```

---

## Troubleshooting

### Error: "401 Unauthorized"
**Problem**: Invalid API key

**Solution**:
1. Check your .env file has the correct key
2. Verify the key in Alchemy dashboard
3. Make sure you copied the full key (no spaces)

### Error: "429 Too Many Requests"
**Problem**: Rate limit exceeded

**Solutions**:
1. Check usage in Alchemy dashboard
2. Upgrade to paid plan if needed
3. Reduce `FEATURE_EXTRACTION_MODE` calls
4. Enable caching: `CACHE_FEATURES=true`

### Error: "Network not supported"
**Problem**: Trying to use Alchemy for BSC

**Solution**:
BSC is not supported by Alchemy. Use:
```env
BSC_RPC_URL=https://bsc-dataseed.binance.org
```

### Slow Response Times
**Problem**: Network latency

**Solutions**:
1. Use Alchemy's closest region (auto-detected)
2. Check Alchemy status: https://status.alchemy.com/
3. Consider using Archive nodes: `https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY/archive`

---

## Best Practices

### 1. Keep API Keys Secret
```bash
# NEVER commit .env file
echo ".env" >> .gitignore

# Use environment variables in production
export ETHEREUM_RPC_URL="https://eth-mainnet.g.alchemy.com/v2/$ALCHEMY_KEY"
```

### 2. Use Separate Keys for Dev/Prod
```env
# Development
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/DEV_KEY

# Production
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/PROD_KEY
```

### 3. Monitor and Alert
- Set up Alchemy dashboard alerts
- Log RPC errors: `tail -f /tmp/rugdetector.log | grep RPC`
- Track response times

### 4. Implement Retries
For transient errors, retry with exponential backoff (add to your code):
```javascript
async function fetchWithRetry(url, options, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fetch(url, options);
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await sleep(1000 * Math.pow(2, i));  // 1s, 2s, 4s
    }
  }
}
```

---

## Summary

**Quick Setup**:
1. ✅ Get Alchemy API key (5 min)
2. ✅ Update `.env` file
3. ✅ Restart server
4. ✅ Test with contract analysis

**Benefits**:
- ✅ **300 req/sec** (vs 10 on public RPC)
- ✅ **No rate limiting** for normal use
- ✅ **99.9% uptime**
- ✅ **Free tier sufficient** for development

**Supported by RugDetector**:
- ✅ Base (Coinbase L2)
- ✅ Solana

**Next Steps**:
1. Set up your `.env` file with Alchemy keys
2. Test feature extraction
3. Monitor usage in Alchemy dashboard
4. Upgrade if needed

---

## Quick Reference

```bash
# Get API key
https://www.alchemy.com/ → Sign up → Create App → Copy Key

# Configure .env
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_KEY
SOLANA_RPC_URL=https://solana-mainnet.g.alchemy.com/v2/YOUR_KEY

# Test
curl -X POST http://localhost:3000/check \
  -H "Content-Type: application/json" \
  -d '{"contract_address":"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913","blockchain":"base","payment_id":"demo_test"}'

# Monitor
tail -f /tmp/rugdetector.log | grep -i rpc
```

**Happy analyzing! 🚀**
