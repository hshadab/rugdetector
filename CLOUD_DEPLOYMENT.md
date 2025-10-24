# RugDetector Cloud Deployment Guide

This guide covers deploying RugDetector to production cloud hosting services.

## 🎯 Recommended Hosting Service

### **Railway.app** (Recommended)

**Why Railway?**
- ✅ Easiest deployment for Node.js + Python hybrid apps
- ✅ No cold starts (always-on instances)
- ✅ Better value for ML workloads (~$5-10/month)
- ✅ Automatic HTTPS and environment variable management
- ✅ Simple scaling

**Alternative**: Render.com (if you prefer YAML configuration)

---

## 🚀 Deploy to Railway.app

### Prerequisites
- GitHub repository with your code
- Railway.app account (free to start)

### Step 1: Connect Repository

1. Go to [railway.app](https://railway.app)
2. Click **"Start a New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your `rugdetector` repository

### Step 2: Configure Environment Variables

In the Railway dashboard, add these environment variables:

```bash
# Node.js
NODE_ENV=production
PORT=3000

# Blockchain RPC Nodes (Required)
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
BSC_RPC_URL=https://bsc-dataseed.binance.org
POLYGON_RPC_URL=https://polygon-rpc.com
ARBITRUM_RPC_URL=https://arb1.arbitrum.io/rpc

# API Keys (Required for full functionality)
THE_GRAPH_API_KEY=your_graph_api_key
MORALIS_API_KEY=your_moralis_api_key
ETHERSCAN_API_KEY=your_etherscan_api_key
BSCSCAN_API_KEY=your_bscscan_api_key
POLYGONSCAN_API_KEY=your_polygonscan_api_key
ARBISCAN_API_KEY=your_arbiscan_api_key
```

### Step 3: Deploy

Railway will automatically:
1. Detect the Dockerfile
2. Build the container
3. Deploy to production
4. Assign a public URL (e.g., `rugdetector-production.up.railway.app`)

### Step 4: Verify Deployment

Visit your Railway URL:
- Health check: `https://your-app.railway.app/health`
- UI: `https://your-app.railway.app`
- API: `POST https://your-app.railway.app/check`

---

## 🔧 Deploy to Render.com

### Prerequisites
- GitHub repository with your code
- Render.com account (free tier available)

### Step 1: Create Blueprint

1. Go to [render.com](https://render.com)
2. Click **"New"** → **"Blueprint"**
3. Connect your GitHub repository
4. Render will detect `render.yaml` automatically

### Step 2: Configure Environment Variables

In the Render dashboard, set these variables:

```bash
NODE_ENV=production
PORT=3000
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
BSC_RPC_URL=https://bsc-dataseed.binance.org
POLYGON_RPC_URL=https://polygon-rpc.com
ARBITRUM_RPC_URL=https://arb1.arbitrum.io/rpc
THE_GRAPH_API_KEY=your_graph_api_key
MORALIS_API_KEY=your_moralis_api_key
ETHERSCAN_API_KEY=your_etherscan_api_key
BSCSCAN_API_KEY=your_bscscan_api_key
POLYGONSCAN_API_KEY=your_polygonscan_api_key
ARBISCAN_API_KEY=your_arbiscan_api_key
```

### Step 3: Deploy

Click **"Apply"** and Render will:
1. Build the Docker image
2. Deploy to their infrastructure
3. Assign a public URL (you can then add your custom domain like `rugdetector.ai`)

### Step 4: Upgrade to Paid Plan (Recommended)

⚠️ **Important**: Render's free tier spins down after 15 minutes of inactivity, causing slow cold starts (30-60 seconds). For production use, upgrade to the **Starter plan ($7/month)** for always-on instances.

---

## 🐳 Deploy with Docker (Self-Hosted)

If you want to self-host on your own server:

### Build the Image

```bash
docker build -t rugdetector:latest .
```

### Run the Container

```bash
docker run -d \
  --name rugdetector \
  -p 3000:3000 \
  -e NODE_ENV=production \
  -e ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY \
  -e THE_GRAPH_API_KEY=your_key \
  -e MORALIS_API_KEY=your_key \
  rugdetector:latest
```

### Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  rugdetector:
    build: .
    ports:
      - "3000:3000"
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

Then run:

```bash
docker-compose up -d
```

---

## 📊 Hosting Service Comparison

| Feature | Railway | Render | Fly.io | Vercel |
|---------|---------|--------|--------|--------|
| **Node.js + Python** | ✅ Native | ✅ Docker | ✅ Docker | ❌ Serverless only |
| **Free Tier** | 500 hrs + $5 credit | Limited hours | 3 VMs + 160GB | ❌ Not suitable |
| **Cold Starts** | ❌ No | ⚠️ Yes (free tier) | ⚠️ Possible | ⚠️ Yes |
| **Pricing** | ~$5-10/mo | ~$7-15/mo | ~$3-8/mo | N/A |
| **Ease of Use** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **ML Workloads** | ✅ Excellent | ✅ Good | ✅ Excellent | ❌ Not suitable |
| **Auto HTTPS** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Scaling** | ✅ Automatic | ✅ Manual | ✅ Automatic | ✅ Automatic |

### Recommendation:
- **Best Overall**: Railway.app (easiest + best value)
- **Best Performance**: Fly.io (global edge network)
- **Best for IaC**: Render.com (YAML config)

---

## 🔑 Required API Keys

### Free API Keys

1. **Alchemy** (Ethereum RPC)
   - Sign up: https://alchemy.com
   - Free tier: 300M compute units/month

2. **The Graph** (DEX liquidity data)
   - Sign up: https://thegraph.com/studio
   - Free tier: 100k queries/month

3. **Moralis** (Holder analytics)
   - Sign up: https://moralis.io
   - Free tier: 40k requests/month

4. **Etherscan** (Contract verification)
   - Sign up: https://etherscan.io/apis
   - Free tier: 5 calls/second

### Optional (Improve Coverage)

- **BSCScan API**: https://bscscan.com/apis
- **PolygonScan API**: https://polygonscan.com/apis
- **Arbiscan API**: https://arbiscan.io/apis

---

## 🛠️ Configuration Files

### Files Created for Deployment

```
rugdetector/
├── Dockerfile              # Docker image definition
├── .dockerignore          # Files to exclude from Docker build
├── render.yaml            # Render.com blueprint
├── railway.toml           # Railway.app config (TOML format)
├── railway.json           # Railway.app config (JSON format)
└── CLOUD_DEPLOYMENT.md    # This file
```

### Environment Variables Template

Create `.env.production`:

```bash
# Copy this to your hosting service's environment variables

NODE_ENV=production
PORT=3000

# Blockchain RPC Nodes
ETHEREUM_RPC_URL=
BSC_RPC_URL=
POLYGON_RPC_URL=
ARBITRUM_RPC_URL=

# API Keys
THE_GRAPH_API_KEY=
MORALIS_API_KEY=
ETHERSCAN_API_KEY=
BSCSCAN_API_KEY=
POLYGONSCAN_API_KEY=
ARBISCAN_API_KEY=
```

---

## 🚨 Troubleshooting

### Build Failures

**Issue**: Docker build fails on `zkml-jolt-core` binary

**Solution**: The binary is large (144MB). Ensure your hosting service supports larger builds:
- Railway: ✅ No issues
- Render: ✅ Works (may take longer)
- Fly.io: ✅ Works

### Memory Issues

**Issue**: Server crashes with OOM (Out of Memory)

**Solution**: Upgrade to a plan with more memory:
- Railway: Upgrade to Pro ($5/mo for 512MB → $10/mo for 1GB)
- Render: Starter plan includes 512MB (should be sufficient)

### Cold Starts

**Issue**: First request after inactivity is slow (30-60s)

**Solution**:
- **Railway**: No cold starts (always-on)
- **Render**: Upgrade to paid plan ($7/mo)
- **Fly.io**: Keep instance running with `keep_alive` cron job

### API Rate Limits

**Issue**: External API calls fail with 429 errors

**Solution**:
1. Check your API key quotas
2. Implement caching for blockchain data
3. Upgrade API tiers if needed

---

## 📈 Post-Deployment

### 1. Custom Domain

**Railway**:
```bash
Settings → Domains → Add Custom Domain
```

**Render**:
```bash
Settings → Custom Domain → Add
```

### 2. Monitoring

Set up health checks:
- Railway: Built-in (no config needed)
- Render: Uses `/health` endpoint automatically

### 3. Scaling

**Railway**: Automatic vertical scaling
**Render**: Manual horizontal scaling (requires Pro plan)

### 4. Logs

Access logs:
- Railway: Dashboard → Deployments → View Logs
- Render: Dashboard → Logs tab

---

## 🎉 Success Checklist

After deployment, verify:

- [ ] Health endpoint returns 200: `GET /health`
- [ ] UI loads correctly: `GET /`
- [ ] API accepts requests: `POST /check`
- [ ] zkML proofs are generated correctly
- [ ] Real blockchain data is being fetched
- [ ] Environment variables are set
- [ ] HTTPS is working
- [ ] Custom domain configured (optional)

---

## 📞 Support

- Railway: https://railway.app/help
- Render: https://render.com/docs
- GitHub Issues: https://github.com/hshadab/rugdetector/issues

---

**Built with ❤️ for the Web3 ecosystem**
