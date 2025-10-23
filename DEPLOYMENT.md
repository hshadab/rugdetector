# RugDetector Deployment Guide

Complete guide for deploying RugDetector with Jolt Atlas zkML in production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Building Jolt Atlas zkML](#building-jolt-atlas-zkml)
4. [Configuration](#configuration)
5. [Deployment Options](#deployment-options)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Security Considerations](#security-considerations)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 20 GB
- OS: Ubuntu 20.04+ or similar Linux distribution

**Recommended (for zkML):**
- CPU: 8+ cores
- RAM: 16 GB
- Storage: 50 GB SSD
- OS: Ubuntu 22.04 LTS

### Software Dependencies

```bash
# Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Python 3.8+
sudo apt-get install -y python3 python3-pip

# Rust 1.88+ (for zkML)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup default 1.88
rustup target add riscv32im-unknown-none-elf

# Git
sudo apt-get install -y git

# Build tools
sudo apt-get install -y build-essential pkg-config libssl-dev
```

### Network Requirements

**Required Access:**
- `github.com` - For cloning repositories
- `crates.io` - For Rust dependencies
- `npmjs.com` - For Node.js packages
- `pypi.org` - For Python packages

**Blockchain RPC:**
- Ethereum mainnet RPC endpoint
- Base network RPC endpoint (for X402 payments)
- BSC, Polygon RPC endpoints (optional, for multi-chain)

**Recommended:**
- Use paid RPC providers (Alchemy, Infura, QuickNode) for production
- Set up rate limiting
- Configure fallback endpoints

---

## Environment Setup

### 1. Clone Repository

```bash
# Clone the repository
git clone https://github.com/hshadab/rugdetector.git
cd rugdetector

# Checkout specific version (production)
git checkout main  # or specific tag/release
```

### 2. Install Dependencies

```bash
# Node.js dependencies
npm install

# Python dependencies
pip3 install -r requirements.txt

# Or use virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
nano .env
```

**Required Variables:**

```bash
# Server Configuration
PORT=3000
NODE_ENV=production
SERVICE_NAME=RugDetector
SERVICE_VERSION=1.0.0

# Blockchain RPC Endpoints
BASE_RPC_URL=https://mainnet.base.org
ETHEREUM_RPC_URL=https://eth-mainnet.alchemyapi.io/v2/YOUR_KEY
BSC_RPC_URL=https://bsc-dataseed.binance.org/
POLYGON_RPC_URL=https://polygon-rpc.com/

# X402 Payment Configuration
USDC_CONTRACT_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
PAYMENT_AMOUNT=100000  # 0.1 USDC (6 decimals)
SERVICE_WALLET_ADDRESS=0xYOUR_SERVICE_WALLET_ADDRESS

# Python Path
PYTHON_PATH=python3  # Or /path/to/venv/bin/python3

# Security
API_RATE_LIMIT=100  # Requests per minute
ENABLE_CORS=true
ALLOWED_ORIGINS=*  # Restrict in production!
```

---

## Building Jolt Atlas zkML

### Step 1: Uncomment Dependencies

Edit `jolt_zkml/Cargo.toml`:

```toml
[dependencies]
# Uncomment these lines:
zkml-jolt-core = { git = "https://github.com/ICME-Lab/jolt-atlas", branch = "main" }
onnx-tracer = { git = "https://github.com/ICME-Lab/jolt-atlas", branch = "main" }
jolt-core = { git = "https://github.com/ICME-Lab/zkml-jolt", branch = "zkml-jolt" }

# Keep existing:
ark-bn254 = "0.5.0"
ark-serialize = { version = "0.5.0", features = ["derive"] }
clap = { version = "4.3", features = ["derive"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
hex = "0.4"
sha3 = "0.10"
```

### Step 2: Uncomment Code

Edit `jolt_zkml/src/lib.rs` - uncomment all the import statements and zkML implementation code (see `JOLT_ATLAS_INTEGRATION.md` for details).

Edit `jolt_zkml/src/main.rs` - uncomment the proof generation and verification logic.

### Step 3: Build

```bash
cd jolt_zkml

# Build in release mode (optimized)
cargo build --release

# This takes 5-10 minutes first time
# Output: target/release/jolt_zkml_cli
```

### Step 4: Verify Build

```bash
# Test binary
./target/release/jolt_zkml_cli version

# Expected output:
# {
#   "name": "jolt_zkml_cli",
#   "version": "0.1.0",
#   "status": "ready"
# }

# Test preprocessing
./target/release/jolt_zkml_cli preprocess --model ../model/rugdetector_v1.onnx

# Test proof generation
echo '{"features": [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59]}' | \
  ./target/release/jolt_zkml_cli prove --model ../model/rugdetector_v1.onnx
```

---

## Configuration

### ML Model Setup

```bash
# Train model (if not using pre-trained)
python3 training/train_model.py

# Verify model exists
ls -lh model/rugdetector_v1.onnx

# Should be ~26 KB
```

### Server Selection

Choose your deployment mode:

#### Option A: zkML Server (Recommended)

Uses real Jolt Atlas zkSNARKs (requires built binary):

```bash
python3 zkml_server.py
```

**Features:**
- ✅ Real zkSNARK proofs
- ✅ Cryptographically verifiable
- ✅ Zero-knowledge guarantees
- ⚠️ Slightly higher latency (~1.2s)

#### Option B: Node.js Server (Fallback)

Uses ONNX inference without zkML:

```bash
npm start
```

**Features:**
- ✅ Lower latency (~600ms)
- ✅ Easier deployment
- ❌ No zkSNARK proofs
- ❌ Trust-based verification

### Load Balancing

For production, use multiple instances:

```bash
# Using PM2 (recommended)
npm install -g pm2

# Start multiple zkML server instances
pm2 start zkml_server.py --name rugdetector-1 --interpreter python3
pm2 start zkml_server.py --name rugdetector-2 --interpreter python3 -- --port 3001
pm2 start zkml_server.py --name rugdetector-3 --interpreter python3 -- --port 3002

# Configure nginx as load balancer
# See nginx configuration below
```

---

## Deployment Options

### Option 1: Systemd Service (Recommended)

Create `/etc/systemd/system/rugdetector.service`:

```ini
[Unit]
Description=RugDetector zkML Service
After=network.target

[Service]
Type=simple
User=rugdetector
WorkingDirectory=/opt/rugdetector
Environment="NODE_ENV=production"
ExecStart=/usr/bin/python3 /opt/rugdetector/zkml_server.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/rugdetector/output.log
StandardError=append:/var/log/rugdetector/error.log

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/rugdetector/logs

[Install]
WantedBy=multi-user.target
```

**Setup:**

```bash
# Create user
sudo useradd -r -s /bin/false rugdetector

# Create directories
sudo mkdir -p /opt/rugdetector /var/log/rugdetector
sudo chown rugdetector:rugdetector /opt/rugdetector /var/log/rugdetector

# Copy files
sudo cp -r . /opt/rugdetector/
sudo chown -R rugdetector:rugdetector /opt/rugdetector

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable rugdetector
sudo systemctl start rugdetector

# Check status
sudo systemctl status rugdetector
```

### Option 2: Docker Container

Create `Dockerfile`:

```dockerfile
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    nodejs npm \
    curl git build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN rustup target add riscv32im-unknown-none-elf

# Create app directory
WORKDIR /app

# Copy dependency files
COPY package*.json requirements.txt ./
RUN npm install && pip3 install -r requirements.txt

# Copy application
COPY . .

# Build Jolt Atlas zkML
WORKDIR /app/jolt_zkml
RUN cargo build --release

WORKDIR /app

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

# Run server
CMD ["python3", "zkml_server.py"]
```

**Build and run:**

```bash
# Build image
docker build -t rugdetector:latest .

# Run container
docker run -d \
  --name rugdetector \
  -p 3000:3000 \
  -e BASE_RPC_URL=$BASE_RPC_URL \
  -e ETHEREUM_RPC_URL=$ETHEREUM_RPC_URL \
  --restart unless-stopped \
  rugdetector:latest

# Check logs
docker logs -f rugdetector
```

### Option 3: Kubernetes Deployment

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rugdetector
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rugdetector
  template:
    metadata:
      labels:
        app: rugdetector
    spec:
      containers:
      - name: rugdetector
        image: your-registry/rugdetector:latest
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: "production"
        - name: BASE_RPC_URL
          valueFrom:
            secretKeyRef:
              name: rugdetector-secrets
              key: base-rpc-url
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: rugdetector-service
spec:
  selector:
    app: rugdetector
  ports:
  - port: 80
    targetPort: 3000
  type: LoadBalancer
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# Server health
curl http://localhost:3000/health

# Service discovery
curl http://localhost:3000/.well-known/ai-service.json

# Test analysis (with mock payment)
curl -X POST http://localhost:3000/check \
  -H "Content-Type: application/json" \
  -d '{
    "contract_address": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
    "blockchain": "ethereum",
    "payment_id": "tx_0xtest"
  }'
```

### Logging

Configure structured logging:

```python
# Add to zkml_server.py
import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/var/log/rugdetector/app.log'),
        logging.StreamHandler()
    ]
)

