# Quick Start: Train on Real Data

## One Command

```bash
cd training
./train_pipeline.sh
```

## Manual (3 Steps)

```bash
cd training

# Step 1: Collect data (~1 minute)
python3 collect_real_data.py

# Step 2: Extract features (~30 seconds per contract)
python3 extract_features_batch.py real_data/labeled_dataset.csv

# Step 3: Train model (~2-5 minutes)
python3 train_model_real.py real_data/features_extracted.csv
```

## Deploy to Production

```bash
# Backup old model
cp model/rugdetector_v1.onnx model/rugdetector_v1_backup.onnx

# Use new model
cp model/rugdetector_v2_real.onnx model/rugdetector_v1.onnx

# Restart
npm restart
```

## Test

```bash
# Test rug pull (expect HIGH risk)
curl -X POST http://localhost:3000/check \
  -H "Content-Type: application/json" \
  -d '{"contract_address":"0x5A3e6A77ba2f983eC0d371ea3B475F8Bc0811AD5","blockchain":"ethereum","payment_id":"demo_test"}'

# Test legitimate (expect LOW risk)
curl -X POST http://localhost:3000/check \
  -H "Content-Type: application/json" \
  -d '{"contract_address":"0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984","blockchain":"ethereum","payment_id":"demo_test"}'
```

## Get More Data

```bash
# CRPWarner dataset (645 rug pulls)
cd ~
git clone https://github.com/CRPWarner/RugPull CRPWarner_RugPull
cd -
python3 collect_real_data.py  # Will auto-detect

# Token Sniffer API (requires Enterprise key)
export TOKENSNIFFER_API_KEY="your_key"
python3 collect_real_data.py
```

## Files Created

```
training/real_data/
  ├── labeled_dataset.csv          # All addresses with labels
  ├── features_extracted.csv       # All features (60 per contract)
  └── data_collection_report.txt   # Summary

model/
  ├── rugdetector_v2_real.onnx     # Trained model
  ├── rugdetector_v2_real_metadata.json
  ├── feature_importance.csv       # Which features matter
  └── training_report_v2.txt       # Full metrics
```

## Expected Time

| Step | Time | Depends On |
|------|------|------------|
| Data collection | 1-2 min | API rate limits |
| Feature extraction | 30s × N contracts | Contract count |
| Model training | 2-5 min | Dataset size |

**Example:** 100 contracts = ~52 minutes total

## Troubleshooting

**"Feature extraction failed"**
→ Add API keys to `.env` (ETHERSCAN_API_KEY, etc.)

**"Not enough data"**
→ Clone CRPWarner dataset (645 more rug pulls)

**"Low accuracy"**
→ Collect more data (target: 200+ contracts)

**Full docs:** `README_REAL_DATA.md`
