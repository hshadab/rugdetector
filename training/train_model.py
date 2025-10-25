#!/usr/bin/env python3
"""
RugDetector Model Training Pipeline
Trains a RandomForest classifier to detect rug pulls from smart contract features
"""

import json
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score, precision_recall_fscore_support
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
import sys
import os

def generate_synthetic_training_data(n_samples=5000):
    """
    Generate synthetic training data for demonstration
    In production, this would load real labeled data from a database

    Returns:
        X: Feature matrix (n_samples, 60)
        y: Labels (n_samples,) - 0=low_risk, 1=medium_risk, 2=high_risk
    """
    print(f"Generating {n_samples} synthetic training samples...")

    np.random.seed(42)

    # Distribution: 30% low risk, 30% medium risk, 40% high risk
    n_low = int(n_samples * 0.3)
    n_medium = int(n_samples * 0.3)
    n_high = n_samples - n_low - n_medium

    X = []
    y = []

    # Generate LOW RISK samples (legitimate projects)
    for _ in range(n_low):
        features = {
            # Ownership features - good patterns
            'ownerBalance': np.random.uniform(0.0, 0.2),
            'hasRenounceOwnership': np.random.choice([0, 1], p=[0.3, 0.7]),
            'ownerBlacklisted': 0,
            'ownerVerified': np.random.choice([0, 1], p=[0.2, 0.8]),

            # Liquidity features - strong liquidity
            'hasLiquidityLock': np.random.choice([0, 1], p=[0.1, 0.9]),
            'liquidityRatio': np.random.uniform(0.5, 0.9),
            'liquidityLockedDays': np.random.uniform(180, 730),
            'lowLiquidityWarning': 0,

            # Holder features - distributed ownership
            'holderConcentration': np.random.uniform(0.1, 0.3),
            'top10HoldersPercent': np.random.uniform(0.15, 0.4),
            'holderCount': np.random.uniform(1000, 10000),

            # Code features - verified and safe
            'hasHiddenMint': 0,
            'verifiedContract': np.random.choice([0, 1], p=[0.1, 0.9]),
            'auditedByFirm': np.random.choice([0, 1], p=[0.4, 0.6]),
            'hasSelfDestruct': 0,

            # Time features - mature project
            'contractAge': np.random.uniform(90, 730),
        }
        X.append(generate_full_feature_vector(features, risk_level='low'))
        y.append(0)  # Low risk

    # Generate MEDIUM RISK samples (suspicious but not confirmed scams)
    for _ in range(n_medium):
        features = {
            # Ownership features - some concerns
            'ownerBalance': np.random.uniform(0.3, 0.6),
            'hasRenounceOwnership': np.random.choice([0, 1], p=[0.6, 0.4]),
            'ownerVerified': np.random.choice([0, 1], p=[0.7, 0.3]),

            # Liquidity features - moderate
            'hasLiquidityLock': np.random.choice([0, 1], p=[0.5, 0.5]),
            'liquidityRatio': np.random.uniform(0.3, 0.6),
            'liquidityLockedDays': np.random.uniform(30, 180),

            # Holder features - moderate concentration
            'holderConcentration': np.random.uniform(0.4, 0.6),
            'top10HoldersPercent': np.random.uniform(0.5, 0.7),
            'holderCount': np.random.uniform(100, 1000),

            # Code features - some red flags
            'hasHiddenMint': np.random.choice([0, 1], p=[0.7, 0.3]),
            'verifiedContract': np.random.choice([0, 1], p=[0.5, 0.5]),
            'auditedByFirm': np.random.choice([0, 1], p=[0.8, 0.2]),

            # Time features - relatively new
            'contractAge': np.random.uniform(14, 90),
        }
        X.append(generate_full_feature_vector(features, risk_level='medium'))
        y.append(1)  # Medium risk

    # Generate HIGH RISK samples (likely rug pulls)
    for _ in range(n_high):
        features = {
            # Ownership features - major red flags
            'ownerBalance': np.random.uniform(0.7, 0.99),
            'hasRenounceOwnership': 0,
            'ownerBlacklisted': np.random.choice([0, 1], p=[0.7, 0.3]),
            'ownerVerified': 0,

            # Liquidity features - poor/no liquidity
            'hasLiquidityLock': 0,
            'liquidityRatio': np.random.uniform(0.05, 0.3),
            'liquidityLockedDays': np.random.uniform(0, 30),
            'lowLiquidityWarning': 1,

            # Holder features - highly concentrated
            'holderConcentration': np.random.uniform(0.7, 0.95),
            'top10HoldersPercent': np.random.uniform(0.8, 0.99),
            'holderCount': np.random.uniform(10, 100),

            # Code features - multiple red flags
            'hasHiddenMint': np.random.choice([0, 1], p=[0.3, 0.7]),
            'verifiedContract': np.random.choice([0, 1], p=[0.9, 0.1]),
            'auditedByFirm': 0,
            'hasSelfDestruct': np.random.choice([0, 1], p=[0.8, 0.2]),

            # Time features - very new
            'contractAge': np.random.uniform(0.1, 14),
        }
        X.append(generate_full_feature_vector(features, risk_level='high'))
        y.append(2)  # High risk

    return np.array(X), np.array(y)


