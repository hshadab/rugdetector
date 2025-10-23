#!/usr/bin/env python3
"""
Python Bindings for Jolt Atlas ZKML

Enables calling Rust zkML code from Python API server via subprocess.

Usage:
    from jolt_zkml.python.bindings import JoltAtlasZKML, quantize_features

    zkml = JoltAtlasZKML(model_path='model/rugdetector_v1.onnx')
    zkml.preprocess()

    features_int = quantize_features(features_float)
    proof_result = zkml.prove(features_int)
"""

import subprocess
import json
import os
from typing import Dict, List, Any, Optional

class JoltAtlasZKML:
    """
    Python interface to Jolt Atlas zkML proof generation

    This class communicates with the Rust CLI binary to:
    1. Preprocess ONNX models for zkVM
    2. Generate zkSNARK proofs for inference
    3. Verify zkSNARK proofs
    """

    def __init__(
        self,
        model_path: str,
        rust_binary: str = "./jolt_zkml/target/release/jolt_zkml_cli"
    ):
        """
        Initialize Jolt Atlas ZKML interface

        Args:
            model_path: Path to ONNX model file (e.g., 'model/rugdetector_v1.onnx')
            rust_binary: Path to compiled Rust binary

        Raises:
            FileNotFoundError: If Rust binary doesn't exist
            RuntimeError: If binary is not executable
        """
        self.model_path = model_path
        self.rust_binary = rust_binary
        self.preprocessed = False

        # Verify binary exists
        if not os.path.exists(rust_binary):
            raise FileNotFoundError(
                f"Rust binary not found: {rust_binary}\n"
                f"Build it with: cd jolt_zkml && cargo build --release\n"
                f"See JOLT_ATLAS_INTEGRATION.md for instructions"
            )

        # Verify binary is executable
        if not os.access(rust_binary, os.X_OK):
            raise RuntimeError(f"Binary is not executable: {rust_binary}")

        # Verify model exists
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

    def preprocess(self) -> None:
        """
        Preprocess the model (one-time setup)

        This step:
        1. Loads the ONNX model
        2. Decodes it into Jolt zkVM bytecode
        3. Generates preprocessing data for the prover

        Time: ~200ms
        Should be called on server startup

        Raises:
            RuntimeError: If preprocessing fails
        """
        try:
            result = subprocess.run(
                [self.rust_binary, "preprocess", "--model", self.model_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                raise RuntimeError(f"Preprocessing failed: {error_msg}")

            response = json.loads(result.stdout)
            if response.get('status') != 'preprocessed':
                raise RuntimeError(f"Unexpected response: {response}")

            self.preprocessed = True
            print(f"✅ Model preprocessed successfully: {self.model_path}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("Preprocessing timed out (>10s)")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response: {e}")

    def prove(self, features: List[int]) -> Dict[str, Any]:
        """
        Generate zkSNARK proof for inference

        Args:
            features: List of 60 quantized features (i32)
                     Use quantize_features() to convert from float

        Returns:
            {
                'proof': str (hex-encoded zkSNARK proof),
                'output': dict (model predictions),
                'verifying_key': str (hex-encoded verification key)
            }

        Time: ~300-500ms

        Raises:
            RuntimeError: If model not preprocessed or proof generation fails
            ValueError: If features list has wrong length
        """
        if not self.preprocessed:
            raise RuntimeError(
                "Model must be preprocessed before proving. "
                "Call .preprocess() first"
            )

        if len(features) != 60:
            raise ValueError(f"Expected 60 features, got {len(features)}")

        # Verify all features are integers
        if not all(isinstance(f, int) for f in features):
            raise ValueError("All features must be integers (i32)")

        try:
            # Prepare input
            input_json = json.dumps({'features': features})

            # Call Rust binary
            result = subprocess.run(
                [self.rust_binary, "prove", "--model", self.model_path],
                input=input_json,
                capture_output=True,
                text=True,
                timeout=5  # Proving takes ~500ms
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                raise RuntimeError(f"Proof generation failed: {error_msg}")

            proof_data = json.loads(result.stdout)

            # Validate response structure
            required_keys = ['proof', 'output', 'verifying_key']
            for key in required_keys:
                if key not in proof_data:
                    raise RuntimeError(f"Missing key in response: {key}")

            return proof_data

        except subprocess.TimeoutExpired:
            raise RuntimeError("Proof generation timed out (>5s)")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response: {e}")

    def verify(
        self,
        proof: str,
        verifying_key: str,
        output: dict
    ) -> bool:
        """
        Verify a zkSNARK proof

        Args:
            proof: Hex-encoded zkSNARK proof
            verifying_key: Hex-encoded verification key
            output: Expected program output

        Returns:
            True if proof is valid, False otherwise

        Time: ~100-200ms

        Raises:
            RuntimeError: If verification process fails
        """
        try:
            verify_input = json.dumps({
                'proof': proof,
                'verifying_key': verifying_key,
                'output': output
            })

            result = subprocess.run(
                [self.rust_binary, "verify"],
                input=verify_input,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                # Verification failed (invalid proof)
                return False

            verify_result = json.loads(result.stdout)
            return verify_result.get('valid', False)

        except subprocess.TimeoutExpired:
            raise RuntimeError("Verification timed out (>5s)")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response: {e}")

    def version(self) -> Dict[str, Any]:
        """
        Get version information about the zkML binary

        Returns:
            {
                'name': str,
                'version': str,
                'description': str,
                'status': str,
                'dependencies_required': list
            }
        """
        try:
            result = subprocess.run(
                [self.rust_binary, "version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return {'error': result.stderr}

            return json.loads(result.stdout)

        except Exception as e:
            return {'error': str(e)}


def quantize_features(features: Dict[str, float]) -> List[int]:
    """
    Quantize float features to i32 for Jolt Atlas zkVM

    Jolt Atlas requires integer inputs, so we quantize floats to i32:
    - Scale: value * 1000 (preserves 3 decimal places)
    - Clamp to i32 range: [-2^31, 2^31-1]

    Args:
        features: Dictionary of feature_name -> float_value (60 features)

    Returns:
        List of 60 quantized i32 values

    Example:
        features = {
            'ownerBalance': 0.85,
            'liquidityRatio': 0.42,
            ...
        }
        quantized = quantize_features(features)  # [850, 420, ...]
    """
    if len(features) != 60:
        raise ValueError(f"Expected 60 features, got {len(features)}")

    quantized = []

    # Sort keys for consistent ordering
    for key in sorted(features.keys()):
        value = features[key]

        # Scale to integer (3 decimal places precision)
        scaled = int(value * 1000)

        # Clamp to i32 range: [-2^31, 2^31-1]
        clamped = max(-2147483648, min(2147483647, scaled))

        quantized.append(clamped)

    return quantized


def dequantize_output(quantized: List[int]) -> List[float]:
    """
    Convert quantized i32 output back to floats

    Inverse of quantize_features()

    Args:
        quantized: List of i32 values

    Returns:
        List of float values
    """
    return [float(q) / 1000.0 for q in quantized]


# Example usage
if __name__ == '__main__':
    import sys

    # Check if binary exists
    binary_path = "./jolt_zkml/target/release/jolt_zkml_cli"

    if not os.path.exists(binary_path):
        print("⚠️  Rust binary not found!")
        print(f"   Expected: {binary_path}")
        print()
        print("Build it with:")
        print("  cd jolt_zkml")
        print("  cargo build --release")
        print()
        print("See JOLT_ATLAS_INTEGRATION.md for full instructions")
        sys.exit(1)

    # Test version
    zkml = JoltAtlasZKML(model_path='model/rugdetector_v1.onnx')
    version_info = zkml.version()
    print(json.dumps(version_info, indent=2))

    # Test quantization
    sample_features = {
        f'feature_{i}': float(i) / 10.0
        for i in range(60)
    }
    quantized = quantize_features(sample_features)
    print(f"\n✅ Quantized {len(quantized)} features")
    print(f"   Example: feature_0 (0.0) -> {quantized[0]}")
    print(f"   Example: feature_5 (0.5) -> {quantized[5]}")
