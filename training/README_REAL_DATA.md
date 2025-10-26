# Training RugDetector on Real Rug Pull Data

This guide explains how to train the RugDetector model on **real rug pull and legitimate token data** instead of synthetic data.

## Overview

The original model (`rugdetector_v1.onnx`) was trained on 5,000 synthetic samples. While it achieved 94% accuracy on synthetic test data, **real-world accuracy was unknown** because the model had never seen actual rug pull patterns.

The new pipeline (`v2.0`) trains on **real labeled data** from:
- Documented rug pull incidents (2021-2024)
- CRPWarner rug pull dataset
- Token Sniffer malicious token database
- Verified legitimate tokens (top DeFi protocols, CoinGecko top 100)

---

## Quick Start

### Prerequisites

```bash
# Python dependencies
pip install -r requirements.txt

# API keys (optional but recommended)
export TOKENSNIFFER_API_KEY="your_key_here"  # For Token Sniffer API
export ETHERSCAN_API_KEY="your_key_here"     # For feature extraction
export BSCSCAN_API_KEY="your_key_here"
export POLYGONSCAN_API_KEY="your_key_here"
export BASESCAN_API_KEY="your_key_here"
```

### Step 1: Collect Real Data

```bash
cd training
python collect_real_data.py
```

**What it does:**
- Collects 14+ known rug pull addresses from documented incidents
- Collects 50+ CRPWarner dataset addresses (if available)
- Fetches malicious tokens from Token Sniffer API (if key provided)
- Collects 30+ verified legitimate tokens (Uniswap, Aave, USDC, etc.)
- Fetches top 100 tokens from CoinGecko API

**Output:**
- `real_data/rugpull_addresses.csv` - Rug pull addresses
- `real_data/legitimate_addresses.csv` - Legitimate token addresses
- `real_data/labeled_dataset.csv` - Combined labeled dataset
- `real_data/data_collection_report.txt` - Summary report

### Step 2: Extract Features

```bash
python extract_features_batch.py real_data/labeled_dataset.csv --output real_data/features_extracted.csv
```

**What it does:**
- Runs `model/extract_features.py` on each contract address
- Extracts 60 blockchain features per contract
- Handles timeouts and errors gracefully
- Shows progress every 10 contracts

**Time estimate:** ~30 seconds per contract
- 50 contracts = ~25 minutes
- 100 contracts = ~50 minutes
- 200 contracts = ~100 minutes

**Output:**
- `real_data/features_extracted.csv` - All contracts with 60 features extracted

### Step 3: Train Model

```bash
python train_model_real.py real_data/features_extracted.csv
```

**What it does:**
- Loads extracted features
- Splits data: 70% train, 15% validation, 15% test
- Trains RandomForest (200 trees, max_depth=25, class_weight=balanced)
- Evaluates on validation and test sets
- Performs 5-fold cross-validation
- Analyzes feature importance
- Exports to ONNX format

**Output:**
- `model/rugdetector_v2_real.onnx` - Trained ONNX model
- `model/rugdetector_v2_real_metadata.json` - Model metadata with metrics
- `model/feature_importance.csv` - Feature importance rankings
- `model/training_report_v2.txt` - Comprehensive training report

---

## Data Sources

### Rug Pull Sources

| Source | Type | Count | Coverage |
|--------|------|-------|----------|
| Manual Curated | Documented incidents | 14+ | High-profile rug pulls (2021-2024) |
| CRPWarner Dataset | Academic research | 645 | Ethereum rug pulls (before May 2024) |
| Token Sniffer API | Real-time detection | Variable | Last 24 hours (Enterprise plan) |

**Notable rug pulls included:**
- Squid Game (SQUID) - $3.38M loss
- AnubisDAO - $60M loss
- StableMagnet - $22M loss
- Meerkat Finance - $31M loss

### Legitimate Token Sources

| Source | Type | Count | Coverage |
|--------|------|-------|----------|
| Manual Verified | Top DeFi protocols | 30+ | Uniswap, Aave, Chainlink, etc. |
| CoinGecko API | Market cap ranking | Variable | Top 100 tokens by market cap |

**Blockchains supported:**
- Ethereum
- Binance Smart Chain (BSC)
- Polygon
- Base

---

## Model Architecture

### RandomForest Configuration