def generate_full_feature_vector(key_features, risk_level='low'):
    """
    Generate a complete 60-feature vector from key features

    Args:
        key_features: Dict of important features
        risk_level: 'low', 'medium', or 'high'

    Returns:
        List of 60 numeric values
    """
    # Set defaults based on risk level
    if risk_level == 'low':
        defaults = {
            'hasOwnershipTransfer': 1, 'hasRenounceOwnership': 1, 'ownerBalance': 0.1,
            'ownerTransactionCount': 20, 'multipleOwners': 0, 'ownershipChangedRecently': 0,
            'ownerContractAge': 180, 'ownerIsContract': 0, 'ownerBlacklisted': 0, 'ownerVerified': 1,
            'hasLiquidityLock': 1, 'liquidityPoolSize': 100000, 'liquidityRatio': 0.7,
            'hasUniswapV2': 1, 'hasPancakeSwap': 0, 'liquidityLockedDays': 365,
            'liquidityProvidedByOwner': 0.1, 'multiplePoolsExist': 1, 'poolCreatedRecently': 0,
            'lowLiquidityWarning': 0, 'rugpullHistoryOnDEX': 0, 'slippageTooHigh': 0,
            'holderCount': 2000, 'holderConcentration': 0.2, 'top10HoldersPercent': 0.3,
            'averageHoldingTime': 60, 'suspiciousHolderPatterns': 0, 'whaleCount': 1,
            'holderGrowthRate': 0.2, 'dormantHolders': 0.2, 'newHoldersSpiking': 0, 'sellingPressure': 0.2,
            'hasHiddenMint': 0, 'hasPausableTransfers': 0, 'hasBlacklist': 0, 'hasWhitelist': 0,
            'hasTimelocks': 1, 'complexityScore': 0.3, 'hasProxyPattern': 0, 'isUpgradeable': 0,
            'hasExternalCalls': 1, 'hasSelfDestruct': 0, 'hasDelegateCall': 0, 'hasInlineAssembly': 0,
            'verifiedContract': 1, 'auditedByFirm': 1, 'openSourceCode': 1,
            'avgDailyTransactions': 50, 'transactionVelocity': 0.2, 'uniqueInteractors': 1000,
            'suspiciousPatterns': 0, 'highFailureRate': 0, 'gasOptimized': 1,
            'flashloanInteractions': 0, 'frontRunningDetected': 0,
            'contractAge': 180, 'lastActivityDays': 1, 'creationBlock': 18500000,
            'deployedDuringBullMarket': 0, 'launchFairness': 0.8
        }
    elif risk_level == 'medium':
        defaults = {
            'hasOwnershipTransfer': 1, 'hasRenounceOwnership': 0, 'ownerBalance': 0.4,
            'ownerTransactionCount': 100, 'multipleOwners': 0, 'ownershipChangedRecently': 0,
            'ownerContractAge': 45, 'ownerIsContract': 0, 'ownerBlacklisted': 0, 'ownerVerified': 0,
            'hasLiquidityLock': 0, 'liquidityPoolSize': 20000, 'liquidityRatio': 0.4,
            'hasUniswapV2': 1, 'hasPancakeSwap': 0, 'liquidityLockedDays': 90,
            'liquidityProvidedByOwner': 0.5, 'multiplePoolsExist': 0, 'poolCreatedRecently': 1,
            'lowLiquidityWarning': 0, 'rugpullHistoryOnDEX': 0, 'slippageTooHigh': 0,
            'holderCount': 200, 'holderConcentration': 0.5, 'top10HoldersPercent': 0.6,
            'averageHoldingTime': 14, 'suspiciousHolderPatterns': 0, 'whaleCount': 5,
            'holderGrowthRate': 0.8, 'dormantHolders': 0.4, 'newHoldersSpiking': 0, 'sellingPressure': 0.5,
            'hasHiddenMint': 0, 'hasPausableTransfers': 1, 'hasBlacklist': 1, 'hasWhitelist': 0,
            'hasTimelocks': 0, 'complexityScore': 0.6, 'hasProxyPattern': 1, 'isUpgradeable': 1,
            'hasExternalCalls': 1, 'hasSelfDestruct': 0, 'hasDelegateCall': 1, 'hasInlineAssembly': 1,
            'verifiedContract': 1, 'auditedByFirm': 0, 'openSourceCode': 1,
            'avgDailyTransactions': 300, 'transactionVelocity': 0.6, 'uniqueInteractors': 150,
            'suspiciousPatterns': 0, 'highFailureRate': 0, 'gasOptimized': 0,
            'flashloanInteractions': 0, 'frontRunningDetected': 0,
            'contractAge': 30, 'lastActivityDays': 0.5, 'creationBlock': 18800000,
            'deployedDuringBullMarket': 1, 'launchFairness': 0.5
        }
    else:  # high risk
        defaults = {
            'hasOwnershipTransfer': 1, 'hasRenounceOwnership': 0, 'ownerBalance': 0.9,
            'ownerTransactionCount': 300, 'multipleOwners': 0, 'ownershipChangedRecently': 1,
            'ownerContractAge': 3, 'ownerIsContract': 0, 'ownerBlacklisted': 1, 'ownerVerified': 0,
            'hasLiquidityLock': 0, 'liquidityPoolSize': 1000, 'liquidityRatio': 0.1,
            'hasUniswapV2': 0, 'hasPancakeSwap': 1, 'liquidityLockedDays': 0,
            'liquidityProvidedByOwner': 0.95, 'multiplePoolsExist': 0, 'poolCreatedRecently': 1,
            'lowLiquidityWarning': 1, 'rugpullHistoryOnDEX': 0, 'slippageTooHigh': 1,
            'holderCount': 30, 'holderConcentration': 0.9, 'top10HoldersPercent': 0.95,
            'averageHoldingTime': 2, 'suspiciousHolderPatterns': 1, 'whaleCount': 10,
            'holderGrowthRate': 2.0, 'dormantHolders': 0.8, 'newHoldersSpiking': 1, 'sellingPressure': 0.8,
            'hasHiddenMint': 1, 'hasPausableTransfers': 1, 'hasBlacklist': 1, 'hasWhitelist': 0,
            'hasTimelocks': 0, 'complexityScore': 0.9, 'hasProxyPattern': 1, 'isUpgradeable': 1,
            'hasExternalCalls': 1, 'hasSelfDestruct': 1, 'hasDelegateCall': 1, 'hasInlineAssembly': 1,
            'verifiedContract': 0, 'auditedByFirm': 0, 'openSourceCode': 0,
            'avgDailyTransactions': 1500, 'transactionVelocity': 1.5, 'uniqueInteractors': 50,
            'suspiciousPatterns': 1, 'highFailureRate': 1, 'gasOptimized': 0,
            'flashloanInteractions': 1, 'frontRunningDetected': 1,
            'contractAge': 5, 'lastActivityDays': 0.1, 'creationBlock': 18900000,
            'deployedDuringBullMarket': 1, 'launchFairness': 0.2
        }

    # Merge key features with defaults
    merged = {**defaults, **key_features}

    # Convert to ordered array (must match order in rugDetector.js)
    feature_order = [
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

    return [merged[feature] for feature in feature_order]


def train_model():
    """Train the RandomForest model and export to ONNX"""

    print("=" * 60)
    print("RugDetector Model Training Pipeline")
    print("=" * 60)

    # Step 1: Generate training data
    X, y = generate_synthetic_training_data(n_samples=5000)
    print(f"\nDataset shape: {X.shape}")
    print(f"Class distribution: Low={np.sum(y==0)}, Medium={np.sum(y==1)}, High={np.sum(y==2)}")

    # Step 2: Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Training samples: {len(X_train)}")
    print(f"Test samples: {len(X_test)}")

    # Step 3: Train model
    print("\nTraining RandomForest classifier...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    print("Training complete!")

    # Step 4: Evaluate model
    print("\n" + "=" * 60)
    print("Model Evaluation")
    print("=" * 60)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='weighted')

    print(f"\nAccuracy: {accuracy:.3f}")
    print(f"Precision: {precision:.3f}")
    print(f"Recall: {recall:.3f}")
    print(f"F1-Score: {f1:.3f}")

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Low Risk', 'Medium Risk', 'High Risk']))

    # Step 5: Cross-validation
    print("\nPerforming 5-fold cross-validation...")
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')
    print(f"CV Scores: {cv_scores}")
    print(f"Mean CV Accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")

    # Step 6: Export to ONNX
    print("\n" + "=" * 60)
    print("Exporting to ONNX")
    print("=" * 60)

    initial_type = [('float_input', FloatTensorType([None, 60]))]
    # Disable ZipMap so probabilities are a tensor (compatible with onnxruntime-node)
    onnx_model = convert_sklearn(
        model,
        initial_types=initial_type,
        target_opset=15,
        options={id(model): {"zipmap": False}}
    )

    # Save ONNX model
    onnx_path = os.path.join(os.path.dirname(__file__), '../model/rugdetector_v1.onnx')
    with open(onnx_path, 'wb') as f:
        f.write(onnx_model.SerializeToString())

    print(f"ONNX model saved to: {onnx_path}")
    print(f"Model size: {os.path.getsize(onnx_path) / 1024:.1f} KB")

    # Step 7: Save metadata
    metadata = {
        "model_name": "rugdetector_v1",
        "version": "1.0.0",
        "created_at": "2025-10-23",
        "model_type": "RandomForestClassifier",
        "num_trees": 100,
        "max_depth": 20,
        "input_features": 60,
        "output_classes": 3,
        "classes": ["low_risk", "medium_risk", "high_risk"],
        "training_samples": len(X),
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1)
    }

    metadata_path = os.path.join(os.path.dirname(__file__), '../model/rugdetector_v1_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"Metadata saved to: {metadata_path}")

    print("\n" + "=" * 60)
    print("Training pipeline complete!")
    print("=" * 60)


if __name__ == '__main__':
    train_model()
