#!/usr/bin/env python3
"""
Example: Using Jolt Atlas zkML with RugDetector

This example demonstrates the full pipeline:
1. Extract features from a contract
2. Quantize features for zkVM
3. Generate zkSNARK proof
4. Verify the proof

Prerequisites:
- Jolt Atlas binary built: jolt_zkml/target/release/jolt_zkml_cli
- ONNX model: model/rugdetector_v1.onnx
"""

import sys
import json
import subprocess
from typing import Dict, List

# Add jolt_zkml to path
sys.path.insert(0, 'jolt_zkml/python')

try:
    from bindings import JoltAtlasZKML, quantize_features
    JOLT_AVAILABLE = True
except ImportError:
    print("⚠️  Jolt Atlas bindings not available")
    JOLT_AVAILABLE = False


def extract_features(contract_address: str, blockchain: str = 'ethereum') -> Dict[str, float]:
    """
    Extract 60 features from a smart contract

    Args:
        contract_address: Contract address (0x...)
        blockchain: Network name (ethereum, bsc, polygon)

    Returns:
        Dictionary of 60 features with float values
    """
    print(f"📊 Extracting features from {contract_address}...")

    result = subprocess.run(
        ['python3', 'model/extract_features.py', contract_address, blockchain],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        raise RuntimeError(f"Feature extraction failed: {result.stderr}")

    features = json.loads(result.stdout)
    print(f"✅ Extracted {len(features)} features")

    return features


def analyze_with_zkml(contract_address: str, blockchain: str = 'ethereum'):
    """
    Analyze a contract with REAL Jolt Atlas zkML

    This function:
    1. Extracts features from the contract
    2. Quantizes them to i32 for the zkVM
    3. Generates a zkSNARK proof of inference
    4. Returns the result with cryptographic proof
    """

    if not JOLT_AVAILABLE:
        print("❌ Jolt Atlas not available. Build it first:")
        print("   cd jolt_zkml && cargo build --release")
        return None

    # Step 1: Extract features
    features_float = extract_features(contract_address, blockchain)

    # Step 2: Quantize for zkVM
    print("\n🔢 Quantizing features to i32...")
    features_int = quantize_features(features_float)
    print(f"✅ Quantized {len(features_int)} values")
    print(f"   Range: [{min(features_int)}, {max(features_int)}]")

    # Step 3: Initialize zkML prover
    print("\n🔐 Initializing Jolt Atlas zkML...")
    zkml = JoltAtlasZKML(model_path='model/rugdetector_v1.onnx')

    # Step 4: Preprocess model (one-time setup)
    print("⚙️  Preprocessing model...")
    zkml.preprocess()
    print("✅ Preprocessing complete (~200ms)")

    # Step 5: Generate zkSNARK proof
    print("\n🔮 Generating zkSNARK proof...")
    proof_result = zkml.prove(features_int)
    print("✅ Proof generated (~500ms)")
    print(f"   Proof size: {len(proof_result['proof']) // 2} bytes")

    # Step 6: Parse output
    output = proof_result['output']
    probabilities = output.get('probabilities', [0, 0, 0])

    risk_score = probabilities[2]  # High risk probability
    risk_category = (
        'high' if risk_score >= 0.6 else
        'medium' if risk_score >= 0.3 else
        'low'
    )

    print(f"\n📈 Analysis Results:")
    print(f"   Risk Score: {risk_score:.2f}")
    print(f"   Category: {risk_category.upper()}")
    print(f"   Confidence: {max(probabilities):.2f}")

    # Step 7: Verify proof
    print("\n🔍 Verifying zkSNARK proof...")
    is_valid = zkml.verify(
        proof=proof_result['proof'],
        verifying_key=proof_result['verifying_key'],
        output=proof_result['output']
    )
    print(f"✅ Proof valid: {is_valid}")

    return {
        'contract_address': contract_address,
        'blockchain': blockchain,
        'risk_score': risk_score,
        'risk_category': risk_category,
        'confidence': max(probabilities),
        'features': features_float,
        'zkml_proof': {
            'proof': proof_result['proof'],
            'verifying_key': proof_result['verifying_key'],
            'output': proof_result['output'],
            'protocol': 'jolt-atlas-v1',
            'verified': is_valid
        }
    }


def example_basic():
    """Example 1: Basic analysis with zkML"""
    print("=" * 60)
    print("Example 1: Basic Contract Analysis with Jolt Atlas zkML")
    print("=" * 60)

    # Uniswap V2 Factory (known safe contract)
    contract = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"

    result = analyze_with_zkml(contract, blockchain='ethereum')

    if result:
        print("\n" + "=" * 60)
        print("✅ Analysis Complete with Cryptographic Proof")
        print("=" * 60)
        print(json.dumps(result, indent=2))


def example_quantization_only():
    """Example 2: Just test quantization without zkML"""
    print("=" * 60)
    print("Example 2: Feature Extraction and Quantization")
    print("=" * 60)

    contract = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"

    # Extract features
    features_float = extract_features(contract, blockchain='ethereum')

    # Show some features
    print("\n📊 Sample Features (float):")
    for key in list(features_float.keys())[:5]:
        print(f"   {key}: {features_float[key]:.4f}")

    # Quantize
    features_int = quantize_features(features_float)

    print("\n🔢 Sample Features (i32):")
    for i, key in enumerate(list(features_float.keys())[:5]):
        print(f"   {key}: {features_float[key]:.4f} → {features_int[i]}")

    print("\n✅ Ready for Jolt Atlas zkVM")
    print(f"   Total features: {len(features_int)}")
    print(f"   All within i32 range: {all(-2147483648 <= v <= 2147483647 for v in features_int)}")


def example_batch_analysis():
    """Example 3: Batch analysis of multiple contracts"""
    print("=" * 60)
    print("Example 3: Batch Contract Analysis")
    print("=" * 60)

    contracts = [
        ("0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f", "Uniswap V2 Factory"),
        ("0xdAC17F958D2ee523a2206206994597C13D831ec7", "Tether USDT"),
        ("0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984", "Uniswap Token"),
    ]

    results = []

    for address, name in contracts:
        print(f"\n📝 Analyzing: {name}")
        print(f"   Address: {address}")

        try:
            result = analyze_with_zkml(address, blockchain='ethereum')
            if result:
                results.append({
                    'name': name,
                    'address': address,
                    'risk_score': result['risk_score'],
                    'risk_category': result['risk_category']
                })
        except Exception as e:
            print(f"❌ Error: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("📊 Batch Analysis Summary")
    print("=" * 60)

    for r in results:
        risk_emoji = "🟢" if r['risk_category'] == 'low' else "🟡" if r['risk_category'] == 'medium' else "🔴"
        print(f"{risk_emoji} {r['name']}: {r['risk_score']:.2f} ({r['risk_category'].upper()})")


def main():
    """Run examples"""

    print("\n" + "🤖 Jolt Atlas zkML Integration Examples\n")

    # Check if binary is built
    import os
    binary_path = "jolt_zkml/target/release/jolt_zkml_cli"

    if not os.path.exists(binary_path):
        print("⚠️  Jolt Atlas binary not found!")
        print(f"   Expected: {binary_path}")
        print()
        print("Build it with:")
        print("  cd jolt_zkml")
        print("  cargo build --release")
        print()
        print("For now, running quantization example only...")
        print()

        example_quantization_only()
        return

    # Run examples
    while True:
        print("\n" + "=" * 60)
        print("Choose an example:")
        print("  1. Basic analysis with zkML proof")
        print("  2. Feature extraction and quantization")
        print("  3. Batch analysis of multiple contracts")
        print("  q. Quit")
        print("=" * 60)

        choice = input("\nYour choice: ").strip().lower()

        if choice == '1':
            example_basic()
        elif choice == '2':
            example_quantization_only()
        elif choice == '3':
            example_batch_analysis()
        elif choice == 'q':
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice")


if __name__ == '__main__':
    main()
