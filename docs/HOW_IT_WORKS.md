# How RugDetector Works: Complete Plain English Guide

## What Is RugDetector?

RugDetector is a smart contract analyzer that uses artificial intelligence to detect "rug pulls" - scams where cryptocurrency project creators abandon a project and steal investors' money. Think of it as a security scanner for crypto tokens, like antivirus software for your computer.

**Key Features:**
- Analyzes smart contracts to predict if they're scams
- Uses zero-knowledge machine learning (zkML) for verifiable AI
- Works with AI agents through the x402 payment protocol
- Provides cryptographic proofs that the AI analysis was done correctly

---

## The Complete System: How Everything Works Together

### 1. **The User Journey**

#### Step 1: Discovery
An AI agent (like Claude or ChatGPT) or human user discovers RugDetector through:
- The service discovery endpoint: `/.well-known/ai-service.json`
- Direct API documentation
- The web UI at https://rugdetector.onrender.com

#### Step 2: Payment (x402 Protocol)
To use the service, you need to pay:
- **Amount**: 0.1 USDC
- **Network**: Base (Layer 2 blockchain)
- **How**: Send USDC to the service wallet address
- **Get**: A transaction hash (proof of payment)

**Demo Mode Alternative:**
- For testing, use a payment ID starting with `demo_` (e.g., `demo_test_123`)
- No actual payment required
- Same analysis quality

#### Step 3: Request Analysis
Send a POST request to `/check` with:
```json
{
  "payment_id": "tx_0xYOUR_TRANSACTION_HASH",
  "contract_address": "0x1234...",
  "blockchain": "base"
}
```

#### Step 4: Behind the Scenes Processing
The server does 6 major steps:
1. **Payment Verification**: Checks your transaction is real and hasn't been used before
2. **Feature Extraction**: Analyzes 18 characteristics of the contract
3. **AI Inference**: Runs the contract through the ML model
4. **Risk Calculation**: Determines if it's high/medium/low risk
5. **Proof Generation**: Creates a cryptographic proof (~700ms)
6. **Proof Verification**: Verifies the proof is valid before sending response

#### Step 5: Receive Results
You get back:
- Risk score (0-1, where 1 is extremely risky)
- Risk category (low/medium/high)
- Confidence level
- 18 extracted features
- Recommendation (what to do)
- **zkML proof** with verification status

---

## 2. **The Machine Learning Model**

### What Kind of AI Is It?

**Model Type**: Logistic Regression
- Simple but effective mathematical model
- Takes 18 numbers as input, outputs a risk probability
- Like a weighted formula: `risk = (feature1 × weight1) + (feature2 × weight2) + ...`

**Training Data**: 18,296 Real Contracts
- Source: Uniswap V2 exchange
- Rug pulls: 16,462 contracts (90%)
- Safe tokens: 1,834 contracts (10%)
- Time period: Historical data from 2020-2023

**Accuracy**: 98.20%
- Tested on separate validation set (20% of data)
- Means: Out of 100 contracts, it correctly identifies 98

### The 18 Features

The model looks at these characteristics from real Uniswap V2 data:

**Liquidity Metrics** (Features 1-3):
1. `mint_count_per_week` - How often new liquidity is added
2. `burn_count_per_week` - How often liquidity is removed
3. `mint_ratio` - Ratio of adding vs removing liquidity

**Trading Patterns** (Features 4-6):
4. `burn_ratio` - Percentage of liquidity burns
5. `transfer_ratio` - Transfer frequency
6. `unique_mints` - Number of unique addresses adding liquidity

**Holder Distribution** (Features 7-12):
7. `unique_burns` - Number of unique addresses removing liquidity
8. `unique_transfers` - Number of active trading addresses
9. `avg_mint_per_week` - Average liquidity additions
10. `avg_burn_per_week` - Average liquidity removals
11. `avg_transfers_per_week` - Average trading volume
12. `total_supply` - Total number of tokens

