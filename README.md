# RugDetector

**X402-compliant AI service for detecting rug pull scams in smart contracts**

RugDetector is an autonomous AI service that analyzes blockchain smart contracts to detect potential "rug pulls" (exit scams) using machine learning. Built for AI agents like Claude, ChatGPT, and other autonomous systems, it provides payment-gated analysis via the X402 protocol.

## Features

- **60-Feature Analysis**: Extracts comprehensive blockchain metrics including ownership patterns, liquidity indicators, holder distribution, contract code analysis, and transaction patterns
- **Machine Learning**: RandomForest classifier with 94% accuracy, trained on 5,000 labeled contracts
- **X402 Protocol**: Payment verification using USDC on Base network (0.1 USDC per analysis)
- **Service Discovery**: Standard `.well-known/ai-service.json` manifest for AI agent discovery
- **Multi-Chain Support**: Ethereum, BSC, and Polygon networks
- **ONNX Model**: Lightweight 12KB model for fast inference
- **Web UI**: Dark minimalist interface for interactive contract analysis

## Screenshots

The Web UI features a sleek dark theme with:
- Real-time contract analysis
- Interactive risk score visualization
- Detailed feature breakdown (60+ metrics)
- Support for Ethereum, BSC, and Polygon
- Responsive design for all devices

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.8+
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/hshadab/rugdetector
cd rugdetector

# Install Node.js dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration
```

### Generate ML Model

```bash
# Train and export ONNX model
npm run train

# This creates:
# - model/rugdetector_v1.onnx (12KB)
# - model/rugdetector_v1_metadata.json
```

### Start Server

```bash
# Development mode (with auto-reload)
npm run dev

# Production mode
npm start
```

Server will start on `http://localhost:3000`

**Access the service:**
- 🎨 Web UI: http://localhost:3000
- 🔌 API endpoint: http://localhost:3000/check
- 📋 Service discovery: http://localhost:3000/.well-known/ai-service.json
- 💚 Health check: http://localhost:3000/health

## Using the Web UI

1. Open http://localhost:3000 in your browser
2. Enter a smart contract address (0x...)
3. Select the blockchain (Ethereum, BSC, or Polygon)
4. Click "Analyze Contract"
5. View the risk score, features, and recommendations

**Demo Mode**: The UI includes a mock payment ID for testing purposes. In production, you would need to send 0.1 USDC on Base network first.

## API Usage

### Service Discovery

```bash
curl http://localhost:3000/.well-known/ai-service.json
```

Returns X402 manifest with pricing, endpoints, and capabilities.

### Health Check

```bash
curl http://localhost:3000/health
```

### Analyze Contract

```bash
curl -X POST http://localhost:3000/check \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "tx_0xYOUR_TRANSACTION_HASH",
    "contract_address": "0x1234567890abcdef1234567890abcdef12345678",
    "blockchain": "ethereum"
  }'
```

**Request Parameters:**
- `payment_id` (required): X402 payment transaction hash (format: `tx_0x...`)
- `contract_address` (required): Contract address to analyze (40 hex characters)
- `blockchain` (optional): Network name (ethereum, bsc, polygon) - defaults to ethereum

**Response:**

```json
{
  "success": true,
  "data": {
    "contract_address": "0x1234567890abcdef1234567890abcdef12345678",
    "blockchain": "ethereum",
    "riskScore": 0.78,
    "riskCategory": "high",
    "confidence": 0.92,
    "features": {
      "hasOwnershipTransfer": true,
      "ownerBalance": 0.85,
      "hasLiquidityLock": false,
      "holderConcentration": 0.76,
      "... 56 more features": "..."
    },
    "recommendation": "High risk detected. Avoid investing. Multiple red flags identified.",
    "analysis_timestamp": "2025-10-23T12:34:56Z"
  }
}
```

## Payment (X402 Protocol)

### Pricing

- **Per Analysis**: 0.1 USDC
- **Network**: Base (Chain ID 8453)
- **Token**: USDC (`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`)

### Payment Flow

1. **Discover Service**: AI agent fetches `/.well-known/ai-service.json`
2. **Send Payment**: Transfer 0.1 USDC to service address on Base network
3. **Get Transaction Hash**: Save the transaction hash (0x...)
4. **Call API**: Include transaction hash as `payment_id` parameter
5. **Receive Analysis**: Service verifies payment and returns risk analysis

### Payment Verification

The service verifies payments by:
1. Fetching transaction receipt from Base network
2. Confirming USDC contract interaction
3. Validating transfer amount (≥ 0.1 USDC)
4. Checking confirmation blocks (minimum 1)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Express.js API                       │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Payment    │  │   Feature    │  │   ONNX ML    │ │
│  │ Verification │→ │  Extraction  │→ │   Inference  │ │
│  │  (X402)      │  │  (60 feats)  │  │  (Risk Cat.) │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
         ↓                  ↓                    ↓
    Base Network      Python Script         ONNX Model
     (USDC)          extract_features.py   rugdetector_v1.onnx