# Log analysis requests
logging.info(json.dumps({
    'event': 'analysis_request',
    'contract': contract_address,
    'blockchain': blockchain,
    'timestamp': datetime.utcnow().isoformat()
}))
```

### Metrics

Monitor key metrics:

- **Request Rate**: Requests per minute
- **Latency**: Average response time
- **Success Rate**: % of successful analyses
- **Proof Generation**: zkSNARK proof time
- **Error Rate**: Failed requests

### Alerts

Set up alerts for:

- Server downtime
- High error rate (>5%)
- High latency (>5s)
- RPC failures
- Memory/CPU usage (>80%)

---

## Security Considerations

### API Security

1. **Rate Limiting**

```nginx
# nginx configuration
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

server {
    location /check {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://localhost:3000;
    }
}
```

2. **CORS Configuration**

```python
# Restrict origins in production
ALLOWED_ORIGINS = [
    'https://yourdomain.com',
    'https://app.yourdomain.com'
]
```

3. **Input Validation**

Already implemented:
- Contract address format validation
- Blockchain name whitelist
- Payment ID verification

### Network Security

```bash
# Firewall rules
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw enable

# Only allow localhost for application port
# Use nginx as reverse proxy
```

### Secrets Management

```bash
# Use environment variables
# Never commit .env to git

