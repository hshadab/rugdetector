#!/usr/bin/env python3
"""
Train a small NN model (18→32→16→1) for Jolt-Atlas zkML
Uses real RugPull dataset, fits within MAX_TENSOR_SIZE=64
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np
import sys

class SmallRugDetector(nn.Module):
    """
    Compact model for Jolt-Atlas: 18→32→16→1
    All hidden layers < 64 to fit MAX_TENSOR_SIZE
    """
    def __init__(self):
        super(SmallRugDetector, self).__init__()

        self.model = nn.Sequential(
            nn.Linear(18, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()  # Binary classification
        )

    def forward(self, x):
        return self.model(x)

class RugPullDataset(Dataset):
    """Dataset from real Uniswap data"""
    def __init__(self, features, labels):
        self.features = torch.FloatTensor(features)
        self.labels = torch.FloatTensor(labels).unsqueeze(1)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]

def load_real_dataset(csv_path):
    """Load and preprocess real RugPull dataset"""
    print(f"📊 Loading dataset: {csv_path}")

    df = pd.read_csv(csv_path)
    print(f"   Loaded {len(df)} samples")

    # Convert label to binary (handle both 'True'/'False' and 'TRUE'/'FALSE')
    df['Label'] = df['Label'].astype(str).str.upper()
    df['Label'] = (df['Label'] == 'TRUE').astype(int)

    # Get features (all columns except id and Label)
    feature_cols = [col for col in df.columns if col not in ['id', 'Label']]
    print(f"   Features: {len(feature_cols)} columns")

    X = df[feature_cols].values
    y = df['Label'].values

    # Handle NaN/inf values
    X = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)

    # Normalize features
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    # Class distribution
    unique, counts = np.unique(y, return_counts=True)
    print(f"   Class distribution: {dict(zip(unique, counts))}")

    return X.astype(np.float32), y.astype(np.float32), scaler

def train_model(model, train_loader, val_loader, epochs=100, lr=0.001):
    """Train the model"""
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    print("\n🚀 Training Small RugDetector (18→32→16→1)...")

    best_val_acc = 0
    best_model_state = None

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
            predicted = (outputs > 0.5).float()
            train_total += labels.size(0)
            train_correct += (predicted == labels).sum().item()

        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        val_loss = 0

        with torch.no_grad():
            for features, labels in val_loader:
                outputs = model(features)
                loss = criterion(outputs, labels)
                val_loss += loss.item()

                predicted = (outputs > 0.5).float()
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()

        train_acc = 100 * train_correct / train_total
        val_acc = 100 * val_correct / val_total

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_model_state = model.state_dict().copy()

        if (epoch + 1) % 10 == 0:
            print(f"Epoch [{epoch+1}/{epochs}] "
                  f"Train Loss: {train_loss/len(train_loader):.4f} "
                  f"Train Acc: {train_acc:.2f}% "
                  f"Val Acc: {val_acc:.2f}%")

    # Load best model
    if best_model_state:
        model.load_state_dict(best_model_state)

    print(f"\n✅ Training complete! Best validation accuracy: {best_val_acc:.2f}%")
    return model, best_val_acc

def export_to_onnx(model, output_path):
    """Export to ONNX"""
    model.eval()

    print(f"\n📦 Exporting to ONNX: {output_path}")

    dummy_input = torch.randn(1, 18, dtype=torch.float32)

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

    print(f"✅ ONNX export complete")

    # Verify
    try:
        import onnx
        onnx_model = onnx.load(output_path)
        onnx.checker.check_model(onnx_model)
        print("✓ ONNX model is valid")

        # Print operations
        print("\n🔧 Operations in model:")
        ops = set()
        for node in onnx_model.graph.node:
            ops.add(node.op_type)
        for op in sorted(ops):
            print(f"   - {op}")

    except ImportError:
        print("⚠️  onnx library not available for validation")

    return output_path

if __name__ == '__main__':
    # Load dataset
    csv_file = 'RugPull-Prediction-AI/Dataset_v1.9.csv'
    X, y, scaler = load_real_dataset(csv_file)

    # Split data (80/20)
    split_idx = int(len(X) * 0.8)
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_train, y_val = y[:split_idx], y[split_idx:]

    # Create datasets
    train_dataset = RugPullDataset(X_train, y_train)
    val_dataset = RugPullDataset(X_val, y_val)

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

    # Create and train model
    model = SmallRugDetector()

    print(f"\n📋 Model Architecture:")
    print(f"   Input: 18 features")
    print(f"   Hidden1: 32 neurons (ReLU)")
    print(f"   Hidden2: 16 neurons (ReLU)")
    print(f"   Output: 1 neuron (Sigmoid)")
    print(f"   Max tensor size: 32 (< 64 ✓)")

    model, best_acc = train_model(model, train_loader, val_loader, epochs=100)

    # Export to ONNX
    onnx_path = 'model/small_rugdetector.onnx'
    export_to_onnx(model, onnx_path)

    # Save scaler for inference
    import pickle
    with open('model/small_rugdetector_scaler.pkl', 'wb') as f:
        pickle.dump(scaler, f)
    print(f"✓ Saved scaler to model/small_rugdetector_scaler.pkl")

    print(f"\n✅ Small model ready for Jolt-Atlas zkML!")
    print(f"   Accuracy: {best_acc:.2f}%")
    print(f"   Model: {onnx_path}")