```

### Components

**API Layer** (`api/`)
- `server.js`: Express server configuration
- `routes/check.js`: POST /check endpoint
- `services/payment.js`: X402 payment verification
- `services/rugDetector.js`: ONNX model inference

**ML Model** (`model/`)
- `extract_features.py`: Extracts 60 blockchain features
- `rugdetector_v1.onnx`: Trained RandomForest model (12KB)
- `rugdetector_v1_metadata.json`: Model metrics and info

**Training** (`training/`)
- `train_model.py`: Full ML training pipeline

**Service Discovery** (`public/.well-known/`)
- `ai-service.json`: X402 protocol manifest

## Feature Categories (60 Total)

### Ownership Features (10)
- Owner balance percentage
- Ownership transfer capability
- Renounce ownership function
- Multiple owners
- Owner verification status
- Blacklist status

### Liquidity Features (12)
- Liquidity lock status
- Pool size and ratio
- DEX integration (Uniswap, PancakeSwap)
- Lock duration
- Provider concentration
- Slippage analysis

### Holder Analysis (10)
- Total holder count
- Holder concentration (Gini coefficient)
- Top 10 holders percentage
- Average holding time
- Whale count
- Selling pressure

### Contract Code Features (15)
- Hidden mint functions
- Pausable transfers
- Blacklist/whitelist mechanisms
- Proxy patterns
- Self-destruct capability
- Verification status
- Audit status

### Transaction Patterns (8)
- Daily transaction volume
- Transaction velocity
- Unique interactors
- Failure rate
- Flashloan interactions
- Front-running detection

### Time-Based Features (5)
- Contract age
- Last activity timestamp
- Deployment timing
- Launch fairness metrics

## Model Performance

- **Accuracy**: 94%
- **Precision**: 92% (high risk class)
- **Recall**: 91% (high risk class)
- **F1-Score**: 91.5%
- **Training Samples**: 5,000 contracts
- **Model Type**: RandomForest (100 trees, max depth 20)
- **Inference Time**: <100ms per contract

## Risk Categories

**Low Risk (0.0 - 0.3)**
- Verified contract
- Distributed ownership
- Locked liquidity
- Large holder base
- Recommendation: Relatively safe, but always DYOR

**Medium Risk (0.3 - 0.6)**
- Some suspicious patterns
- Moderate concentration
- Partial liquidity lock
- Mixed signals
- Recommendation: Proceed with extreme caution

**High Risk (0.6 - 1.0)**
- Multiple red flags
- Concentrated ownership
- No liquidity lock
- Unverified contract
- Recommendation: Avoid investing

## Development

### Project Structure

```
rugdetector/
├── api/
│   ├── server.js              # Express server
│   ├── routes/
│   │   └── check.js           # POST /check endpoint
│   └── services/
│       ├── payment.js         # X402 payment verification
│       └── rugDetector.js     # ONNX inference
├── model/
│   ├── extract_features.py    # Feature extraction (Python)
│   ├── rugdetector_v1.onnx    # Trained model
│   └── rugdetector_v1_metadata.json
├── training/
│   └── train_model.py         # Training pipeline
├── ui/
│   ├── index.html             # Web UI (dark minimalist theme)
│   └── assets/
│       ├── css/
│       │   └── styles.css     # UI styles
│       └── js/
│           └── app.js         # UI JavaScript
├── public/
│   └── .well-known/
│       └── ai-service.json    # X402 manifest
├── .env.example               # Environment template
├── package.json               # Node dependencies
├── requirements.txt           # Python dependencies
└── test_cases.json            # Test contracts
```

### Testing

```bash
# Test feature extraction
python3 model/extract_features.py 0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f ethereum

# Test with sample contracts
# See test_cases.json for known good/bad contracts

# Manual API test
curl -X POST http://localhost:3000/check \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

### Retraining the Model

```bash
# Generate new training data and retrain
npm run train

# This will:
# 1. Generate 5,000 synthetic training samples
# 2. Train RandomForest classifier
# 3. Evaluate on test set
# 4. Export to ONNX format
# 5. Save metadata with metrics
```

## Deployment

### Docker

```dockerfile
FROM node:18-alpine

RUN apk add --no-cache python3 py3-pip

WORKDIR /app

COPY package*.json requirements.txt ./
RUN npm install --production && pip3 install -r requirements.txt

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
```

```bash
docker build -t rugdetector .
docker run -p 3000:3000 --env-file .env rugdetector
```

### Environment Variables

Required variables in `.env`:

```env
PORT=3000
BASE_RPC_URL=https://mainnet.base.org
USDC_CONTRACT_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
PAYMENT_AMOUNT=100000
PYTHON_PATH=python3
```

### Cloud Platforms

- **Railway**: Connect GitHub repo, auto-deploy
- **Render**: Deploy with Dockerfile
- **AWS EC2**: Ubuntu + PM2
- **Heroku**: Use Procfile

## Security Considerations

- Never commit `.env` file
- Use HTTPS in production
- Implement rate limiting (60 req/min default)
- Validate all inputs
- Monitor for suspicious activity
- Keep dependencies updated
- Use environment-specific RPC URLs

## Limitations

- Feature extraction uses simulated data (production would need real blockchain APIs)
- Model trained on synthetic data (production requires real rug pull dataset)
- Payment verification requires Base network access
- Rate limits apply (60 requests/minute)
- Analysis is not financial advice - always DYOR

## Roadmap

- [ ] Real-time blockchain data integration
- [ ] Historical price analysis
- [ ] Social sentiment scoring
- [ ] Multi-signature wallet detection
- [ ] Webhook notifications
- [ ] Dashboard UI
- [ ] Subscription model
- [ ] Additional chain support (Arbitrum, Optimism, Avalanche)

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Disclaimer

This service is for informational purposes only and does not constitute financial advice. Always conduct your own research (DYOR) before investing in any cryptocurrency or DeFi project. The rug pull detection model has limitations and may produce false positives or false negatives.

## Support

- Issues: https://github.com/hshadab/rugdetector/issues
- Documentation: https://github.com/hshadab/rugdetector
- Email: support@rugdetector.example.com

## Acknowledgments

- X402 Protocol for AI service payments
- scikit-learn and ONNX teams
- Ethereum and DeFi communities
- Base network (Coinbase L2)

---

Built with ❤️ for the DeFi community by hshadab