**Price & Volume** (Features 13-15):
13. `circulating_supply` - Tokens in circulation
14. `holder_concentration` - How concentrated ownership is
15. `top_10_holder_balance` - Percentage held by top 10 wallets

**Time Factors** (Features 16-18):
16. `ownership_change_count` - How often ownership changed
17. `liquidity_lock_duration` - How long liquidity is locked
18. `days_since_creation` - Age of the contract

### How The Model Works

```
Input Features → Multiply by Weights → Add Together → Sigmoid → Probability
[18 numbers]      [18 weights]         [sum]          [0-1]     [risk score]
```

**Example:**
```
Features: [100, 50, 0.5, 0.3, ...]
Weights:  [0.2, -0.1, 0.3, 0.4, ...]

Calculation:
(100 × 0.2) + (50 × -0.1) + (0.5 × 0.3) + ... = LogitScore
Sigmoid(LogitScore) = 0.78 = 78% chance of rug pull
```

---

## 3. **Zero-Knowledge Machine Learning (zkML)**

### What Is zkML? (Simple Explanation)

Imagine you ask a friend to do a math problem, and they tell you the answer. You might not trust them. zkML is like them showing you:
- The problem
- Their work (step by step)
- A cryptographic seal that proves they did it correctly

**Without zkML:**
- You send contract → AI says "high risk" → You trust it?
- Problem: No way to verify the AI actually ran correctly
- Could be compromised, biased, or broken

**With zkML:**
- You send contract → AI says "high risk" + provides proof
- Proof = cryptographic evidence that the AI ran correctly
- Anyone can verify the proof independently
- Trustless: Don't need to trust the server

### How Jolt-Atlas Works (Not SNARKs!)

**Traditional zkML (SNARKs):**
- Use complex elliptic curve cryptography
- Slow (~5-10 seconds for simple operations)
- Requires "trusted setup" ceremony

**Jolt-Atlas (Our Approach):**
- Uses **lookup tables** (pre-computed operation results)
- Fast (~700ms total time)
- No trusted setup needed
- More transparent and auditable

**The Four Operations:**

1. **Mul** (Multiply): Multiply features by weights
   ```
   [100, 50, 0.5] × [0.2, -0.1, 0.3] = [20, -5, 0.15]
   ```

2. **ReduceSum** (Add): Sum all the results
   ```
   20 + (-5) + 0.15 = 15.15
   ```

3. **Add** (Bias): Add the model's bias term
   ```
   15.15 + 2.5 = 17.65
   ```

4. **Sigmoid** (Probability): Convert to 0-1 probability
   ```
   Sigmoid(17.65) = 0.999... ≈ 1.0 (very high risk!)
   ```

### Proof Generation Process

```
1. Preprocessing (100ms)
   ├─ Load model weights
   ├─ Scale input features
   └─ Prepare computation circuit

2. Prove (500ms)
   ├─ Execute Mul operations with lookup tables
   ├─ Execute ReduceSum with accumulator
   ├─ Execute Add for bias
   ├─ Execute Sigmoid approximation
   └─ Generate Lasso commitment proof

3. Verify (100ms)
   ├─ Check proof structure
   ├─ Verify Lasso commitments
   ├─ Validate computation correctness
   └─ Return verified=true/false

Total: ~700ms
```

### Proof Structure

The proof contains:
- **Proof ID**: Unique identifier (e.g., `a1b2c3d4e5f67890`)
- **Protocol**: `jolt-atlas-v1`
- **Commitments**: Cryptographic hashes of intermediate computations
- **Witness Data**: Values at each computation step
- **Verification Keys**: Public keys for verification

---

## 4. **The API Server Architecture**

### Express.js Server Components

