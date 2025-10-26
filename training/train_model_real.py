#!/usr/bin/env python3
"""
RugDetector Model Training on Real Data
Trains a RandomForest classifier using real rug pull and legitimate token data
"""

import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, accuracy_score, precision_recall_fscore_support,
    confusion_matrix, roc_auc_score, roc_curve
)
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os
from pathlib import Path
from datetime import datetime

class RealDataModelTrainer:
    """Train RandomForest model on real rug pull data"""

    def __init__(self, features_csv: str):
        self.features_csv = Path(features_csv)
        self.model_dir = Path(__file__).parent.parent / "model"
        self.model_dir.mkdir(exist_ok=True)

        print("=" * 70)
        print("RugDetector Model Training on Real Data")
        print("=" * 70)
        print(f"Features CSV: {self.features_csv}")
        print(f"Model directory: {self.model_dir}")

    def load_and_prepare_data(self):
        """Load features CSV and prepare for training"""

        print("\n[1] Loading and preparing data...")

        # Load CSV
        df = pd.read_csv(self.features_csv)
        print(f"  ✓ Loaded {len(df)} contracts")

        # Define feature columns (60 features)
        feature_columns = [
            'hasOwnershipTransfer', 'hasRenounceOwnership', 'ownerBalance', 'ownerTransactionCount',
            'multipleOwners', 'ownershipChangedRecently', 'ownerContractAge', 'ownerIsContract',
            'ownerBlacklisted', 'ownerVerified',
            'hasLiquidityLock', 'liquidityPoolSize', 'liquidityRatio', 'hasUniswapV2',
            'hasPancakeSwap', 'liquidityLockedDays', 'liquidityProvidedByOwner', 'multiplePoolsExist',
            'poolCreatedRecently', 'lowLiquidityWarning', 'rugpullHistoryOnDEX', 'slippageTooHigh',
            'holderCount', 'holderConcentration', 'top10HoldersPercent', 'averageHoldingTime',
            'suspiciousHolderPatterns', 'whaleCount', 'holderGrowthRate', 'dormantHolders',
            'newHoldersSpiking', 'sellingPressure',
            'hasHiddenMint', 'hasPausableTransfers', 'hasBlacklist', 'hasWhitelist',
            'hasTimelocks', 'complexityScore', 'hasProxyPattern', 'isUpgradeable',
            'hasExternalCalls', 'hasSelfDestruct', 'hasDelegateCall', 'hasInlineAssembly',
            'verifiedContract', 'auditedByFirm', 'openSourceCode',
            'avgDailyTransactions', 'transactionVelocity', 'uniqueInteractors', 'suspiciousPatterns',
            'highFailureRate', 'gasOptimized', 'flashloanInteractions', 'frontRunningDetected',
            'contractAge', 'lastActivityDays', 'creationBlock', 'deployedDuringBullMarket',
            'launchFairness'
        ]

        # Extract features and labels
        X = df[feature_columns].values

        # Convert labels to numeric (low_risk=0, medium_risk=1, high_risk=2)
        label_mapping = {'low_risk': 0, 'medium_risk': 1, 'high_risk': 2}
        y = df['label'].map(label_mapping).values

        # Fill NaN values with 0
        X = np.nan_to_num(X, nan=0.0)

        print(f"  ✓ Feature matrix shape: {X.shape}")
        print(f"  ✓ Labels shape: {y.shape}")
        print(f"\n  Label distribution:")
        unique, counts = np.unique(y, return_counts=True)
        for label, count in zip(unique, counts):
            label_name = [k for k, v in label_mapping.items() if v == label][0]
            print(f"    {label_name}: {count} ({100 * count / len(y):.1f}%)")

        # Store metadata
        self.metadata = df[['address', 'blockchain', 'name', 'source']].copy()

        return X, y, feature_columns

    def train_and_evaluate(self, X, y, feature_columns):
        """Train model and perform comprehensive evaluation"""

        print("\n[2] Training and evaluating model...")

        # Split data: 70% train, 15% validation, 15% test
        X_train_val, X_test, y_train_val, y_test = train_test_split(
            X, y, test_size=0.15, random_state=42, stratify=y
        )
        X_train, X_val, y_train, y_val = train_test_split(
            X_train_val, y_train_val, test_size=0.176, random_state=42, stratify=y_train_val
        )  # 0.176 of 0.85 ≈ 0.15 of total

        print(f"\n  Dataset splits:")
        print(f"    Train: {len(X_train)} samples ({100 * len(X_train) / len(X):.1f}%)")
        print(f"    Validation: {len(X_val)} samples ({100 * len(X_val) / len(X):.1f}%)")
        print(f"    Test: {len(X_test)} samples ({100 * len(X_test) / len(X):.1f}%)")

        # Train model with hyperparameter tuning
        print("\n  Training RandomForest classifier...")
        model = RandomForestClassifier(
            n_estimators=200,  # Increased from 100
            max_depth=25,      # Increased from 20
            min_samples_split=5,
            min_samples_leaf=2,
            max_features='sqrt',  # Added for better generalization
            random_state=42,
            n_jobs=-1,
            class_weight='balanced'  # Handle class imbalance
        )
        model.fit(X_train, y_train)
        print("  ✓ Training complete")

        # Evaluate on validation set
        print("\n  Evaluating on validation set...")
        y_val_pred = model.predict(X_val)
        val_accuracy = accuracy_score(y_val, y_val_pred)
        print(f"  Validation Accuracy: {val_accuracy:.3f}")

        # Evaluate on test set
        print("\n[3] Final evaluation on test set...")
        y_test_pred = model.predict(X_test)
        y_test_proba = model.predict_proba(X_test)

        accuracy = accuracy_score(y_test, y_test_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, y_test_pred, average='weighted'
        )

        print(f"\n  Test Set Metrics:")
        print(f"    Accuracy: {accuracy:.3f}")
        print(f"    Precision: {precision:.3f}")
        print(f"    Recall: {recall:.3f}")
        print(f"    F1-Score: {f1:.3f}")

        print("\n  Classification Report:")
        print(classification_report(
            y_test, y_test_pred,
            target_names=['Low Risk', 'Medium Risk', 'High Risk'],
            digits=3
        ))

        # Confusion matrix
        cm = confusion_matrix(y_test, y_test_pred)
        print("\n  Confusion Matrix:")
        print("                Predicted")
        print("                Low    Med    High")
        print(f"  Actual Low    {cm[0][0]:4d}   {cm[0][1]:4d}   {cm[0][2]:4d}")
        if len(cm) > 1:
            print(f"         Med    {cm[1][0]:4d}   {cm[1][1]:4d}   {cm[1][2]:4d}")
        if len(cm) > 2:
            print(f"         High   {cm[2][0]:4d}   {cm[2][1]:4d}   {cm[2][2]:4d}")

        # Cross-validation
        print("\n[4] Performing 5-fold cross-validation...")
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy', n_jobs=-1)
        print(f"  CV Scores: {cv_scores}")
        print(f"  Mean CV Accuracy: {cv_scores.mean():.3f} (±{cv_scores.std() * 2:.3f})")

        # Feature importance
        print("\n[5] Analyzing feature importance...")
        importances = model.feature_importances_
        indices = np.argsort(importances)[::-1]

        print("\n  Top 15 most important features:")
        for i in range(min(15, len(indices))):
            idx = indices[i]
            print(f"    {i+1:2d}. {feature_columns[idx]:30s} {importances[idx]:.4f}")

        # Save feature importance
        feature_importance = pd.DataFrame({
            'feature': feature_columns,
            'importance': importances
        }).sort_values('importance', ascending=False)
        importance_file = self.model_dir / "feature_importance.csv"
        feature_importance.to_csv(importance_file, index=False)
        print(f"\n  ✓ Saved feature importance to {importance_file}")

        return model, {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'val_accuracy': val_accuracy,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'confusion_matrix': cm.tolist(),
            'feature_importance_top10': {
                feature_columns[idx]: float(importances[idx])
                for idx in indices[:10]
            }
        }

    def export_to_onnx(self, model, metrics):
        """Export trained model to ONNX format"""

        print("\n[6] Exporting model to ONNX...")

        initial_type = [('float_input', FloatTensorType([None, 60]))]

        # Disable ZipMap so probabilities are a tensor (compatible with onnxruntime-node)
        onnx_model = convert_sklearn(
            model,
            initial_types=initial_type,
            target_opset=15,
            options={id(model): {"zipmap": False}}
        )

        # Save ONNX model
        onnx_path = self.model_dir / 'rugdetector_v2_real.onnx'
        with open(onnx_path, 'wb') as f:
            f.write(onnx_model.SerializeToString())

        print(f"  ✓ ONNX model saved to: {onnx_path}")
        print(f"  ✓ Model size: {os.path.getsize(onnx_path) / 1024:.1f} KB")

        # Save metadata
        metadata = {
            "model_name": "rugdetector_v2_real",
            "version": "2.0.0",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model_type": "RandomForestClassifier",
            "training_data": "real_rugpull_dataset",
            "num_trees": 200,
            "max_depth": 25,
            "input_features": 60,
            "output_classes": 3,
            "classes": ["low_risk", "medium_risk", "high_risk"],
            "metrics": metrics,
            "note": "Trained on real rug pull and legitimate token data"
        }

        metadata_path = self.model_dir / 'rugdetector_v2_real_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"  ✓ Metadata saved to: {metadata_path}")

        return onnx_path, metadata_path

    def generate_report(self, metrics):
        """Generate comprehensive training report"""

        report_path = self.model_dir / "training_report_v2.txt"

        with open(report_path, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("RugDetector v2.0 Training Report (Real Data)\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")

            f.write("Model Configuration:\n")
            f.write("  - Algorithm: RandomForestClassifier\n")
            f.write("  - Number of trees: 200\n")
            f.write("  - Max depth: 25\n")
            f.write("  - Class weighting: balanced\n")
            f.write("  - Features: 60\n\n")

            f.write("Performance Metrics:\n")
            f.write(f"  - Test Accuracy: {metrics['accuracy']:.3f}\n")
            f.write(f"  - Precision: {metrics['precision']:.3f}\n")
            f.write(f"  - Recall: {metrics['recall']:.3f}\n")
            f.write(f"  - F1-Score: {metrics['f1_score']:.3f}\n")
            f.write(f"  - Validation Accuracy: {metrics['val_accuracy']:.3f}\n")
            f.write(f"  - CV Mean Accuracy: {metrics['cv_mean']:.3f} (±{metrics['cv_std'] * 2:.3f})\n\n")

            f.write("Top 10 Most Important Features:\n")
            for i, (feature, importance) in enumerate(metrics['feature_importance_top10'].items(), 1):
                f.write(f"  {i:2d}. {feature:30s} {importance:.4f}\n")

            f.write("\nComparison with v1.0 (Synthetic Data):\n")
            f.write("  v1.0 Accuracy: 0.940 (synthetic data)\n")
            f.write(f"  v2.0 Accuracy: {metrics['accuracy']:.3f} (real data)\n")
            f.write("\n  Note: v2.0 performance on real data is the true indicator of\n")
            f.write("  production performance. Synthetic data often overestimates accuracy.\n")

        print(f"\n  ✓ Training report saved to {report_path}")

    def run(self):
        """Execute the full training pipeline"""

        # Load data
        X, y, feature_columns = self.load_and_prepare_data()

        # Train and evaluate
        model, metrics = self.train_and_evaluate(X, y, feature_columns)

        # Export to ONNX
        onnx_path, metadata_path = self.export_to_onnx(model, metrics)

        # Generate report
        self.generate_report(metrics)

        print("\n" + "=" * 70)
        print("Training Complete!")
        print("=" * 70)
        print(f"\nModel files created:")
        print(f"  - {onnx_path}")
        print(f"  - {metadata_path}")
        print(f"  - {self.model_dir / 'feature_importance.csv'}")
        print(f"  - {self.model_dir / 'training_report_v2.txt'}")
        print(f"\nTest Accuracy: {metrics['accuracy']:.3f}")
        print(f"CV Accuracy: {metrics['cv_mean']:.3f} (±{metrics['cv_std'] * 2:.3f})")
        print("\nNext steps:")
        print("  1. Review training_report_v2.txt for detailed analysis")
        print("  2. Update api/services/rugDetector.js to use rugdetector_v2_real.onnx")
        print("  3. Test the model with real contracts")
        print("  4. Deploy to production")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train RugDetector model on real data")
    parser.add_argument("features_csv", help="CSV file with extracted features")

    args = parser.parse_args()

    trainer = RealDataModelTrainer(features_csv=args.features_csv)
    trainer.run()
