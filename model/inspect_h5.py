#!/usr/bin/env python3
"""
Inspect H5 file structure without TensorFlow
"""
import h5py
import numpy as np

def inspect_h5(path):
    print(f"📋 Inspecting: {path}\n")

    with h5py.File(path, 'r') as f:
        def print_structure(name, obj):
            indent = "  " * name.count('/')
            if isinstance(obj, h5py.Dataset):
                print(f"{indent}{name}: shape={obj.shape}, dtype={obj.dtype}")
            else:
                print(f"{indent}{name}/ (Group)")

        f.visititems(print_structure)

        # Look for model_weights group
        if 'model_weights' in f:
            print("\n✓ Found model_weights group")
            model_weights = f['model_weights']

            # Try to list layers
            for layer_name in model_weights.keys():
                print(f"\nLayer: {layer_name}")
                layer_group = model_weights[layer_name]

                if hasattr(layer_group, 'keys'):
                    for weight_name in layer_group.keys():
                        weight_group = layer_group[weight_name]
                        if hasattr(weight_group, 'keys'):
                            for param_name in weight_group.keys():
                                param = weight_group[param_name]
                                if isinstance(param, h5py.Dataset):
                                    print(f"  {param_name}: shape={param.shape}, dtype={param.dtype}")

if __name__ == '__main__':
    inspect_h5('model/ann97_rugpull.h5')