```
┌─────────────────────────────────────────────────────┐
│              Express.js API Server                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │         Rate Limiting Middleware             │  │
│  │  • Global: 60 req/min per IP                │  │
│  │  • Payment: 30 verifications/min per IP     │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │         Payment Verification Service         │  │
│  │  1. Check payment replay cache              │  │
│  │  2. Fetch transaction from Base network     │  │
│  │  3. Verify USDC contract interaction        │  │
│  │  4. Confirm amount ≥ 0.1 USDC              │  │
│  │  5. Mark payment as used (1hr TTL)          │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │      Feature Extraction Service              │  │
│  │  • Extracts 18 features from contract       │  │
│  │  • Normalizes using StandardScaler          │  │
│  │  • Returns feature array                    │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │         ONNX Inference Service               │  │
│  │  • Loads zkml_rugdetector.onnx              │  │
│  │  • Runs inference on scaled features        │  │
│  │  • Returns risk probability (0-1)           │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │         zkML Prover Service                  │  │
│  │  • Calls Rust prover binary                 │  │
│  │  • Generates Jolt-Atlas proof               │  │
│  │  • ~700ms proof generation                  │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │         zkML Verifier Service                │  │
│  │  • Calls Rust verifier binary               │  │
│  │  • Validates proof correctness              │  │
│  │  • Returns verified=true/false              │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Request Flow

```
User Request → Rate Limiter → Payment Check → Feature Extraction
                                    ↓
                              Replay Protection
                                    ↓
                            Base Network RPC
                                    ↓
                         USDC Transaction Check
                                    ↓
                              ONNX Inference
                                    ↓
                           zkML Proof Generation
                                    ↓
                           zkML Proof Verification
                                    ↓
                           JSON Response → User
```

---

## 5. **Security Features**

### Payment Replay Prevention

**Problem**: Someone could reuse a payment transaction hash multiple times

**Solution**: Payment Tracker
```javascript
// In-memory cache with TTL
{
  "tx_0x123abc": {
    used_at: "2025-10-26T12:00:00Z",
    contract: "0x456def",
    expires_at: "2025-10-26T13:00:00Z"  // 1 hour TTL
  }
}
```

**How It Works:**
1. Check if payment ID exists in cache
2. If exists → reject with 402 Payment Required
3. If new → verify payment → mark as used
4. Auto-expire after 1 hour

### Rate Limiting

**Global Rate Limit:**
- 60 requests per minute per IP address
- Protects against DoS attacks
- Uses express-rate-limit middleware

**Payment Verification Rate Limit:**
- 30 payment verifications per minute per IP
- Prevents payment verification spam
- Separate counter from global limit

**Health Check Exemption:**
- `/health` endpoint not rate limited
- Allows monitoring without consuming quota

### Input Validation

**Contract Address:**
- EVM: Must match `^0x[a-fA-F0-9]{40}$`
- Solana: Must match `^[1-9A-HJ-NP-Za-km-z]{32,44}$`

**Payment ID:**
- Format: `tx_0x[hash]` or `demo_[anything]`
- Demo mode: Bypasses payment verification
- Real mode: Must be valid transaction hash

**Blockchain Parameter:**
- Must be one of: `base`, `solana`
- Case-insensitive
- Defaults to `base` if not provided

---

## 6. **The x402 Protocol**

### What Is x402?

x402 is a protocol for payment-gated HTTP APIs. Think of it like:
- HTTP 200 = Success
- HTTP 404 = Not Found
- **HTTP 402 = Payment Required**

### How It Works

**1. Service Discovery**
```
GET /.well-known/ai-service.json

Response:
{
  "name": "RugDetector",
  "description": "AI rug pull detector",
  "pricing": {
    "currency": "USDC",
    "amount": "0.1",
    "network": "base"
  },
  "endpoints": ["/check"]
}
```

**2. Payment Request (402 Response)**
```
POST /check
{
  "contract_address": "0x123..."
}

Response: HTTP 402 Payment Required
X-PAYMENT-RESPONSE: eyJzY2hlbWVzIjpb...