```python
RandomForestClassifier(
    n_estimators=200,      # 200 decision trees (up from 100)
    max_depth=25,          # Max tree depth (up from 20)
    min_samples_split=5,
    min_samples_leaf=2,
    max_features='sqrt',   # Feature sampling for diversity
    class_weight='balanced', # Handle class imbalance
    random_state=42
)
```

### Training Pipeline

1. **Data Loading**
   - Load CSV with 60 features + metadata
   - Convert labels to numeric (low=0, medium=1, high=2)
   - Fill NaN values with 0

2. **Data Splitting**
   - 70% training (model fitting)
   - 15% validation (hyperparameter tuning)
   - 15% test (final evaluation)
   - Stratified split preserves class distribution

3. **Model Training**
   - Fit RandomForest on training set
   - Evaluate on validation set
   - Final evaluation on test set (never seen during training)

4. **Cross-Validation**
   - 5-fold stratified cross-validation
   - Reports mean accuracy ± 2 standard deviations

5. **Feature Importance**
   - Analyze which features matter most
   - Save rankings to CSV
   - Include top 10 in metadata

6. **ONNX Export**
   - Convert to ONNX format (onnxruntime-node compatible)
   - Strip ZipMap for tensor outputs
   - Save with metadata

---

## Expected Performance

### Realistic Expectations

| Metric | Synthetic (v1.0) | Real Data (v2.0) | Notes |
|--------|------------------|------------------|-------|
| Accuracy | 94% | **70-85%** | Real data is harder |
| Precision | 92% | **65-80%** | Fewer false positives expected |
| Recall | 91% | **70-85%** | Detect most rug pulls |
| F1-Score | 91.5% | **67-82%** | Balanced metric |

**Why lower performance is expected:**
- Real-world data is **noisy** (missing features, API failures)
- Rug pull patterns are **diverse** (not as clean as synthetic data)
- Class imbalance (more legitimate tokens than rug pulls)
- Feature extraction may fail for some contracts

