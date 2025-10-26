#!/usr/bin/env python3
"""
Extract weights from Keras model and save as numpy arrays
"""

import tensorflow as tf
from tensorflow import keras
import numpy as np
import sys
import pickle

def extract_keras_weights(keras_path, weights_path):
    """Extract weights from Keras model and save as pickle"""
    print(f"📦 Loading Keras model: {keras_path}")
    model = keras.models.load_model(keras_path)

    print("\n📊 Model Architecture:")
    model.summary()

    # Extract Dense layers only
    dense_layers = [l for l in model.layers if isinstance(l, keras.layers.Dense)]
    print(f"\n✓ Found {len(dense_layers)} Dense layers")

    # Get input size from first layer
    first_weights = dense_layers[0].get_weights()[0]
    input_size = first_weights.shape[0]
    print(f"✓ Input size: {input_size}")

    # Extract all weights
    weights_dict = {
        'input_size': input_size,
        'layers': []
    }

    for i, layer in enumerate(dense_layers):
        layer_weights = layer.get_weights()
        weight = layer_weights[0]  # Weight matrix [in, out]
        bias = layer_weights[1] if len(layer_weights) > 1 else None

        weights_dict['layers'].append({
            'name': layer.name,
            'weight': weight,
            'bias': bias,
            'units': layer.units
        })

        print(f"   Layer {i+1}: {layer.name} - weight shape {weight.shape}, bias shape {bias.shape if bias is not None else None}")

    # Save as pickle
    with open(weights_path, 'wb') as f:
        pickle.dump(weights_dict, f)

    print(f"\n✅ Weights saved to: {weights_path}")
    return weights_path

if __name__ == '__main__':
    keras_model = 'model/ann97_rugpull.h5'
    weights_file = 'model/ann97_weights.pkl'

    if len(sys.argv) > 1:
        keras_model = sys.argv[1]
    if len(sys.argv) > 2:
        weights_file = sys.argv[2]

    extract_keras_weights(keras_model, weights_file)
