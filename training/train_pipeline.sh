#!/bin/bash
#
# Complete Training Pipeline for RugDetector v2.0
# Automates data collection, feature extraction, and model training
#

set -e  # Exit on error

echo "========================================================================"
echo "RugDetector v2.0 Training Pipeline"
echo "Training on Real Rug Pull Data"
echo "========================================================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found"
    exit 1
fi

echo "✓ Python: $(python3 --version)"
echo ""

# Step 1: Collect real data
echo "========================================================================"
echo "Step 1/3: Collecting Real Rug Pull and Legitimate Token Data"
echo "========================================================================"
echo ""

if [ -f "real_data/labeled_dataset.csv" ]; then
    read -p "⚠ labeled_dataset.csv already exists. Re-collect data? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 collect_real_data.py
    else
        echo "Skipping data collection (using existing data)"
    fi
else
    python3 collect_real_data.py
fi

echo ""
echo "✓ Data collection complete"
echo ""

# Check if data was collected
if [ ! -f "real_data/labeled_dataset.csv" ]; then
    echo "❌ Error: labeled_dataset.csv not found after collection"
    exit 1
fi

# Count contracts
CONTRACT_COUNT=$(tail -n +2 real_data/labeled_dataset.csv | wc -l)
echo "📊 Collected $CONTRACT_COUNT contracts"
echo ""

# Step 2: Extract features
echo "========================================================================"
echo "Step 2/3: Extracting Features from Contracts"
echo "========================================================================"
echo ""
echo "This will take approximately $(( CONTRACT_COUNT * 30 / 60 )) minutes"
echo "Feature extraction: ~30 seconds per contract"
echo ""

if [ -f "real_data/features_extracted.csv" ]; then
    read -p "⚠ features_extracted.csv already exists. Re-extract features? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 extract_features_batch.py real_data/labeled_dataset.csv --output real_data/features_extracted.csv
    else
        echo "Skipping feature extraction (using existing data)"
    fi
else
    python3 extract_features_batch.py real_data/labeled_dataset.csv --output real_data/features_extracted.csv
fi

echo ""
echo "✓ Feature extraction complete"
echo ""

# Check if features were extracted
if [ ! -f "real_data/features_extracted.csv" ]; then
    echo "❌ Error: features_extracted.csv not found after extraction"
    exit 1
fi

# Count successful extractions
FEATURE_COUNT=$(tail -n +2 real_data/features_extracted.csv | wc -l)
SUCCESS_RATE=$(( FEATURE_COUNT * 100 / CONTRACT_COUNT ))
echo "📊 Successfully extracted features from $FEATURE_COUNT/$CONTRACT_COUNT contracts ($SUCCESS_RATE%)"
echo ""

if [ "$FEATURE_COUNT" -lt 20 ]; then
    echo "⚠ Warning: Less than 20 contracts with features extracted"
    echo "   Model training may not be reliable with this little data"
    read -p "   Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Training cancelled"
        exit 1
    fi
fi

# Step 3: Train model
echo "========================================================================"
echo "Step 3/3: Training RandomForest Model on Real Data"
echo "========================================================================"
echo ""

python3 train_model_real.py real_data/features_extracted.csv

echo ""
echo "========================================================================"
echo "Pipeline Complete! 🎉"
echo "========================================================================"
echo ""
echo "📁 Files created:"
echo "   - model/rugdetector_v2_real.onnx"
echo "   - model/rugdetector_v2_real_metadata.json"
echo "   - model/feature_importance.csv"
echo "   - model/training_report_v2.txt"
echo ""
echo "📊 Next steps:"
echo "   1. Review training_report_v2.txt for model performance"
echo "   2. Check feature_importance.csv to see which features matter most"
echo "   3. Test the model with known contracts"
echo "   4. Deploy to production:"
echo "      cp model/rugdetector_v2_real.onnx model/rugdetector_v1.onnx"
echo "      npm restart"
echo ""
echo "🔬 To test the new model:"
echo "   # Backup old model"
echo "   cp ../model/rugdetector_v1.onnx ../model/rugdetector_v1_backup.onnx"
echo ""
echo "   # Use new model"
echo "   cp ../model/rugdetector_v2_real.onnx ../model/rugdetector_v1.onnx"
echo ""
echo "   # Restart server and test"
echo "   cd .. && npm restart"
echo ""