Body:
{
  "error": "Payment required",
  "payment_details": {
    "amount": "0.1",
    "currency": "USDC",
    "network": "base",
    "recipient": "0xSERVICE_WALLET"
  }
}
```

**3. Make Payment**
- User sends 0.1 USDC to service wallet on Base
- Gets transaction hash: `0xabc123...`

**4. Retry with Payment**
```
POST /check
X-PAYMENT: eyJ0eEhhc2giOiIweGFiYzEyMyJ9  (base64 encoded)

OR in JSON body:
{
  "payment_id": "tx_0xabc123...",
  "contract_address": "0x123..."
}

Response: HTTP 200 OK
{
  "success": true,
  "data": { ... analysis results ... }
}
```

---

## 7. **The Web UI**

### What Users See

**Home Page (index.html):**
1. **Hero Section**
   - Title: "zkML-Verified Rug Pull Detection"
   - Stats: 98.2% accuracy, 18 features, ~700ms proofs
   - Feature badges

2. **Analyzer Form**
   - Contract address input
   - Blockchain selector (Base/Solana)
   - Payment ID input (with demo mode hint)
   - "Analyze Contract" button

3. **Loading Animation**
   - Progress steps:
     - Verifying payment...
     - Extracting 18 features...
     - Running zkML model...
     - Generating Jolt-Atlas proof...
     - Finalizing results...

4. **Results Display**
   - **Risk Score Card**: Circular progress with color coding
     - Green: Low risk (0-0.3)
     - Yellow: Medium risk (0.3-0.7)
     - Red: High risk (0.7-1.0)

   - **zkML Proof Card**: NEW!
     - Status badge: ✅ Verified / ⚠️ Failed / ❌ Not Verified
     - Proof ID, protocol, timestamp
     - Proof size in KB
     - "View Raw Proof" button
     - Expandable JSON viewer

   - **Features Breakdown**: 18 features with values

   - **Contract Details**: Address, blockchain, timestamp

### JavaScript Functionality

**Main Functions:**

1. `analyzeContract()` - Form submission handler
   ```javascript
   - Validate inputs
   - Show loading animation
   - Call API
   - Handle response
   - Display results
   ```

2. `displayResults(data)` - Populate results UI
   ```javascript
   - Update risk score
   - Update risk category
   - Display features
   - Show contract details
   - Display zkML proof
   ```

3. `displayZkmlProof(zkml)` - NEW! Show proof details
   ```javascript
   - Set verification status icon
   - Populate proof fields
   - Store proof for raw viewer
   - Show/hide view button
   ```

---

## 8. **Deployment**

### Render.com Hosting

**Build Process:**
```bash
1. Install Node.js dependencies (npm install)
2. Install Python dependencies (pip install)
3. Build ONNX model (npm run train)
4. Strip ZipMap from model (python script)
5. Start server (npm start)
```

**Environment Variables:**
```
PORT=3000
NODE_ENV=production
PAYMENT_ADDRESS=0x...
BASE_RPC_URL=https://...
RATE_LIMIT_MAX_REQUESTS=60
PAYMENT_RATE_LIMIT_MAX=30
PAYMENT_CACHE_TTL_SECONDS=3600
```

**Automatic Deployment:**
- Push to GitHub `main` branch
- Render auto-detects changes
- Rebuilds and redeploys (~5 minutes)
- Zero downtime deployment

---

## 9. **Common Questions**

### Q: Do I need to trust the RugDetector service?

**A:** No! That's the point of zkML. The cryptographic proof guarantees that:
1. The AI model ran correctly on your input
2. The risk score is mathematically correct
3. No one tampered with the results

You can verify the proof independently using the Jolt-Atlas verifier.

### Q: What if the proof verification fails?

**A:** If `verified: false`, it means:
- The proof generation failed, OR
- The proof verification detected an error

In this case, don't trust the risk score. The response will include a `verification_warning` explaining why.

### Q: Can I use this without paying?

**A:** Yes! Use demo mode:
- Set `payment_id` to anything starting with `demo_` (e.g., `demo_test_123`)
- Free unlimited testing
- Same analysis quality
- Same zkML proofs

### Q: How long does analysis take?

**A:** Typical timing:
- Payment verification: 1-2 seconds
- Feature extraction: 0.5 seconds
- ML inference: 0.1 seconds
- zkML proof generation: 0.7 seconds
- zkML proof verification: 0.1 seconds
- **Total**: ~2.5 seconds

### Q: What blockchains are supported?

**A:** Currently:
- **Base** (Ethereum Layer 2) - Primary
- **Solana** - Supported for contract addresses

Model was trained on Ethereum/Base data (Uniswap V2).

### Q: Is my payment transaction private?

**A:** Payment transactions are on-chain (Base network), so they're public. However:
- Only transaction hash is stored temporarily (1 hour)
- No personal information collected
- Payment tracker expires after 1 hour
- No persistent user database

---

## 10. **For Developers**

### Running Locally

```bash
# 1. Clone repository
git clone https://github.com/hshadab/rugdetector
cd rugdetector

