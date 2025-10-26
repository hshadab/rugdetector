#!/usr/bin/env python3
"""
Convert Keras model (ann97.h5) to ONNX format for Jolt-Atlas zkML
Extracts Keras weights and rebuilds as PyTorch model for clean ONNX export
"""

import tensorflow as tf
from tensorflow import keras
import numpy as np
import torch
import torch.nn as nn
import sys

class KerasToTorchNN(nn.Module):
    """PyTorch model rebuilt from Keras weights"""
    def __init__(self, layer_sizes):
        super(KerasToTorchNN, self).__init__()

        layers = []
        for i in range(len(layer_sizes) - 1):
            layers.append(nn.Linear(layer_sizes[i], layer_sizes[i+1]))
            if i < len(layer_sizes) - 2:  # Add activation except for last layer
                layers.append(nn.ReLU())

        self.model = nn.Sequential(*layers)

    def forward(self, x):
        return self.model(x)

def convert_keras_to_onnx(keras_path, onnx_path, opset=11):
    """
    Convert Keras H5 model to ONNX format by extracting weights
    and rebuilding in PyTorch
    """
    print(f"🔧 Converting Keras model to ONNX")
    print(f"   Input: {keras_path}")
    print(f"   Output: {onnx_path}")
    print(f"   ONNX Opset: {opset}")

    # Load Keras model
    print("\n📦 Loading Keras model...")
    keras_model = keras.models.load_model(keras_path)

    # Print model summary
    print("\n📊 Keras Model Architecture:")
    keras_model.summary()

    # Extract layer sizes
    layer_sizes = []
    keras_layers = [l for l in keras_model.layers if isinstance(l, keras.layers.Dense)]

    if len(keras_layers) > 0:
        # Get input size from first layer's weights
        first_weights = keras_layers[0].get_weights()[0]
        input_size = first_weights.shape[0]
        layer_sizes.append(input_size)

        for layer in keras_layers:
            layer_sizes.append(layer.units)

    print(f"\n✓ Detected layer sizes: {layer_sizes}")

    # Create PyTorch model
    print("\n🔄 Creating PyTorch model...")
    torch_model = KerasToTorchNN(layer_sizes)

    # Transfer weights from Keras to PyTorch
    print("📋 Transferring weights...")

    # Get all PyTorch Linear layers
    torch_linears = [m for m in torch_model.model if isinstance(m, nn.Linear)]

    # Transfer weights from each Keras Dense layer to corresponding PyTorch Linear
    for i, keras_layer in enumerate(keras_layers):
        if i >= len(torch_linears):
            break

        torch_linear = torch_linears[i]

        # Get Keras weights (shape: [in_features, out_features])
        keras_weights = keras_layer.get_weights()
        weight = keras_weights[0]  # Weight matrix
        bias = keras_weights[1] if len(keras_weights) > 1 else None

        # PyTorch Linear expects [out_features, in_features], so transpose
        torch_linear.weight.data = torch.from_numpy(weight.T).float()
        if bias is not None:
            torch_linear.bias.data = torch.from_numpy(bias).float()

        print(f"   Layer {i+1}: {keras_layer.name} ({weight.shape}) -> PyTorch Linear ({torch_linear.weight.shape})")

    print("✓ All weights transferred")

    # Set model to eval mode
    torch_model.eval()

    # Export to ONNX
    print(f"\n📦 Exporting PyTorch model to ONNX...")

    dummy_input = torch.randn(1, layer_sizes[0], dtype=torch.float32)

    torch.onnx.export(
        torch_model,
        dummy_input,
        onnx_path,
        export_params=True,
        opset_version=opset,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
    )

    print(f"✅ ONNX export complete: {onnx_path}")

    # Verify with onnx library if available
    try:
        import onnx
        onnx_model = onnx.load(onnx_path)
        onnx.checker.check_model(onnx_model)
        print("✓ ONNX model is valid")

        # Print model info
        print("\n📋 ONNX Model Info:")
        print(f"   IR Version: {onnx_model.ir_version}")
        print(f"   Producer: {onnx_model.producer_name}")
        print(f"   Opset: {onnx_model.opset_import[0].version}")
        print(f"   Inputs: {[inp.name for inp in onnx_model.graph.input]}")
        print(f"   Outputs: {[out.name for out in onnx_model.graph.output]}")

        # Print operations used
        print("\n🔧 Operations in model:")
        ops = set()
        for node in onnx_model.graph.node:
            ops.add(node.op_type)
        for op in sorted(ops):
            print(f"   - {op}")
    except ImportError:
        print("⚠️  onnx library not available for validation")

    # Test inference to verify
    print("\n🧪 Testing inference...")
    test_input = np.random.randn(1, layer_sizes[0]).astype(np.float32)

    # Keras prediction
    keras_output = keras_model.predict(test_input, verbose=0)

    # PyTorch prediction
    with torch.no_grad():
        torch_input = torch.from_numpy(test_input)
        torch_output = torch_model(torch_input).numpy()

    # Compare
    diff = np.abs(keras_output - torch_output).max()
    print(f"   Max difference between Keras and PyTorch: {diff:.6f}")

    if diff < 1e-4:
        print("   ✓ Weight transfer successful!")
    else:
        print(f"   ⚠️  Warning: High difference detected")

    return onnx_path

if __name__ == '__main__':
    # Default paths
    keras_model = 'model/ann97_rugpull.h5'
    onnx_model = 'model/ann97_from_keras.onnx'

    if len(sys.argv) > 1:
        keras_model = sys.argv[1]
    if len(sys.argv) > 2:
        onnx_model = sys.argv[2]

    try:
        convert_keras_to_onnx(keras_model, onnx_model)
        print("\n✅ SUCCESS! Model converted to ONNX format")
        print(f"   You can now test with: ./zkml-jolt-atlas/target/release/zkml-jolt-core prove --model {onnx_model} ...")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
