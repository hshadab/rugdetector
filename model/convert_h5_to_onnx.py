#!/usr/bin/env python3
"""
Convert Keras H5 model to ONNX format
Converts the pre-trained ann97.h5 rug pull detection model
"""

import tensorflow as tf
import tf2onnx
import onnx
import sys
from pathlib import Path

def convert_h5_to_onnx(h5_path, onnx_path):
    """Convert Keras H5 model to ONNX"""

    print("="*70)
    print("Converting Keras H5 Model to ONNX")
    print("="*70)
    print(f"\nInput:  {h5_path}")
    print(f"Output: {onnx_path}")

    # Load Keras model
    print("\n[1] Loading Keras model...")
    try:
        model = tf.keras.models.load_model(h5_path)
        print(f"  ✓ Model loaded successfully")
    except Exception as e:
        print(f"  ✗ Error loading model: {e}")
        return False

    # Print model summary
    print("\n[2] Model Architecture:")
    model.summary()

    # Get input/output specs
    input_signature = [tf.TensorSpec(model.inputs[0].shape, model.inputs[0].dtype, name='input')]
    print(f"\n  Input shape: {model.inputs[0].shape}")
    print(f"  Output shape: {model.outputs[0].shape}")

    # Convert to ONNX
    print("\n[3] Converting to ONNX...")
    try:
        onnx_model, _ = tf2onnx.convert.from_keras(
            model,
            input_signature=input_signature,
            opset=15,
            output_path=str(onnx_path)
        )
        print(f"  ✓ Conversion successful")
    except Exception as e:
        print(f"  ✗ Error converting: {e}")
        return False

    # Verify ONNX model
    print("\n[4] Verifying ONNX model...")
    try:
        onnx_model = onnx.load(str(onnx_path))
        onnx.checker.check_model(onnx_model)
        print(f"  ✓ ONNX model is valid")
    except Exception as e:
        print(f"  ✗ ONNX validation failed: {e}")
        return False

    # Get file sizes
    h5_size = Path(h5_path).stat().st_size / 1024 / 1024
    onnx_size = Path(onnx_path).stat().st_size / 1024 / 1024

    print("\n"+"="*70)
    print("Conversion Complete!")
    print("="*70)
    print(f"\nH5 size:   {h5_size:.2f} MB")
    print(f"ONNX size: {onnx_size:.2f} MB")
    print(f"\nModel details:")
    print(f"  - Input features: {model.inputs[0].shape[1]} (from shape {model.inputs[0].shape})")
    print(f"  - Output: {model.outputs[0].shape}")
    print(f"  - Layers: {len(model.layers)}")

    return True


if __name__ == "__main__":
    model_dir = Path(__file__).parent
    h5_file = model_dir / "ann97_rugpull.h5"
    onnx_file = model_dir / "ann97_rugpull.onnx"

    if not h5_file.exists():
        print(f"Error: {h5_file} not found")
        sys.exit(1)

    success = convert_h5_to_onnx(h5_file, onnx_file)
    sys.exit(0 if success else 1)
