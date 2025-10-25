#!/usr/bin/env python3
"""
Python inference helper for RugDetector

Purpose: Handle ONNX models that output non-tensor types (ZipMap sequence of maps),
which onnxruntime-node cannot return. Reads features JSON from stdin and returns
probabilities, risk score, category, and confidence as JSON to stdout.
"""

import sys
import json
import os

try:
    import onnxruntime as ort
    import numpy as np
except Exception as e:
    print(json.dumps({"error": f"Missing dependencies for Python inference: {e}"}), file=sys.stderr)
    sys.exit(2)


MODEL_PATH = os.path.join(os.path.dirname(__file__), 'rugdetector_v1.onnx')


FEATURE_ORDER = [
    # Ownership (10)
    'hasOwnershipTransfer', 'hasRenounceOwnership', 'ownerBalance', 'ownerTransactionCount',
    'multipleOwners', 'ownershipChangedRecently', 'ownerContractAge', 'ownerIsContract',
    'ownerBlacklisted', 'ownerVerified',
    # Liquidity (12)
    'hasLiquidityLock', 'liquidityPoolSize', 'liquidityRatio', 'hasUniswapV2',
    'hasPancakeSwap', 'liquidityLockedDays', 'liquidityProvidedByOwner', 'multiplePoolsExist',
    'poolCreatedRecently', 'lowLiquidityWarning', 'rugpullHistoryOnDEX', 'slippageTooHigh',
    # Holders (10)
    'holderCount', 'holderConcentration', 'top10HoldersPercent', 'averageHoldingTime',
    'suspiciousHolderPatterns', 'whaleCount', 'holderGrowthRate', 'dormantHolders',
    'newHoldersSpiking', 'sellingPressure',
    # Contract code (15)
    'hasHiddenMint', 'hasPausableTransfers', 'hasBlacklist', 'hasWhitelist',
    'hasTimelocks', 'complexityScore', 'hasProxyPattern', 'isUpgradeable',
    'hasExternalCalls', 'hasSelfDestruct', 'hasDelegateCall', 'hasInlineAssembly',
    'verifiedContract', 'auditedByFirm', 'openSourceCode',
    # Transaction patterns (8)
    'avgDailyTransactions', 'transactionVelocity', 'uniqueInteractors', 'suspiciousPatterns',
    'highFailureRate', 'gasOptimized', 'flashloanInteractions', 'frontRunningDetected',
    # Time-based (5)
    'contractAge', 'lastActivityDays', 'creationBlock', 'deployedDuringBullMarket',
    'launchFairness'
]


def to_array(features: dict):
    arr = []
    for name in FEATURE_ORDER:
        v = features.get(name, 0)
        if isinstance(v, bool):
            v = 1 if v else 0
        try:
            v = float(v)
        except Exception:
            v = 0.0
        arr.append(v)
    if len(arr) != 60:
        raise ValueError(f"Expected 60 features, got {len(arr)}")
    return np.array([arr], dtype=np.float32)


def infer(features: dict):
    sess = ort.InferenceSession(MODEL_PATH, providers=['CPUExecutionProvider'])
    x = to_array(features)
    input_name = sess.get_inputs()[0].name
    outputs = sess.run(None, {input_name: x})

    # Pick probability vector in a robust way:
    # - Prefer sequence<map> (ZipMap) if present
    # - Else find a float ndarray output with length >= 3
    probs = None
    for out in outputs:
        if isinstance(out, list) and out and isinstance(out[0], dict):
            m = out[0]
            keys = sorted(m.keys())
            if keys == [0, 1, 2]:
                probs = [m[0], m[1], m[2]]
            else:
                probs = [m.get(k, 0.0) for k in keys[:3]]
            break
    if probs is None:
        for out in outputs:
            if isinstance(out, np.ndarray) and out.dtype.kind in ('f', 'c') and out.size >= 3:
                probs = list(map(float, out.reshape(-1)[:3]))
                break
    if probs is None:
        probs = [0.33, 0.33, 0.34]

    low, med, high = map(float, probs[:3])

    if high > 0.6:
        category = 'high'
        score = 0.6 + (high - 0.6) * 0.4 / 0.4
        conf = high
    elif med > 0.5:
        category = 'medium'
        score = 0.3 + (med - 0.5) * 0.3 / 0.5
        conf = med
    else:
        category = 'low'
        score = low * 0.3
        conf = low

    return {
        'riskScore': round(float(score), 2),
        'riskCategory': category,
        'confidence': round(float(conf), 2),
        'probabilities': {
            'low': round(low, 3),
            'medium': round(med, 3),
            'high': round(high, 3),
        }
    }


def main():
    try:
        data = json.load(sys.stdin)
        features = data.get('features') if isinstance(data, dict) else None
        if not isinstance(features, dict):
            raise ValueError('Invalid input: expected {"features": {...}} JSON on stdin')
        result = infer(features)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