**What matters:**
- **High recall for high-risk class** (catch most rug pulls, even with false positives)
- **High precision for low-risk class** (don't falsely flag legitimate tokens)
- **Consistent cross-validation scores** (model generalizes well)

---

## Feature Importance Analysis

After training, review `model/feature_importance.csv` to see which features contribute most to predictions.

**Expected top features:**
1. `ownerBalance` - High owner concentration is red flag
2. `holderConcentration` - Gini coefficient of holder distribution
3. `hasLiquidityLock` - Liquidity locking indicates legitimacy
4. `liquidityRatio` - Ratio of liquidity to total supply
5. `verifiedContract` - Source code verification
6. `contractAge` - Older contracts more trustworthy
7. `hasRenounceOwnership` - Renounced ownership reduces risk
8. `top10HoldersPercent` - Whale concentration
9. `hasHiddenMint` - Hidden minting function
10. `auditedByFirm` - Professional security audit

---

## Troubleshooting

### Issue: "Feature extraction failed for many contracts"

**Cause:** API rate limits, timeouts, or missing API keys

**Solution:**
- Add API keys to `.env` file
- Reduce batch size (process fewer contracts)
- Increase timeout in `extract_features_batch.py` (default: 60s)
- Use multiple RPC providers

### Issue: "Imbalanced class distribution"

**Cause:** Not enough rug pull data vs. legitimate tokens

**Solution:**
- Collect more rug pull addresses (CRPWarner dataset, Token Sniffer)
- Use `class_weight='balanced'` in RandomForest (already enabled)
- Apply SMOTE oversampling (advanced)

### Issue: "Model accuracy is low (<60%)"

**Cause:** Insufficient training data or poor feature quality

**Solution:**
- Collect more labeled data (target: 200+ contracts minimum)
- Verify feature extraction is working correctly
- Check for missing values in features
- Consider feature engineering (create new derived features)

### Issue: "CRPWarner dataset not found"

**Cause:** Dataset not cloned locally

**Solution:**
```bash
cd ~
git clone https://github.com/CRPWarner/RugPull CRPWarner_RugPull
```

The script will automatically find it at `~/CRPWarner_RugPull/dataset/groundtruth/`

---

## Advanced Usage

### Custom Dataset

If you have your own labeled dataset:

```python
# CSV format required:
# address,blockchain,label,name,source
# 0x1234...,ethereum,high_risk,MyRugPull,custom
# 0x5678...,bsc,low_risk,LegitToken,custom

python extract_features_batch.py my_custom_dataset.csv
python train_model_real.py real_data/features_extracted.csv
```

### Hyperparameter Tuning

Edit `train_model_real.py` to modify RandomForest parameters:

```python
model = RandomForestClassifier(
    n_estimators=300,      # More trees (slower but more accurate)
    max_depth=30,          # Deeper trees (risk overfitting)
    min_samples_split=10,  # More conservative splitting
    # ... other params
)
```

### Adding More Data Sources

Edit `collect_real_data.py` to add custom sources:

```python
# In collect_known_rugpulls() or collect_legitimate_tokens()
custom_rugpulls = [
    {"address": "0x...", "blockchain": "ethereum", "name": "MyRugPull", ...}
]
rugpulls.extend(custom_rugpulls)
```

---

## Deployment

### Update API to Use New Model

1. **Backup old model:**
   ```bash
   cp model/rugdetector_v1.onnx model/rugdetector_v1_backup.onnx
   ```

2. **Replace with new model:**
   ```bash
   cp model/rugdetector_v2_real.onnx model/rugdetector_v1.onnx
   cp model/rugdetector_v2_real_metadata.json model/rugdetector_v1_metadata.json
   ```

3. **Restart server:**
   ```bash
   npm restart
   ```

4. **Test with known contracts:**
   ```bash
   # Test with known rug pull
   curl -X POST http://localhost:3000/check \
     -H "Content-Type: application/json" \
     -d '{"contract_address": "0x5A3e6A77ba2f983eC0d371ea3B475F8Bc0811AD5", "blockchain": "ethereum", "payment_id": "demo_test"}'

   # Test with legitimate token (Uniswap)
   curl -X POST http://localhost:3000/check \
     -H "Content-Type: application/json" \
     -d '{"contract_address": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984", "blockchain": "ethereum", "payment_id": "demo_test"}'
   ```

### Gradual Rollout

For production, consider A/B testing:

1. Deploy v2.0 to staging environment
2. Run both models in parallel (v1.0 and v2.0)
3. Compare predictions on live traffic
4. Gradually shift traffic to v2.0
5. Monitor false positive/negative rates

---

## Continuous Improvement

### Retraining Schedule

Recommended: Retrain model **monthly** with new data

```bash
# 1. Collect new rug pulls from Token Sniffer
# 2. Add to labeled_dataset.csv
# 3. Re-extract features
# 4. Retrain model
# 5. Evaluate on holdout test set
# 6. Deploy if accuracy improves
```

### Feedback Loop

Track prediction outcomes:
- Log all predictions to database
- Monitor user reports (false positives/negatives)
- Periodically audit predictions
- Add misclassified contracts to training set
- Retrain with augmented data

---

## Files Created

```
training/
├── collect_real_data.py          # Data collection script
├── extract_features_batch.py     # Batch feature extraction
├── train_model_real.py           # Model training on real data
├── README_REAL_DATA.md           # This file
└── real_data/                    # Generated data directory
    ├── rugpull_addresses.csv
    ├── legitimate_addresses.csv
    ├── labeled_dataset.csv
    ├── features_extracted.csv
    └── data_collection_report.txt

model/
├── rugdetector_v2_real.onnx      # New trained model
├── rugdetector_v2_real_metadata.json
├── feature_importance.csv
└── training_report_v2.txt
```

---

## References

### Academic Research

1. **RPHunter** - "Unveiling Rug Pull Schemes in Crypto Token via Code-and-Transaction Fusion Analysis" (2024)
   - Dataset: 645 rug pulls, 1,675 benign tokens
   - Accuracy: 91%

2. **TokenScout** - "Early Detection of Ethereum Scam Tokens via Temporal Graph Learning" (CCS 2024)
   - Dataset: 214,084 tokens (2015-2023)
   - Detected: 706 rugpulls, 174 honeypots, 90 Ponzi schemes

3. **CRPWarner** - Static bytecode analysis for rug pull detection
   - GitHub: https://github.com/CRPWarner/RugPull

### Tools & APIs

- **Token Sniffer**: https://tokensniffer.com/
- **GoPlus Security**: https://gopluslabs.io/
- **CoinGecko API**: https://www.coingecko.com/en/api

---

## License

MIT License (same as parent project)

## Support

For issues or questions:
- GitHub Issues: https://github.com/hshadab/rugdetector/issues
- Email: (your email here)
