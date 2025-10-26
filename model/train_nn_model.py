#!/usr/bin/env python3
"""
Train a neural network RugDetector model compatible with Jolt-Atlas zkML
Replaces tree ensemble with MLP that works with onnx-tracer
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import onnx
from onnx import numpy_helper

class RugDetectorNN(nn.Module):
    """
    Simple MLP for rug pull detection - compatible with Jolt-Atlas
    Uses only operations supported by onnx-tracer: Linear, ReLU, Softmax
    """
    def __init__(self, input_size=60, hidden_sizes=[128, 64, 32], num_classes=3):
        super(RugDetectorNN, self).__init__()

        layers = []
        prev_size = input_size

        # Hidden layers with ReLU
        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(prev_size, hidden_size))
            layers.append(nn.ReLU())
            prev_size = hidden_size

        # Output layer
        layers.append(nn.Linear(prev_size, num_classes))

        self.model = nn.Sequential(*layers)

    def forward(self, x):
        logits = self.model(x)
        # Return logits - softmax will be applied during export
        return logits

class RugPullDataset(Dataset):
    """Dataset for rug pull detection"""
    def __init__(self, features, labels):
        self.features = torch.FloatTensor(features)
        self.labels = torch.LongTensor(labels)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]

def generate_synthetic_data(n_samples=10000):
    """
    Generate synthetic rug pull detection data
    Features: 60 contract metrics
    Labels: 0=safe, 1=medium_risk, 2=high_risk
    """
    np.random.seed(42)

    features = []
    labels = []

    for _ in range(n_samples):
        label = np.random.choice([0, 1, 2], p=[0.6, 0.3, 0.1])  # Most contracts safe

        feature_vector = np.random.random(60)

        # Inject patterns based on risk level
        if label == 2:  # High risk
            feature_vector[0:10] *= 0.3  # Low liquidity
            feature_vector[10:20] *= 1.8  # High ownership concentration
            feature_vector[20:30] *= 0.2  # Low holder count
        elif label == 1:  # Medium risk
            feature_vector[0:10] *= 0.7
            feature_vector[10:20] *= 1.3

        features.append(feature_vector)
        labels.append(label)

    return np.array(features, dtype=np.float32), np.array(labels, dtype=np.int64)

def train_model(model, train_loader, val_loader, epochs=50, lr=0.001):
    """Train the neural network"""
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    print("🚀 Training RugDetector Neural Network...")

    best_val_acc = 0
    for epoch in range(epochs):
        # Training
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0

        for features, labels in train_loader:
            optimizer.zero_grad()
            outputs = model(features)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            train_total += labels.size(0)
            train_correct += (predicted == labels).sum().item()

        # Validation
        model.eval()
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for features, labels in val_loader:
                outputs = model(features)
                _, predicted = torch.max(outputs.data, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()

        train_acc = 100 * train_correct / train_total
        val_acc = 100 * val_correct / val_total

        if val_acc > best_val_acc:
            best_val_acc = val_acc

        if (epoch + 1) % 10 == 0:
            print(f"Epoch [{epoch+1}/{epochs}] "
                  f"Train Loss: {train_loss/len(train_loader):.4f} "
                  f"Train Acc: {train_acc:.2f}% "
                  f"Val Acc: {val_acc:.2f}%")

    print(f"✅ Training complete! Best validation accuracy: {best_val_acc:.2f}%")
    return model

def export_to_onnx(model, output_path, input_size=60, use_float=False):
    """Export model to ONNX format for Jolt-Atlas"""
    model.eval()

    if use_float:
        # Simple float32 export without int conversion
        dummy_input = torch.randn(1, input_size, dtype=torch.float32)

        print(f"📦 Exporting model to ONNX: {output_path}")

        torch.onnx.export(
            model,
            dummy_input,
            output_path,
            export_params=True,
            opset_version=11,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
        )

        print(f"✅ ONNX model exported: {output_path}")
        print(f"   Input type: FLOAT32")
        return output_path

    # Create dummy input with integer type (scaled floats)
    dummy_input = torch.randint(-1000, 1000, (1, input_size), dtype=torch.int32)

    # Convert to float for inference
    dummy_input_float = dummy_input.float()

    print(f"📦 Exporting model to ONNX: {output_path}")

    torch.onnx.export(
        model,
        dummy_input_float,
        output_path,
        export_params=True,
        opset_version=11,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
    )

    # Load and modify to accept int32 inputs
    onnx_model = onnx.load(output_path)

    # Change input type to INT32
    onnx_model.graph.input[0].type.tensor_type.elem_type = onnx.TensorProto.INT32

    # Add Cast node to convert INT32 to FLOAT
    cast_node = onnx.helper.make_node(
        'Cast',
        inputs=['input'],
        outputs=['input_float'],
        to=onnx.TensorProto.FLOAT
    )

    # Add Div node to scale down (divide by 1000)
    scale_name = 'scale_factor'
    scale_value = np.array([1000.0], dtype=np.float32)
    scale_tensor = numpy_helper.from_array(scale_value, name=scale_name)

    div_node = onnx.helper.make_node(
        'Div',
        inputs=['input_float', scale_name],
        outputs=['input_scaled']
    )

    # Update first node to use scaled input
    first_node = onnx_model.graph.node[0]
    for i, inp in enumerate(first_node.input):
        if inp == 'input':
            first_node.input[i] = 'input_scaled'

    # Insert nodes at beginning
    onnx_model.graph.node.insert(0, div_node)
    onnx_model.graph.node.insert(0, cast_node)
    onnx_model.graph.initializer.append(scale_tensor)

    onnx.save(onnx_model, output_path)

    print(f"✅ ONNX model exported: {output_path}")
    print(f"   Input type: INT32 (scale factor: 1000)")
    print(f"   Compatible with Jolt-Atlas onnx-tracer")

    return output_path

if __name__ == '__main__':
    # Generate data
    print("📊 Generating training data...")
    features, labels = generate_synthetic_data(10000)

    # Split data manually (80/20)
    split_idx = int(len(features) * 0.8)
    X_train, X_val = features[:split_idx], features[split_idx:]
    y_train, y_val = labels[:split_idx], labels[split_idx:]

    # Create datasets
    train_dataset = RugPullDataset(X_train, y_train)
    val_dataset = RugPullDataset(X_val, y_val)

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

    # Create model
    model = RugDetectorNN(input_size=60, hidden_sizes=[128, 64, 32], num_classes=3)

    # Train
    model = train_model(model, train_loader, val_loader, epochs=50)

    # Export to ONNX
    output_path = 'model/rugdetector_v1_nn.onnx'
    export_to_onnx(model, output_path)

    print("\n✅ Neural network RugDetector ready for Jolt-Atlas zkML!")