# For production, use:
# - AWS Secrets Manager
# - HashiCorp Vault
# - Kubernetes Secrets
```

---

## Troubleshooting

### Issue: Binary not found

**Error:** `Rust binary not found: jolt_zkml/target/release/jolt_zkml_cli`

**Solution:**
```bash
cd jolt_zkml
cargo build --release
```

### Issue: Network errors during build

**Error:** `failed to get successful HTTP response from https://index.crates.io/config.json`

**Solution:**
- Check internet connection
- Verify firewall allows crates.io
- Try again (temporary network issue)

### Issue: High memory usage

**Observation:** Server using >8GB RAM

**Solution:**
```bash
# Limit process memory
ulimit -v 8388608  # 8GB in KB

# Or use cgroups
systemctl set-property rugdetector.service MemoryMax=8G
```

### Issue: Proof generation timeout

**Error:** `Proof generation timed out (>5s)`

**Solution:**
- Check CPU usage
- Ensure release build (not debug)
- Increase timeout in bindings.py
- Add preprocessing cache

### Issue: RPC rate limiting

**Error:** `429 Too Many Requests`

**Solution:**
- Use paid RPC provider
- Implement request caching
- Add retry logic with backoff
- Use multiple RPC endpoints

---

## Performance Tuning

### CPU Optimization

```bash
# Use all CPU cores for zkML
export RAYON_NUM_THREADS=8  # Or your core count
```

### Caching

Implement Redis caching for:
- Feature extraction results (1 hour TTL)
- Proof verification (24 hour TTL)
- RPC responses (5 minute TTL)

### Connection Pooling

```python
# Use connection pooling for RPC
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20
)
session.mount('http://', adapter)
session.mount('https://', adapter)
```

---

## Backup & Recovery

### Data to Backup

- Configuration files (.env)
- ML model (model/rugdetector_v1.onnx)
- Logs (for analytics)
- Preprocessing cache (if implemented)

### Backup Script

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/rugdetector_$DATE"

mkdir -p $BACKUP_DIR
cp .env $BACKUP_DIR/
cp model/rugdetector_v1.onnx $BACKUP_DIR/
cp -r logs/ $BACKUP_DIR/ 2>/dev/null || true

tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

echo "Backup created: $BACKUP_DIR.tar.gz"
```

---

## Checklist

**Pre-Deployment:**
- [ ] Build Jolt Atlas zkML binary
- [ ] Configure environment variables
- [ ] Set up RPC endpoints
- [ ] Test zkSNARK proof generation
- [ ] Configure payment verification
- [ ] Set up monitoring
- [ ] Configure logging
- [ ] Implement rate limiting

**Deployment:**
- [ ] Deploy application
- [ ] Configure reverse proxy (nginx)
- [ ] Set up SSL/TLS certificates
- [ ] Configure firewall
- [ ] Set up health checks
- [ ] Test end-to-end flow
- [ ] Enable monitoring alerts

**Post-Deployment:**
- [ ] Monitor logs for errors
- [ ] Check performance metrics
- [ ] Verify proof generation
- [ ] Test payment flow
- [ ] Document any issues
- [ ] Set up automated backups

---

## Support

For issues or questions:
- See [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) for build help
- See [JOLT_ATLAS_INTEGRATION.md](JOLT_ATLAS_INTEGRATION.md) for zkML details
- Check logs: `tail -f /var/log/rugdetector/error.log`
- GitHub Issues: https://github.com/hshadab/rugdetector/issues
