# Real Jolt Atlas Integration Example

Based on actual code from https://github.com/ICME-Lab/jolt-atlas

## Key Findings from Real Implementation

### 1. Actual API (from `/tmp/jolt-atlas/onnx-tracer/src/lib.rs`)

```rust
// Load ONNX model
pub fn model(model_path: &PathBuf) -> Model

// Decode model to instructions (preprocessing)
pub fn decode(model_path: &PathBuf) -> Vec<ONNXInstr>
pub fn decode_model(model: Model) -> Vec<ONNXInstr>

// Get execution trace (for proving)
pub fn trace(model_path: &PathBuf, input: &Tensor<i32>) -> (Vec<ONNXCycle>, ProgramIO)
pub fn execution_trace(model: Model, input: &Tensor<i32>) -> (Vec<ONNXCycle>, ProgramIO)
```

### 2. Input Format

**CRITICAL**: Inputs are `Tensor<i32>`, NOT `float32`!

```rust
// From examples in builder.rs:
let mut tensor: Tensor<i32> = Tensor::new(Some(&[50, 60, 70, 80]), &[1, 4]).unwrap();
tensor.set_scale(SCALE);  // Typical SCALE = 7

// Input to model:
let input = Tensor::new(Some(&input_data), &[1, 60]).unwrap();
```

### 3. Quantization Scale

Models use fixed-point arithmetic with a scale factor:

```rust
const SCALE: i32 = 7;  // Common scale factor

// To convert float to scaled i32:
fn to_scaled_i32(value: f32, scale: i32) -> i32 {
    (value * (2_f32.powi(scale))).round() as i32
}

// To convert back:
fn from_scaled_i32(value: i32, scale: i32) -> f32 {
    (value as f32) / (2_f32.powi(scale))
}

// Example:
// 0.5 with SCALE=7 -> 0.5 * 128 = 64
// 1.0 with SCALE=7 -> 1.0 * 128 = 128
```

### 4. Benchmark Results (from bench.rs)

```rust
fn prove_and_verify<F>(model_fn: F, input: Vec<i32>, input_shape: Vec<usize>) {
    let model = model_fn();
    let program_bytecode = onnx_tracer::decode_model(model.clone());

    // Preprocessing (~200ms)
    let pp: JoltProverPreprocessing<Fr, PCS, KeccakTranscript> =
        JoltSNARK::prover_preprocess(program_bytecode);

    // Execution trace
    let (raw_trace, program_output) =
        onnx_tracer::execution_trace(model, &Tensor::new(Some(&input), &input_shape).unwrap());
    let execution_trace = jolt_execution_trace(raw_trace.clone());

    // Generate proof (~300-500ms)
    let snark: JoltSNARK<Fr, PCS, KeccakTranscript> =
        JoltSNARK::prove(pp.clone(), execution_trace, &program_output);

    // Verify (~100-200ms)
    snark.verify((&pp).into(), program_output).unwrap();
}
```

**Total**: ~600-800ms (matches README claim)

##  5. Model Examples

Jolt Atlas includes pre-built models:

```rust
// From builder.rs:
pub fn multiclass0() -> Model  // Text classification (10 classes)
pub fn sentiment0() -> Model    // Sentiment analysis
pub fn tiny_mlp_head_model() -> Model  // 2-layer MLP
```

These are built using `ModelBuilder` with i32 tensors and scale factors.

## Corrected Integration for RugDetector

### Problem: Our Model Uses float32

Our ONNX model:
- Input: `float32[60]`
- Output: `float32[3]` (probabilities)

Jolt Atlas requires:
- Input: `i32[60]`
- Output: `i32[3]` (scaled integers)

### Solution 1: Quantize at Runtime

```rust
// In jolt_zkml/src/lib.rs

const SCALE: i32 = 7;  // Fixed-point scale (2^7 = 128)

fn quantize_features(features: Vec<f32>) -> Vec<i32> {
    features.iter()
        .map(|&f| (f * 128.0).round() as i32)  // 2^7 = 128
        .collect()
}

fn dequantize_output(output: Vec<i32>) -> Vec<f32> {
    output.iter()
        .map(|&i| (i as f32) / 128.0)
        .collect()
}

pub fn prove(&self, features: Vec<f32>) -> Result<ProofResult, ZKMLError> {
    // Quantize input
    let quantized = quantize_features(features);

    // Create tensor
    let input_tensor = Tensor::new(Some(&quantized), &vec![1, 60])
        .map_err(|e| ZKMLError::TensorError(e.to_string()))?;

    // Load model
    let model = onnx_tracer::model(&self.model_path);

    // Get bytecode (if not cached from preprocessing)
    let bytecode = onnx_tracer::decode_model(model.clone());

    // Get execution trace
    let (raw_trace, program_output) = onnx_tracer::execution_trace(model, &input_tensor);

    // Convert to Jolt execution trace
    let execution_trace = jolt_execution_trace(raw_trace);

    // Generate proof
    let pp = self.preprocessing.as_ref().unwrap();
    let snark = JoltSNARK::prove(pp.clone(), execution_trace, &program_output);

    Ok(ProofResult { snark, output: program_output, ... })
}
```

### Solution 2: Convert ONNX Model to i32 (Better)

Retrain our model to accept and output i32:

```python
# training/train_model_quantized.py

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import Int32TensorType
import onnx

# Train model
model = RandomForestClassifier(n_estimators=100, max_depth=20)

# Scale features during training
SCALE = 7
X_scaled = (X * (2 ** SCALE)).astype(np.int32)
model.fit(X_scaled, y)

# Convert to ONNX with Int32 input type
initial_type = [('int_input', Int32TensorType([None, 60]))]
onnx_model = convert_sklearn(
    model,
    initial_types=initial_type,
    target_opset=15,
    options={
        'nocl': False,  # Include class labels
        'zipmap': False  # Don't use ZipMap for output
    }
)

# Save
with open('model/rugdetector_v1_int32.onnx', 'wb') as f:
    f.write(onnx_model.SerializeToString())
```

Then use directly with Jolt Atlas (no runtime quantization needed).

## Updated Rust Integration

```rust
// jolt_zkml/src/lib.rs

use std::path::PathBuf;
use onnx_tracer::{model, decode_model, execution_trace, tensor::Tensor};
use zkml_jolt_core::{
    jolt::{JoltProverPreprocessing, JoltSNARK, execution_trace::jolt_execution_trace},
};
use ark_bn254::Fr;
use jolt_core::{
    poly::commitment::dory::DoryCommitmentScheme,
    utils::transcript::KeccakTranscript,
};

type PCS = DoryCommitmentScheme<KeccakTranscript>;
const SCALE: i32 = 7;

pub struct RugDetectorZKML {
    model_path: PathBuf,
    preprocessing: Option<JoltProverPreprocessing<Fr, PCS, KeccakTranscript>>,
}

impl RugDetectorZKML {
    pub fn new(model_path: PathBuf) -> Self {
        Self { model_path, preprocessing: None }
    }

    pub fn preprocess(&mut self) {
        // Load model
        let model = model(&self.model_path);

        // Decode to bytecode
        let bytecode = decode_model(model);

        // Preprocess for proving
        let pp = JoltSNARK::prover_preprocess(bytecode);

        self.preprocessing = Some(pp);
    }

    pub fn prove(&self, features: Vec<f32>) -> Result<ProofResult, ZKMLError> {
        let pp = self.preprocessing.as_ref()
            .ok_or(ZKMLError::NotPreprocessed)?;

        // Quantize features to i32 with SCALE=7
        let quantized: Vec<i32> = features.iter()
            .map(|&f| (f * 128.0).round() as i32)  // 2^7 = 128
            .collect();

        // Create input tensor
        let input_tensor = Tensor::new(Some(&quantized), &vec![1, 60])
            .map_err(|e| ZKMLError::TensorError(e.to_string()))?;

        // Load model
        let model = model(&self.model_path);

        // Get execution trace
        let (raw_trace, program_output) = execution_trace(model, &input_tensor);

        // Convert to Jolt execution trace
        let execution_trace = jolt_execution_trace(raw_trace);

        // Generate zkSNARK proof
        let snark: JoltSNARK<Fr, PCS, KeccakTranscript> =
            JoltSNARK::prove(pp.clone(), execution_trace, &program_output);

        // Extract verifying key
        let vk = pp.into();

        Ok(ProofResult {
            snark,
            output: program_output,
            verifying_key: vk,
        })
    }

    pub fn verify(
        proof: &JoltSNARK<Fr, PCS, KeccakTranscript>,
        verifying_key: &JoltVerifyingKey<Fr, PCS>,
        output: ProgramIO,
    ) -> Result<bool, ZKMLError> {
        proof.verify(verifying_key, output)
            .map_err(|e| ZKMLError::VerificationError(e.to_string()))
    }
}
```

## Testing with Actual Models

```bash
# Test with multiclass0 example from Jolt Atlas
cd /tmp/jolt-atlas/zkml-jolt-core

# Run benchmark (includes preprocessing, proving, verifying)
cargo run -r -- profile --name multi-class --format default

# Expected output:
# ~200ms preprocessing
# ~300-500ms proving
# ~100-200ms verifying
# Total: ~600-800ms
```

## Key Differences from Our Initial Approach

| Aspect | Initial | Actual (from code) |
|--------|---------|-------------------|
| **Input Type** | Assumed float32 → i32 conversion | Native i32 with scale factor |
| **Quantization** | Simple `* 1000` | Fixed-point with `2^SCALE` |
| **API** | Made-up interface | Real `onnx_tracer::` functions |
| **Tensor Creation** | Guessed | `Tensor::new(Some(&data), &shape)` |
| **Scale Factor** | Not considered | Critical: SCALE=7 typical |
| **Model Format** | Assumed float32 ONNX works | Need i32 ONNX or runtime conversion |

## Recommended Next Steps

1. **Test with existing models first**:
   ```bash
   cd /tmp/jolt-atlas
   cargo build --release
   cd zkml-jolt-core
   cargo run -r -- profile --name multi-class
   ```

2. **Convert our ONNX model**:
   - Either: Retrain with i32 input/output
   - Or: Use runtime quantization (add ~1ms overhead)

3. **Update integration code**:
   - Use real API from `onnx_tracer`
   - Use proper scale factors (2^7 = 128)
   - Follow their tensor creation pattern

4. **Benchmark**:
   - Should match their ~700ms total time
   - If significantly different, check quantization

## Conclusion

The actual Jolt Atlas API is **simpler** than we thought, but requires:
- Native i32 tensors (not float32)
- Fixed-point arithmetic with scale factors
- Proper ONNX model format

Our integration code structure was correct, but needs these adjustments to match the real implementation.
