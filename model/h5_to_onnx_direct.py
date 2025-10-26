#!/usr/bin/env python3
"""
Load weights directly from H5 file using h5py and convert to ONNX via PyTorch
No TensorFlow required!
"""

import h5py
import numpy as np
import torch
import torch.nn as nn
import sys

class RugDetectorFromH5(nn.Module):
    """PyTorch model built from H5 weights"""
    def __init__(self, layer_sizes):
        super(RugDetectorFromH5, self).__init__()

        layers = []
        for i in range(len(layer_sizes) - 1):
            layers.append(nn.Linear(layer_sizes[i], layer_sizes[i+1]))
            if i < len(layer_sizes) - 2:  # Add ReLU except for last layer
                layers.append(nn.ReLU())

        self.model = nn.Sequential(*layers)

    def forward(self, x):
        return self.model(x)

def load_weights_from_h5(h5_path):
    """Load weights from H5 file"""
    print(f"📦 Loading weights from: {h5_path}")

    weights_list = []

    with h5py.File(h5_path, 'r') as f:
        model_weights = f['model_weights']

        # Get Dense layers in order (dense_11, dense_12, ..., dense_18)
        dense_layers = sorted([k for k in model_weights.keys() if k.startswith('dense')])

        for layer_name in dense_layers:
            layer_group = model_weights[layer_name][layer_name]

            # Load kernel (weight matrix) and bias
            kernel = layer_group['kernel:0'][:]  # Shape: [in, out]
            bias = layer_group['bias:0'][:]

            weights_list.append({
                'name': layer_name,
                'kernel': kernel,
                'bias': bias
            })

            print(f"   {layer_name}: kernel={kernel.shape}, bias={bias.shape}")

    return weights_list

def convert_h5_to_onnx(h5_path, onnx_path, opset=11):
    """Convert H5 model to ONNX"""
    print(f"\n🔧 Converting H5 to ONNX")
    print(f"   Input: {h5_path}")
    print(f"   Output: {onnx_path}")

    # Load weights
    weights_list = load_weights_from_h5(h5_path)

    # Extract layer sizes
    layer_sizes = [weights_list[0]['kernel'].shape[0]]  # Input size
    for w in weights_list:
        layer_sizes.append(w['kernel'].shape[1])  # Output size

    print(f"\n✓ Layer architecture: {layer_sizes}")

    # Create PyTorch model
    print("\n🔄 Creating PyTorch model...")
    model = RugDetectorFromH5(layer_sizes)

    # Transfer weights
    print("📋 Transferring weights...")
    torch_linears = [m for m in model.model if isinstance(m, nn.Linear)]

    for i, (torch_linear, weights) in enumerate(zip(torch_linears, weights_list)):
        # H5 kernel shape: [in, out]
        # PyTorch Linear weight shape: [out, in]
        # So we need to transpose
        kernel_transposed = weights['kernel'].T
        torch_linear.weight.data = torch.from_numpy(kernel_transposed).float()
        torch_linear.bias.data = torch.from_numpy(weights['bias']).float()

        print(f"   Layer {i+1}: {weights['name']} -> PyTorch Linear")

    print("✓ All weights transferred")

    # Set to eval mode
    model.eval()

    # Export to ONNX
    print(f"\n📦 Exporting to ONNX (opset {opset})...")

    dummy_input = torch.randn(1, layer_sizes[0], dtype=torch.float32)

    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        export_params=True,
        opset_version=opset,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
    )

    print(f"✅ ONNX export complete!")

    # Verify with onnx
    try:
        import onnx
        onnx_model = onnx.load(onnx_path)
        onnx.checker.check_model(onnx_model)
        print("✓ ONNX model is valid")

        # Print model info
        print("\n📋 ONNX Model Info:")
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

    return onnx_path

if __name__ == '__main__':
    h5_file = 'model/ann97_rugpull.h5'
    onnx_file = 'model/ann97_from_keras.onnx'

    if len(sys.argv) > 1:
        h5_file = sys.argv[1]
    if len(sys.argv) > 2:
        onnx_file = sys.argv[2]

    try:
        convert_h5_to_onnx(h5_file, onnx_file)
        print("\n✅ SUCCESS! Model converted to ONNX format")
        print(f"   Ready for Jolt-Atlas zkML testing")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
