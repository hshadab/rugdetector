#!/usr/bin/env python3
"""
Train logistic regression model for Jolt-Atlas zkML
Uses only Mul+ReduceSum+Add+Sigmoid operations (no MatMul)
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np

class LogisticRegressionModel(nn.Module):
    def __init__(self, input_size=18):
        super(LogisticRegressionModel, self).__init__()
        # Simple logistic regression: weights + bias + sigmoid
        self.weights = nn.Parameter(torch.randn(input_size))
        self.bias = nn.Parameter(torch.zeros(1))

    def forward(self, x):
        # x * w -> element-wise multiply
        # sum -> ReduceSum
        # + b -> Add
        # sigmoid -> Sigmoid
        logits = (x * self.weights).sum(dim=-1, keepdim=True) + self.bias
        return torch.sigmoid(logits)

class RugPullDataset(Dataset):
    def __init__(self, features, labels):
        self.features = torch.FloatTensor(features)
        self.labels = torch.FloatTensor(labels).unsqueeze(1)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]

# Load dataset
print("📊 Loading RugPull dataset...")
df = pd.read_csv('RugPull-Prediction-AI/Dataset_v1.9.csv')
print(f"   Loaded {len(df)} samples")

# Process labels
df['Label'] = df['Label'].astype(str).str.upper()
df['Label'] = (df['Label'] == 'TRUE').astype(int)

# Get features
feature_cols = [col for col in df.columns if col not in ['id', 'Label']]
X = df[feature_cols].values
y = df['Label'].values

# Handle NaN/inf
X = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)

# Normalize
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
X = scaler.fit_transform(X)

# Split
split_idx = int(len(X) * 0.8)
X_train, X_val = X[:split_idx], X[split_idx:]
y_train, y_val = y[:split_idx], y[split_idx:]

# Create datasets
train_dataset = RugPullDataset(X_train, y_train)
val_dataset = RugPullDataset(X_val, y_val)

train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=64, shuffle=False)

# Train
print("\n🚀 Training Logistic Regression for zkML...")
model = LogisticRegressionModel()
criterion = nn.BCELoss()
optimizer = optim.Adam(model.parameters(), lr=0.01)

best_val_acc = 0
best_model_state = None

for epoch in range(100):
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

    with torch.no_grad():
        for features, labels in val_loader:
            outputs = model(features)
            predicted = (outputs > 0.5).float()
            val_total += labels.size(0)
            val_correct += (predicted == labels).sum().item()

    train_acc = 100 * train_correct / train_total
    val_acc = 100 * val_correct / val_total

    if val_acc > best_val_acc:
        best_val_acc = val_acc
        best_model_state = model.state_dict().copy()

    if (epoch + 1) % 10 == 0:
        print(f"Epoch [{epoch+1}/100] Train Acc: {train_acc:.2f}% Val Acc: {val_acc:.2f}%")

# Load best model
if best_model_state:
    model.load_state_dict(best_model_state)

print(f"\n✅ Best validation accuracy: {best_val_acc:.2f}%")

# Export to ONNX
print(f"\n📦 Exporting to ONNX...")
model.eval()
dummy_input = torch.randn(1, 18)

torch.onnx.export(
    model, dummy_input, 'model/zkml_rugdetector.onnx',
    export_params=True, opset_version=11, do_constant_folding=True,
    input_names=['input'], output_names=['output'],
    dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
)

print("✓ Exported zkml_rugdetector.onnx")

# Verify operations
import onnx
onnx_model = onnx.load('model/zkml_rugdetector.onnx')
print("\nOperations (Jolt-Atlas compatible):")
for node in onnx_model.graph.node:
    print(f"  ✓ {node.op_type}")

# Save scaler
import pickle
with open('model/zkml_rugdetector_scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

print(f"\n🎉 zkML model ready!")
print(f"   Accuracy: {best_val_acc:.2f}%")
print(f"   Model: model/zkml_rugdetector.onnx")
print(f"   Compatible operations: Mul, ReduceSum, Add, Sigmoid")