# 2. Install dependencies
npm install
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Edit .env with your configuration

# 4. Train model (if needed)
npm run train

# 5. Start server
npm start
```

Server runs on http://localhost:3000

### API Integration Example

```javascript
// Make API request
const response = await fetch('http://localhost:3000/check', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    payment_id: 'demo_test_123',  // Use demo mode
    contract_address: '0x1234567890abcdef1234567890abcdef12345678',
    blockchain: 'base'
  })
});

const result = await response.json();

// Check if analysis succeeded
if (result.success) {
  console.log('Risk Score:', result.data.riskScore);
  console.log('Risk Category:', result.data.riskCategory);
  console.log('Confidence:', result.data.confidence);

  // Check zkML proof
  if (result.data.zkml.verified) {
    console.log('✅ Proof verified!');
    console.log('Proof ID:', result.data.zkml.proof_id);
  } else {
    console.log('⚠️ Proof verification failed');
  }
}
```

### File Structure

```
rugdetector/
├── api/
│   ├── server.js              # Express server entry point
│   ├── routes/
│   │   ├── check.js           # Main analysis endpoint
│   │   └── zkmlVerify.js      # Proof verification endpoint
│   └── services/
│       ├── payment.js         # Payment verification
│       ├── paymentTracker.js  # Replay prevention
│       ├── rugDetector.js     # ML inference
│       ├── zkmlProver.js      # Proof generation/verification
│       └── x402.js            # x402 protocol helpers
├── model/
│   ├── zkml_rugdetector.onnx  # ML model (432 bytes!)
│   ├── zkml_rugdetector_scaler.pkl  # Feature scaler
│   └── train_zkml_model.py    # Training script
├── ui/
│   ├── index.html             # Web UI
│   └── assets/
│       ├── js/app.js          # UI JavaScript
│       └── css/styles.css     # UI styles
├── public/
│   └── .well-known/
│       └── ai-service.json    # X402 service discovery
├── zkml-jolt-atlas/           # Jolt-Atlas prover (Rust)
├── HOW_IT_WORKS.md            # This file!
└── README.md                  # Quick start guide
```

---

## Summary

RugDetector is a complete end-to-end system that:

1. **Accepts payments** via x402 protocol (or demo mode)
2. **Extracts 18 features** from smart contracts
3. **Runs AI analysis** using a logistic regression model
4. **Generates zkML proofs** using Jolt-Atlas (~700ms)
5. **Verifies proofs** before returning results
6. **Provides trustless AI** - users don't need to trust the service

The system combines traditional web technologies (Node.js, Express) with cutting-edge cryptography (zero-knowledge proofs) to provide verifiable, trustless AI analysis of smart contracts.

**Key Innovation**: Every analysis includes a cryptographic proof that the AI ran correctly, making it possible to have trustless AI services on the internet.
